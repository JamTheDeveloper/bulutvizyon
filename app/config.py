"""
Uygulama yapılandırması
"""
import os
from datetime import timedelta
from urllib.parse import quote_plus

class Config:
    """Temel yapılandırma sınıfı"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'bulutvizyongizli2023anahtar')
    
    # MongoDB kimlik bilgileri
    MONGO_USER = os.environ.get('MONGO_USER', 'elektrobil_admin')
    MONGO_PASS = os.environ.get('MONGO_PASS', 'Eb@2254097*')
    MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
    MONGO_PORT = os.environ.get('MONGO_PORT', '27017')
    MONGO_DB = os.environ.get('MONGO_DB', 'bulutvizyondb')
    
    # URL güvenli kullanıcı adı ve şifre
    encoded_username = quote_plus(MONGO_USER)
    encoded_password = quote_plus(MONGO_PASS)
    
    # MongoDB URI
    MONGO_URI = f"mongodb://{encoded_username}:{encoded_password}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"
    
    UPLOAD_FOLDER = 'app/static/uploads'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov', 'avi'}
    PASSWORD_RESET_EXPIRE = timedelta(hours=24)
    
    # Mail ayarları
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'mail.elektrobil.com.tr')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() in ('true', 'on', '1')
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False').lower() in ('true', 'on', '1')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', 'bulutvizyon@elektrobil.com.tr')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'bulutvizyon@elektrobil.com.tr')

class DevelopmentConfig(Config):
    """Geliştirme ortamı yapılandırması"""
    DEBUG = True
    TESTING = False

class TestingConfig(Config):
    """Test ortamı yapılandırması"""
    DEBUG = False
    TESTING = True
    MONGO_DB = 'bulutvizyondb_test'
    MONGO_URI = f"mongodb://{Config.encoded_username}:{Config.encoded_password}@{Config.MONGO_HOST}:{Config.MONGO_PORT}/{MONGO_DB}?authSource=admin"

class ProductionConfig(Config):
    """Canlı ortam yapılandırması"""
    DEBUG = False
    TESTING = False
    # Canlı ortama özel güvenlik ayarları
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

# Aktif yapılandırmayı belirle
active_config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}.get(os.environ.get('FLASK_ENV', 'development')) 