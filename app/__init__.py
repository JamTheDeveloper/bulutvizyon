"""
BulutVizyon Flask Uygulaması
"""
import os
from flask import Flask, render_template, send_from_directory, g, request, session
import json
from flask_cors import CORS
from flask_pymongo import PyMongo
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from datetime import datetime, timedelta
from pymongo import MongoClient
from flask_wtf.csrf import CSRFProtect, CSRFError
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler
from bson import ObjectId
from werkzeug.middleware.proxy_fix import ProxyFix
from urllib.parse import quote_plus

# ObjectId için özel JSON encoder
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(MongoJSONEncoder, self).default(obj)

# Uygulama bileşenleri
mongo = PyMongo()
login_manager = LoginManager()
mail = Mail()
bootstrap = Bootstrap()
csrf = CSRFProtect()

# Yapılandırma
from .config import active_config

def create_app(test_config=None):
    """Flask uygulamasını oluştur ve yapılandır"""
    # .env dosyasını yükle
    load_dotenv()
    
    # Flask uygulamasını başlat
    app = Flask(__name__, instance_relative_config=True)
    
    # Proxy işleme ekle
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # MongoDB bağlantı bilgilerini al ve URI oluştur - yapılandırmadan önce ayarla
    mongo_user = os.environ.get('MONGO_USER', 'elektrobil_admin')
    mongo_pass = os.environ.get('MONGO_PASS', 'Eb@2254097*')
    mongo_host = os.environ.get('MONGO_HOST', 'localhost')
    mongo_port = os.environ.get('MONGO_PORT', '27017')
    mongo_db = os.environ.get('MONGO_DB', 'bulutvizyondb')
    
    # Şifreyi URL-encode et
    encoded_password = quote_plus(mongo_pass)
    
    # MongoDB URI oluştur ve doğrudan os.environ'a ata - PyMongo bu değeri okuyacak
    mongo_uri = f"mongodb://{mongo_user}:{encoded_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"
    os.environ['MONGO_URI'] = mongo_uri
    
    try:
        app.logger.info(f"MongoDB URI oluşturuldu: {mongo_uri}")
    except:
        print(f"MongoDB URI oluşturuldu: {mongo_uri}")
    
    # Varsayılan konfigürasyon
    app.config.from_object(active_config)
    app.config.from_mapping(
        UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads'),
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'),
        MONGO_URI=mongo_uri
    )

    # Test konfigürasyonu
    if test_config is None:
        # Test konfigürasyonu yoksa, instance konfigürasyonunu yükle
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Test konfigürasyonu varsa, onu yükle
        app.config.from_mapping(test_config)

    # Instance klasörünün var olduğundan emin ol
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Upload klasörünün var olduğundan emin ol
    try:
        os.makedirs(app.config['UPLOAD_FOLDER'])
    except OSError:
        pass

    # Özel JSON encoder ayarla
    app.json.encoder = MongoJSONEncoder
    
    # Uzantıları başlat
    mongo.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    CORS(app)
    
    # CSRF koruması
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 saat (saniye cinsinden)
    app.config['WTF_CSRF_SSL_STRICT'] = False  # HTTPS kontrolünü gevşet
    csrf.init_app(app)
    
    # CSRF hatası için özel hata işleyici
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        return render_template('errors/csrf_error.html', reason=e.description), 400
    
    # Giriş görünümünü ayarla
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bu sayfayı görüntülemek için giriş yapmalısınız.'
    login_manager.login_message_category = 'info'
    
    # Dil ve zaman dilimi ayarları
    app.jinja_env.globals.update(now=datetime.now)
    
    # ObjectId'leri string'e çeviren ve datetime'ları formatlayan jinja filter'ı ekle
    @app.template_filter('str')
    def string_filter(value):
        if isinstance(value, ObjectId):
            return str(value)
        return value
    
    # Template yardımcı fonksiyonları
    from .models.user import User
    
    def get_user(user_id):
        if not user_id:
            return None
        return User.find_by_id(user_id)
    
    app.jinja_env.globals.update(get_user=get_user)
    
    # Her istekte mevcut kullanıcıyı sağla
    @app.context_processor
    def inject_user():
        if 'user_id' in session:
            return {'current_user': get_user(session['user_id'])}
        return {'current_user': None}
    
    # Blueprint'leri kaydet
    from .routes import auth, admin, user, supervisor, api, main
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp, url_prefix='/admin')
    app.register_blueprint(user.bp, url_prefix='/user')
    app.register_blueprint(supervisor.bp, url_prefix='/supervisor')
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(main.main_bp)
    
    # Kullanıcı yükleme
    @login_manager.user_loader
    def load_user(user_id):
        return User.find_by_id(user_id)
    
    # Hata sayfaları
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        return render_template('errors/500.html'), 500
    
    # Context processor ekle
    @app.context_processor
    def utility_processor():
        from datetime import datetime
        
        def now():
            return datetime.now()
            
        return dict(now=now)
    
    # Medya servis etme endpoint'i - optimize edilmiş
    @app.route('/uploads/<filename>')
    def serve_uploads(filename):
        import os, mimetypes
        from flask import send_from_directory, current_app, request, make_response
        
        # Mimetype'ı belirle
        mimetype, _ = mimetypes.guess_type(filename)
        
        # Varsayılan önbellekleme süresi - 1 gün (saniye cinsinden)
        cache_duration = 86400
        
        # Video dosyaları için daha uzun önbellekleme süresi kullan
        if mimetype and mimetype.startswith('video/'):
            # Videolar için 7 gün önbellekleme
            cache_duration = 604800
        elif mimetype and mimetype.startswith('image/'):
            # Resimler için 3 gün önbellekleme
            cache_duration = 259200
        
        # ETag'ları kullanarak önbellekleme yap
        response = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], filename))
        
        # Önbellekleme başlıklarını ayarla
        response.headers['Cache-Control'] = f'public, max-age={cache_duration}'
        
        # ETag oluştur
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            file_stat = os.stat(file_path)
            etag = f'"{filename}-{file_stat.st_mtime}-{file_stat.st_size}"'
            response.headers['ETag'] = etag
            
            # ETag kontrolü yap
            if request.headers.get('If-None-Match') == etag:
                return '', 304  # Not Modified
        
        return response
    
    return app

def configure_logging(app):
    """Loglama ayarlarını yapılandır"""
    if not os.path.exists('logs'):
        os.mkdir('logs')
        
    file_handler = RotatingFileHandler('logs/bulutvizyon.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('BulutVizyon başlatılıyor...')

def run_app():
    app = create_app()
    app.run(host='0.0.0.0', port=5006, debug=True)

if __name__ == '__main__':
    run_app() 