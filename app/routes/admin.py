from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.models.user import User
from app.models.screen import Screen
from app.models.media import Media
from app.models.logs import Log
from app.models.screen_media import ScreenMedia
from app.utils.decorators import admin_required
import secrets
import string
import os
from bson import ObjectId
from functools import wraps
from app import mongo
from bson.objectid import ObjectId
from app.utils.admin_ekran_detay import get_screen_detail, get_user_screens_detail

bp = Blueprint('admin', __name__, url_prefix='/admin')

@bp.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard sayfası"""
    user_count = len(User.find_all())
    screen_count = len(Screen.find_all())
    media_count = len(Media.find_all())
    pending_media_count = len(Media.find_pending())
    
    # Playlist istatistiklerini ekle
    from app.models.playlist import Playlist
    playlist_count = mongo.db.playlists.count_documents({})
    recent_playlists = list(mongo.db.playlists.find().sort('created_at', -1).limit(5))
    
    # Playlist nesnelerini oluştur
    playlist_objects = []
    for playlist_data in recent_playlists:
        playlist_objects.append(Playlist(**playlist_data))
    
    # Kullanıcı bilgilerini ekle
    for playlist in playlist_objects:
        user = User.find_by_id(playlist.user_id)
        playlist.user_name = f"{user.name}" if user else "Bilinmiyor"
    
    recent_users = User.find_all()[:5]
    recent_screens = Screen.find_all()[:5]
    recent_media = Media.find_all()[:5]
    
    return render_template(
        'admin/dashboard.html', 
        user_count=user_count,
        screen_count=screen_count,
        media_count=media_count,
        pending_media_count=pending_media_count,
        playlist_count=playlist_count,
        recent_users=recent_users,
        recent_screens=recent_screens,
        recent_media=recent_media,
        recent_playlists=playlist_objects,
        User=User  # User sınıfını template'e gönderiyoruz
    )

@bp.route('/users')
@admin_required
def users():
    """Kullanıcı listesi sayfası"""
    users = User.find_all()
    return render_template('admin/users.html', users=users)

@bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Kullanıcı oluşturma sayfası"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        package = request.form.get('package')
        
        # E-posta kontrolü
        existing_user = User.find_by_email(email)
        if existing_user:
            flash('Bu e-posta adresi zaten kullanımda.', 'danger')
            return render_template('admin/create_user.html')
        
        # Rastgele şifre oluştur
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        
        # Kullanıcı oluştur
        user = User.create(
            email=email, 
            password=password, 
            name=name, 
            role=role, 
            package=package, 
            status='active'
        )
        
        # Hoşgeldin e-postası gönder
        try:
            # Basit ASCII içerikli bir e-posta 
            from app.utils.email import Mailer
            login_url = url_for('auth.login', _external=True)
            mailer = Mailer()
            simple_content = """
            <html>
            <body>
                <p>Merhaba,</p>
                <p>BulutVizyon sistemine hosgeldiniz!</p>
                <p>Giris bilgileriniz:</p>
                <p>E-posta: {}</p>
                <p>Gecici sifreniz: {}</p>
                <p>Giris yapmak icin: <a href="{}">Buraya tiklayin</a></p>
                <p>Tesekkurler,<br>BulutVizyon Ekibi</p>
            </body>
            </html>
            """.format(email, password, login_url)
            
            mailer.sendHTML(
                to=email,
                subject="BulutVizyon - Hos Geldiniz",
                content=simple_content
            )
        except Exception as e:
            current_app.logger.error(f"Hosgeldin e-postasi gonderilemedi: {str(e)}")
            # E-posta başarısız olsa da kullanıcı oluşturma işlemini devam ettir
        
        Log.log_action(
            action=Log.TYPE_USER_CREATE,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"created_user_id": user.id, "name": name, "email": email}
        )
        
        flash(f'Kullanıcı başarıyla oluşturuldu. Geçici şifre: {password}', 'success')
        return redirect(url_for('admin.users'))
        
    return render_template('admin/create_user.html')

@bp.route('/users/edit/<user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Kullanıcı düzenleme sayfası"""
    # MongoDB ile doğrudan erişim
    try:
        from app import mongo
        from bson.objectid import ObjectId
        
        # URL'den gelen ID'yi doğrula
        current_app.logger.info(f"Kullanıcı düzenleme sayfası: user_id={user_id}, method={request.method}")
        
        if not ObjectId.is_valid(user_id):
            flash('Geçersiz kullanıcı ID formatı.', 'danger')
            return redirect(url_for('admin.users'))
            
        # MongoDB'den doğrudan kullanıcıyı al
        user_data = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        
        if not user_data:
            flash('Kullanıcı bulunamadı.', 'danger')
            return redirect(url_for('admin.users'))
            
        # Kullanıcı nesnesini manuel oluştur
        from app.models.user import User
        user = User(**user_data)
        
        if request.method == 'POST':
            # POST verilerini al
            current_app.logger.info(f"POST verisi alındı: {request.form}")
            
            name = request.form.get('name')
            email = request.form.get('email')
            role = request.form.get('role')
            package = request.form.get('package')
            status = request.form.get('status')
            
            current_app.logger.info(f"Form değerleri: name={name}, email={email}, role={role}, package={package}, status={status}")
            
            # E-posta kontrolü (kendisi hariç)
            email_exists = User.find_by_email(email)
            
            if email_exists and str(email_exists.id) != str(user_id):
                flash('Bu e-posta adresi zaten kullanımda.', 'danger')
                return render_template('admin/edit_user.html', 
                                      user=user,
                                      screen_count=len(Screen.find_by_user(user.id)),
                                      media_count=len(Media.find_by_user(user.id)),
                                      view_count=0)
            
            try:
                # Kullanıcıyı güncelle
                user.update(
                    name=name,
                    email=email,
                    role=role, 
                    package=package,
                    status=status
                )
                
                from app.models.logs import Log
                Log.log_action(
                    action="user_update",
                    user_id=session['user_id'],
                    ip_address=request.remote_addr,
                    details={"updated_user_id": user.id, "name": name, "email": email}
                )
                
                flash('Kullanıcı başarıyla güncellendi.', 'success')
                return redirect(url_for('admin.users'))
            except Exception as update_error:
                current_app.logger.error(f"Kullanıcı güncellenirken hata: {str(update_error)}")
                flash('Kullanıcı güncellenirken bir hata oluştu.', 'danger')
                
                # Hata oluştuğunda form değerlerini koruyarak sayfayı yeniden göster
                return render_template('admin/edit_user.html', 
                                      user=user,
                                      screen_count=len(Screen.find_by_user(user.id)),
                                      media_count=len(Media.find_by_user(user.id)),
                                      view_count=0)
        
        # Kullanıcı istatistiklerini hesapla
        from app.models.screen import Screen
        from app.models.media import Media
        
        screen_count = len(Screen.find_by_user(user.id))
        media_count = len(Media.find_by_user(user.id))
        view_count = 0  # İleriki aşamalarda görüntülenme sayısı için
        
        # Atanmış supervisor'ı bul (varsa)
        assigned_supervisor = None
        if hasattr(user, 'supervisor_id') and user.supervisor_id:
            assigned_supervisor = User.find_by_id(user.supervisor_id)
        
        # Tüm supervisor'ları getir
        supervisors = User.find_all(role=User.ROLE_SUPERVISOR)
        
        # Aktivite verileri
        activities = [
            {
                'icon': 'sign-in-alt',
                'color': 'primary',
                'description': 'Kullanıcı giriş yaptı',
                'time': user.last_login or user.created_at
            },
            {
                'icon': 'upload',
                'color': 'success',
                'description': 'Yeni medya yükledi',
                'time': user.created_at
            }
        ]
        
        # Template'e verileri gönder
        return render_template('admin/edit_user.html', 
                            user=user, 
                            screen_count=screen_count, 
                            media_count=media_count, 
                            view_count=view_count,
                            activities=activities,
                            supervisors=supervisors,
                            assigned_supervisor=assigned_supervisor)
                            
    except Exception as e:
        # Hata durumunda log ve yönlendirme
        import traceback
        current_app.logger.error(f"Kullanıcı düzenleme sayfası yüklenirken hata: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        flash('Beklenmeyen bir hata oluştu.', 'danger')
        return redirect(url_for('admin.users'))

@bp.route('/users/delete/<user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Kullanıcı silme"""
    user = User.find_by_id(user_id)
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Admin kendisini silemez
    if user_id == session['user_id']:
        flash('Kendinizi silemezsiniz.', 'danger')
        return redirect(url_for('admin.users'))
    
    Log.log_action(
        action=Log.TYPE_USER_DELETE,
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={"deleted_user_id": user.id, "name": user.name, "email": user.email}
    )
    
    user.delete()
    flash('Kullanıcı başarıyla silindi.', 'success')
    return redirect(url_for('admin.users'))

@bp.route('/users/reset_password/<user_id>', methods=['POST'])
@admin_required
def reset_password(user_id):
    """Kullanıcıya şifre sıfırlama e-postası gönderir"""
    current_app.logger.info(f"Admin panelinden şifre sıfırlama isteği alındı: user_id={user_id}")
    user = User.find_by_id(user_id)
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.users'))

    try:
        # Şifre sıfırlama token oluştur
        token = user.set_reset_token()
        current_app.logger.info(f"Şifre sıfırlama token oluşturuldu: user_id={user.id}")
        
        # Sıfırlama URL'sini oluştur
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        # E-posta gönder
        from app.utils.email import send_password_reset_email
        current_app.logger.info(f"Şifre sıfırlama e-postası gönderiliyor: Kime={user.email}")
        success = send_password_reset_email(user.email, reset_url)
        
        if success:
            Log.log_action(
                action="password_reset_email_sent",
                user_id=session['user_id'],
                ip_address=request.remote_addr,
                details={"target_user_id": user.id, "email": user.email}
            )
            flash(f'{user.name} kullanıcısına şifre sıfırlama e-postası başarıyla gönderildi.', 'success')
        else:
            flash(f'Şifre sıfırlama e-postası gönderilirken bir hata oluştu. Lütfen logları kontrol edin.', 'danger')
            
    except Exception as e:
        current_app.logger.error(f"Admin panelinden şifre sıfırlama e-postası gönderilirken hata: {str(e)}")
        flash('Şifre sıfırlama e-postası gönderilirken beklenmedik bir hata oluştu.', 'danger')

    return redirect(url_for('admin.edit_user', user_id=user_id))

@bp.route('/screens')
@admin_required
def screens():
    """Ekranlar listesi"""
    # Tüm kullanıcıları getir
    users = User.find_all()
    
    # Tüm ekranları getir
    all_screens = Screen.find_all()
    
    # Kullanıcılara göre ekranları gruplayacak sözlük
    screens_by_user = {}
    
    # Her kullanıcı için ekranları bul
    for user in users:
        user_screens = []
        for screen in all_screens:
            if screen.user_id == user.id:
                # Playlistleri getir (eğer varsa)
                if hasattr(screen, 'playlist_id') and screen.playlist_id:
                    from app.models.playlist import Playlist
                    playlist = Playlist.find_by_id(screen.playlist_id)
                    if playlist:
                        screen.playlist = playlist
                
                user_screens.append(screen)
        
        # Sadece ekranı olan kullanıcıları ekle
        if user_screens:
            screens_by_user[user] = user_screens
    
    # Filtreleme parametrelerini al
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    user_id = request.args.get('user_id', '')
    
    # Filtrelenmiş sözlüğü oluştur
    filtered_screens_by_user = {}
    
    # Filtrelemeyi uygula
    for user, user_screens in screens_by_user.items():
        # Kullanıcı ID'sine göre filtrele
        if user_id and str(user.id) != user_id:
            continue
        
        filtered_screens = []
        for screen in user_screens:
            # Duruma göre filtrele
            if status and screen.status != status:
                continue
            
            # Arama terimlerine göre filtrele
            if search and search.lower() not in screen.name.lower() and (not screen.description or search.lower() not in screen.description.lower()):
                continue
            
            filtered_screens.append(screen)
        
        if filtered_screens:
            filtered_screens_by_user[user] = filtered_screens
    
    # Filtreleme yapıldıysa filtrelenmiş sonuçları, değilse tüm sonuçları gönder
    if search or status or user_id:
        screens_by_user = filtered_screens_by_user
    
    return render_template('admin/screens.html', screens_by_user=screens_by_user, users=users, hasattr=hasattr)

@bp.route('/screens/view/')
@admin_required
def view_screen_redirect():
    """Eksik screen_id parametresi ile erişimi yönetir"""
    flash('Lütfen görüntülemek için bir ekran seçin.', 'warning')
    return redirect(url_for('admin.screens'))

@bp.route('/screens/view/<screen_id>')
@admin_required
def view_screen(screen_id):
    """Ekran detay sayfası"""
    current_app.logger.info(f"[EKRAN DETAY] Ekran ID: {screen_id} için detay sayfası açılıyor")
    
    # Eski metod (mevcut kod)
    screen = Screen.find_by_id(screen_id)
    if not screen:
        current_app.logger.error(f"[EKRAN DETAY] {screen_id} ID'li ekran bulunamadı")
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('admin.screens'))
    
    # Yeni geliştirilen gelişmiş detayları al
    enhanced_details = get_screen_detail(screen_id)
    current_app.logger.info(f"[EKRAN DETAY] Gelişmiş detaylar: {enhanced_details is not None}")
    
    current_app.logger.info(f"[EKRAN DETAY] Ekran bulundu: {screen.name}, Kullanıcı ID: {screen.user_id}")
    user = User.find_by_id(screen.user_id)
    
    # Ekrana atanmış playlist bilgilerini getir
    from app.models.playlist import Playlist
    from app.models.playlist_media import PlaylistMedia
    
    playlist = None
    playlist_media = []
    
    # Ekranın playlist_id özelliği varsa
    playlist_id = None
    if hasattr(screen, 'playlist_id'):
        playlist_id = screen.playlist_id
        current_app.logger.info(f"[EKRAN DETAY] Ekran playlist_id kontrol: {playlist_id}")
    
    # MongoDB belgesinde playlist_id alanı varsa
    if hasattr(screen, '_id') and isinstance(screen._id, dict) and 'playlist_id' in screen._id:
        playlist_id = screen._id.get('playlist_id')
        current_app.logger.info(f"[EKRAN DETAY] MongoDB belgesinde playlist_id: {playlist_id}")
    
    # Screen nesnesinin tüm özelliklerini logla
    screen_properties = dir(screen)
    current_app.logger.info(f"[EKRAN DETAY] Ekran sınıfı özellikleri: {screen_properties}")
    
    # Screen nesnesinin to_dict metodu varsa kullan
    if hasattr(screen, 'to_dict'):
        screen_dict = screen.to_dict()
        current_app.logger.info(f"[EKRAN DETAY] Ekran to_dict: {screen_dict}")
        if 'playlist_id' in screen_dict:
            playlist_id = screen_dict['playlist_id']
            current_app.logger.info(f"[EKRAN DETAY] to_dict'ten playlist_id: {playlist_id}")
    
    # MongoDB koleksiyonundan doğrudan sorgula
    from bson.objectid import ObjectId
    try:
        if isinstance(screen_id, str):
            screen_data = mongo.db.screens.find_one({"_id": ObjectId(screen_id)})
            if screen_data and 'playlist_id' in screen_data:
                playlist_id = screen_data['playlist_id']
                current_app.logger.info(f"[EKRAN DETAY] MongoDB'den playlist_id: {playlist_id}")
    except Exception as e:
        current_app.logger.error(f"[EKRAN DETAY] MongoDB sorgulamada hata: {str(e)}")
    
    # Playlist'i getir
    if playlist_id:
        try:
            playlist = Playlist.find_by_id(playlist_id)
            current_app.logger.info(f"[EKRAN DETAY] Playlist bulundu: {playlist is not None}")
            
            if playlist:
                # Playlist'e ait medyaları getir
                playlist_media_relations = PlaylistMedia.find_by_playlist(playlist_id)
                current_app.logger.info(f"[EKRAN DETAY] Playlist medya ilişkileri: {len(playlist_media_relations) if playlist_media_relations else 0}")
                
                playlist_media = []  # Listeyi sıfırla
                
                for relation in playlist_media_relations:
                    media = Media.find_by_id(relation.media_id)
                    if media:
                        current_app.logger.info(f"[EKRAN DETAY] Playlist medyası bulundu: {getattr(media, 'title', media.get('title') if isinstance(media, dict) else 'bilinmiyor')}")
                        
                        media_dict = {}
                        # Media nesnesinin tipine göre işlem yap
                        if isinstance(media, dict):
                            # MongoDB belgesini doğrudan kullan
                            media_dict = {
                                'id': str(media.get('_id')),
                                'title': media.get('title', ''),
                                'filename': media.get('filename', ''),
                                'file_type': media.get('file_type', ''),
                                'type': media.get('file_type', ''),
                                'file_size': media.get('file_size', 0),
                                'views': media.get('views', 0),
                                'created_at': media.get('created_at'),
                                'updated_at': media.get('updated_at'),
                                'duration': media.get('duration', 0),
                                'last_played': media.get('last_played', None),
                                'url': f"/static/uploads/{media.get('filename', '')}" if media.get('filename') else ''
                            }
                        else:
                            # Sınıf örneği - to_dict metodu ile dönüştür
                            try:
                                media_dict = media.to_dict()
                                # Şablon uyumluluğu için type alanını ekle
                                media_dict['type'] = media_dict.get('file_type', '')
                                # URL oluştur
                                media_dict['url'] = f"/static/uploads/{media_dict.get('filename', '')}" if media_dict.get('filename') else ''
                            except Exception as e:
                                current_app.logger.error(f"[EKRAN DETAY] Media to_dict hatası: {str(e)}")
                                continue
                                
                        # İlişki bilgilerini ekle
                        media_dict['order'] = relation.order
                        media_dict['playlist_media_id'] = relation.id
                        media_dict['display_time'] = relation.display_time
                        
                        playlist_media.append(media_dict)
                
                # Medyaları sıralama sırasına göre sırala
                playlist_media = sorted(playlist_media, key=lambda x: x['order'])
                current_app.logger.info(f"[EKRAN DETAY] Playlist medya sayısı: {len(playlist_media)}")
        except Exception as e:
            current_app.logger.error(f"[EKRAN DETAY] Playlist işlemlerinde hata: {str(e)}")
    
    # Ekrana doğrudan atanmış medyaları getir
    current_app.logger.info(f"[EKRAN DETAY] Ekrana atanmış medyaları getirme başlıyor")
    screen_media_relations = ScreenMedia.find_by_screen(screen_id)
    current_app.logger.info(f"[EKRAN DETAY] Ekran-medya ilişkileri: {len(screen_media_relations) if screen_media_relations else 0}")
    
    # Medya detaylarını al ve sırala
    assigned_media = []
    for relation in screen_media_relations:
        media = Media.find_by_id(relation.media_id)
        if media:
            current_app.logger.info(f"[EKRAN DETAY] Ekrana atanmış medya bulundu: {getattr(media, 'title', media.get('title') if isinstance(media, dict) else 'bilinmiyor')}")
            
            # Medya bilgilerine ilişki bilgilerini ekle
            media_dict = {}
            
            # Media nesnesinin tipine göre işlem yap
            if isinstance(media, dict):
                # MongoDB belgesini doğrudan kullan
                media_dict = {
                    'id': str(media.get('_id')),
                    'title': media.get('title', ''),
                    'filename': media.get('filename', ''),
                    'file_type': media.get('file_type', ''),
                    'type': media.get('file_type', ''),
                    'file_size': media.get('file_size', 0),
                    'views': media.get('views', 0),
                    'created_at': media.get('created_at'),
                    'updated_at': media.get('updated_at'),
                    'duration': media.get('duration', 0),
                    'last_played': media.get('last_played', None),
                    'url': f"/static/uploads/{media.get('filename', '')}" if media.get('filename') else ''
                }
            else:
                # Sınıf örneği - to_dict metodu ile dönüştür
                try:
                    media_dict = media.to_dict()
                    # Şablon uyumluluğu için type alanını ekle
                    media_dict['type'] = media_dict.get('file_type', '')
                    # URL oluştur
                    media_dict['url'] = f"/static/uploads/{media_dict.get('filename', '')}" if media_dict.get('filename') else ''
                except Exception as e:
                    current_app.logger.error(f"[EKRAN DETAY] Media to_dict hatası: {str(e)}")
                    continue
            
            # İlişki bilgilerini ekle
            media_dict['order'] = relation.order
            media_dict['screen_media_id'] = relation.id
            media_dict['display_time'] = relation.display_time
            
            assigned_media.append(media_dict)
    
    # Medyaları sıralama sırasına göre sırala
    assigned_media = sorted(assigned_media, key=lambda x: x['order'])
    current_app.logger.info(f"[EKRAN DETAY] Ekrana atanmış medya sayısı: {len(assigned_media)}")
    
    # Ekrana atanabilecek medyaları getir (aktif ve atanmamış olanlar)
    assigned_media_ids = [m['id'] for m in assigned_media]
    available_media = []
    
    # Önce tüm medyaları getir, sonra aktif olanları filtrele
    all_media = Media.find_all()
    
    # Aktif medyaları getir ve zaten atanmışları filtrele
    for media in all_media:
        if media.get('status') == Media.STATUS_ACTIVE and media.get('_id') not in assigned_media_ids:
            available_media.append(media)
    
    current_app.logger.info(f"[EKRAN DETAY] Şablona gönderilecek değişkenler: playlist={playlist is not None}, playlist_media={len(playlist_media)}, assigned_media={len(assigned_media)}")
    
    # Şablonu render et - Gelişmiş detayları da gönder
    return render_template('admin/view_screen.html', 
                          screen=screen, 
                          user=user, 
                          assigned_media=assigned_media,
                          available_media=available_media,
                          playlist=playlist,
                          playlist_media=playlist_media,
                          enhanced_details=enhanced_details,  # Yeni gelişmiş detaylar
                          hasattr=hasattr)

@bp.route('/screens/status/<screen_id>', methods=['POST'])
@admin_required
def toggle_screen_status(screen_id):
    """Ekran durumunu değiştirme"""
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('admin.screens'))
    
    # Durumu değiştir
    current_status = screen.status
    new_status = Screen.STATUS_INACTIVE if current_status == Screen.STATUS_ACTIVE else Screen.STATUS_ACTIVE
    
    try:
        # Screen nesnesinin update metodu ile güncelle
        screen.update(status=new_status)
        
        Log.log_action(
            action=Log.TYPE_SCREEN_UPDATE,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"screen_id": screen.id, "field": "status", "value": new_status}
        )
        
        status_text = "aktif" if new_status == Screen.STATUS_ACTIVE else "pasif"
        flash(f'Ekran durumu {status_text} olarak güncellendi.', 'success')
    except Exception as e:
        current_app.logger.error(f"Ekran durumu değiştirilirken hata: {str(e)}")
        flash('Ekran durumu değiştirilirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin.screens'))

@bp.route('/screens/approve/<screen_id>', methods=['POST'])
@admin_required
def approve_screen(screen_id):
    """Ekran onaylama"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('admin.screens'))
    
    # Ekranı onayla
    screen.update(status=Screen.STATUS_ACTIVE)
    
    # Kullanıcı bilgilerini getir
    user = User.find_by_id(screen.user_id)
    
    # Log kaydı
    Log.log_action(
        action=Log.TYPE_SCREEN_APPROVED,
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={
            "screen_id": screen_id,
            "screen_name": screen.name,
            "owner_id": screen.user_id
        }
    )
    
    # Email bildirim gönder
    if user:
        from app.utils.email import send_screen_status_change_notification
        send_screen_status_change_notification(
            email=user.email,
            name=user.name,
            screen_name=screen.name,
            screen_code=screen.code,
            new_status='active',
            screen_location=screen.location,
            reason="Yönetici tarafından onaylandı"
        )
    
    flash('Ekran başarıyla onaylandı.', 'success')
    return redirect(url_for('admin.view_screen', screen_id=screen_id))

@bp.route('/screens/disable/<screen_id>', methods=['POST'])
@admin_required
def disable_screen(screen_id):
    """Ekran devre dışı bırakma"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('admin.screens'))
    
    # Nedeni al
    reason = request.form.get('reason', 'Yönetici tarafından devre dışı bırakıldı')
    
    # Ekranı devre dışı bırak
    screen.update(status=Screen.STATUS_INACTIVE)
    
    # Kullanıcı bilgilerini getir
    user = User.find_by_id(screen.user_id)
    
    # Log kaydı
    Log.log_action(
        action=Log.TYPE_SCREEN_DISABLED,
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={
            "screen_id": screen_id,
            "screen_name": screen.name,
            "owner_id": screen.user_id,
            "reason": reason
        }
    )
    
    # Email bildirim gönder
    if user:
        from app.utils.email import send_screen_status_change_notification
        send_screen_status_change_notification(
            email=user.email,
            name=user.name,
            screen_name=screen.name,
            screen_code=screen.code,
            new_status='inactive',
            screen_location=screen.location,
            reason=reason
        )
    
    flash('Ekran başarıyla devre dışı bırakıldı.', 'success')
    return redirect(url_for('admin.view_screen', screen_id=screen_id))

@bp.route('/media')
@admin_required
def media():
    """Medya listesi sayfası"""
    media_list = Media.find_all()
    
    # Her medya için kullanıcı bilgilerini ekleyelim
    for media in media_list:
        if media.get('user_id'):
            user = User.find_by_id(media.get('user_id'))
            if user:
                media['user_name'] = user.name
            else:
                media['user_name'] = 'Bilinmeyen Kullanıcı'
        else:
            media['user_name'] = 'Kullanıcı Yok'
    
    # Debug için
    current_app.logger.info(f"Media sayfası: {len(media_list)} adet medya gösteriliyor")
    if media_list:
        current_app.logger.info(f"İlk medya örneği: {media_list[0]}")
    
    # Onay bekleyen medya sayısını hesapla
    pending_media_count = Media.count_pending() if hasattr(Media, 'count_pending') else 0
    
    return render_template('admin/media.html', media_list=media_list, pending_media_count=pending_media_count)

@bp.route('/media/view/<media_id>')
@admin_required
def view_media(media_id):
    """Medya detay sayfası"""
    media = Media.find_by_id(media_id)
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('admin.media'))
    
    # Dictionary tipindeki medya verisi için doğru erişim şekli
    user = User.find_by_id(media.get('user_id'))
    
    # Bu medyanın atandığı ekranları getir
    screen_media_relations = ScreenMedia.find_by_media(media_id)
    
    # Ekran detaylarını al
    assigned_screens = []
    for relation in screen_media_relations:
        screen = Screen.find_by_id(relation.screen_id)
        if screen:
            # Ekran bilgilerine ilişki bilgilerini ekle
            screen_dict = screen.to_dict()
            screen_dict['screen_media_id'] = relation.id
            screen_dict['order'] = relation.order
            screen_dict['display_time'] = relation.display_time
            assigned_screens.append(screen_dict)
    
    return render_template('admin/view_media.html', 
                          media=media, 
                          user=user, 
                          assigned_screens=assigned_screens)

@bp.route('/media/approve/<media_id>', methods=['POST'])
@admin_required
def approve_media(media_id):
    """Medya onaylama"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('admin.media'))
    
    # Medyayı onayla - sınıf metodunu doğru parametrelerle çağır
    Media.update(media_id, {'status': Media.STATUS_ACTIVE})
    
    # Kullanıcı bilgilerini getir
    user = User.find_by_id(media.get('user_id'))
    
    # Log kaydı
    Log.log_action(
        action=Log.TYPE_MEDIA_APPROVE,
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={
            "media_id": media_id,
            "media_title": media.get('title'),
            "media_type": media.get('file_type'),
            "owner_id": media.get('user_id')
        }
    )
    
    # Email bildirim gönder
    if user:
        from app.utils.email import send_media_approval_notification
        send_media_approval_notification(
            email=user.email,
            name=user.name,
            media_title=media.get('title'),
            media_type=media.get('file_type', ''),
            preview_url=url_for('user.view_media', media_id=media_id, _external=True)
        )
    
    flash('Medya başarıyla onaylandı.', 'success')
    
    # Yönlendirme
    referer = request.referrer
    if referer and '/view_media/' in referer:
        return redirect(referer)
    else:
        return redirect(url_for('admin.media'))

@bp.route('/media/reject/<media_id>', methods=['POST'])
@admin_required
def reject_media(media_id):
    """Medya reddetme"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('admin.media'))
    
    # Red sebebi
    reason = request.form.get('reason', 'İçerik politikamıza uygun değil')
    
    # Medyayı reddet
    Media.update(media_id, {'status': Media.STATUS_INACTIVE})
    
    # Kullanıcı bilgilerini getir
    user = User.find_by_id(media.get('user_id'))
    
    # Log kaydı
    Log.log_action(
        action=Log.TYPE_MEDIA_REJECT,
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={
            "media_id": media_id,
            "media_title": media.get('title'),
            "media_type": media.get('file_type'),
            "owner_id": media.get('user_id'),
            "reason": reason
        }
    )
    
    # Email bildirim gönder
    if user:
        from app.utils.email import send_media_rejection_notification
        send_media_rejection_notification(
            email=user.email,
            name=user.name,
            media_title=media.get('title'),
            media_type=media.get('file_type', ''),
            rejection_reason=reason
        )
    
    flash('Medya başarıyla reddedildi.', 'success')
    
    # Yönlendirme
    referer = request.referrer
    if referer and '/view_media/' in referer:
        return redirect(referer)
    else:
        return redirect(url_for('admin.media'))

@bp.route('/media/delete/<media_id>', methods=['POST'])
@admin_required
def delete_media(media_id):
    """Medya silme"""
    media = Media.find_by_id(media_id)
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('admin.media'))
    
    # Media.delete metodunu kullanarak sil
    if Media.delete(media_id):
        Log.log_action(
            action=Log.TYPE_MEDIA_DELETE,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={
                "media_id": media_id, 
                "filename": media.get('filename'), 
                "user_id": media.get('user_id')
            }
        )
        flash('Medya başarıyla silindi.', 'success')
    else:
        flash('Medya silinirken bir hata oluştu.', 'danger')
        
    return redirect(url_for('admin.media'))

@bp.route('/logs')
@admin_required
def logs():
    """Log listeleme sayfası"""
    logs = Log.find_latest(200)
    return render_template('admin/logs.html', logs=logs)

@bp.route('/screens/assign_media/<screen_id>', methods=['POST'])
@admin_required
def assign_media_to_screen(screen_id):
    """Ekrana medya atama"""
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('admin.screens'))
    
    media_id = request.form.get('media_id')
    display_time = request.form.get('display_time')
    
    if not media_id:
        flash('Medya seçilmedi.', 'danger')
        return redirect(url_for('admin.view_screen', screen_id=screen_id))
    
    # Medya aktif mi kontrol et
    media = Media.find_by_id(media_id)
    if not media or media.status != Media.STATUS_ACTIVE:
        flash('Medya aktif değil veya bulunamadı.', 'danger')
        return redirect(url_for('admin.view_screen', screen_id=screen_id))
    
    # Sırayı belirle (mevcut son medyadan sonra)
    screen_media_list = ScreenMedia.find_by_screen(screen_id)
    order = len(screen_media_list)
    
    # Display_time'ı sayıya çevir
    try:
        display_time = int(display_time) if display_time else None
    except ValueError:
        display_time = None
    
    # Ekran-medya ilişkisi oluştur
    ScreenMedia.create(
        screen_id=screen_id,
        media_id=media_id,
        order=order,
        display_time=display_time
    )
    
    Log.log_action(
        action="screen_media_assign",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={"screen_id": screen_id, "media_id": media_id}
    )
    
    flash('Medya ekrana başarıyla atandı.', 'success')
    return redirect(url_for('admin.view_screen', screen_id=screen_id))

@bp.route('/screens/remove_media/<screen_id>/<media_id>', methods=['POST'])
@admin_required
def remove_media_from_screen(screen_id, media_id):
    """Ekrandan medya kaldırma"""
    # Ekran ve medya kontrolü
    screen = Screen.find_by_id(screen_id)
    media = Media.find_by_id(media_id)
    
    if not screen or not media:
        flash('Ekran veya medya bulunamadı.', 'danger')
        return redirect(url_for('admin.screens'))
    
    # İlişkiyi kaldır
    ScreenMedia.remove_from_screen(screen_id, media_id)
    
    # Sıralamayı yeniden düzenle
    screen_media_list = ScreenMedia.find_by_screen(screen_id)
    media_order = []
    for i, relation in enumerate(sorted(screen_media_list, key=lambda x: x.order)):
        media_order.append({"media_id": relation.media_id, "order": i})
    
    if media_order:
        ScreenMedia.reorder_screen_media(screen_id, media_order)
    
    Log.log_action(
        action="screen_media_remove",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={"screen_id": screen_id, "media_id": media_id}
    )
    
    flash('Medya ekrandan kaldırıldı.', 'success')
    return redirect(url_for('admin.view_screen', screen_id=screen_id))

@bp.route('/screens/reorder_media/<screen_id>', methods=['POST'])
@admin_required
def reorder_screen_media(screen_id):
    """Ekrandaki medyaları yeniden sıralama"""
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('admin.screens'))
    
    # JSON formatındaki sıralama verilerini al
    media_order = request.json.get('media_order', [])
    
    if not media_order:
        return jsonify({"status": "error", "message": "Sıralama bilgisi eksik"}), 400
    
    # Sıralamayı güncelle
    try:
        ScreenMedia.reorder_screen_media(screen_id, media_order)
        
        Log.log_action(
            action="screen_media_reorder",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"screen_id": screen_id}
        )
        
        return jsonify({"status": "success", "message": "Sıralama güncellendi"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/profile')
@admin_required
def profile():
    """Yönetici profil sayfası"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Kullanıcı istatistikleri
    total_screens = Screen.count()
    total_media = Media.count()
    active_media = Media.count(status=Media.STATUS_ACTIVE)
    total_views = 0  # Tüm görüntülenmeleri hesapla
    for media in Media.find_all():
        total_views += media.view_count if hasattr(media, 'view_count') and media.view_count else 0
    
    stats = {
        'total_screens': total_screens,
        'total_media': total_media,
        'active_media': active_media,
        'total_views': total_views
    }
    
    # Bildirim ayarları
    notifications = {
        'email': True,
        'media_approval': True,
        'screen_status': True,
        'new_user': True
    }
    
    return render_template('admin/profile.html', user=user, stats=stats, notifications=notifications)

@bp.route('/update_profile', methods=['POST'])
@admin_required
def update_profile():
    """Profil bilgilerini güncelle"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    
    # Alanlar boş mu kontrolü
    if not name or not email:
        flash('Ad Soyad ve E-posta alanları gereklidir.', 'danger')
        return redirect(url_for('admin.profile'))
    
    # Email başka bir kullanıcı tarafından kullanılıyor mu?
    if email != user.email:
        existing_user = User.find_by_email(email)
        if existing_user and existing_user.id != user.id:
            flash('Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor.', 'danger')
            return redirect(url_for('admin.profile'))
    
    # Kullanıcı bilgilerini güncelle
    user.update(
        name=name,
        email=email
    )
    
    Log.log_action(
        action="profile_update",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={"fields": ["name", "email"]}
    )
    
    flash('Profil bilgileriniz başarıyla güncellendi.', 'success')
    return redirect(url_for('admin.profile'))

@bp.route('/change_password', methods=['POST'])
@admin_required
def change_password():
    """Şifre değiştirme"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Alanlar boş mu kontrolü
    if not current_password or not new_password or not confirm_password:
        flash('Tüm şifre alanları gereklidir.', 'danger')
        return redirect(url_for('admin.profile'))
    
    # Mevcut şifre doğru mu?
    if not user.verify_password(current_password):
        flash('Mevcut şifre yanlış.', 'danger')
        return redirect(url_for('admin.profile'))
    
    # Yeni şifreler eşleşiyor mu?
    if new_password != confirm_password:
        flash('Yeni şifreler eşleşmiyor.', 'danger')
        return redirect(url_for('admin.profile'))
    
    # Şifre uzunluğu kontrolü
    if len(new_password) < 6:
        flash('Şifre en az 6 karakter uzunluğunda olmalıdır.', 'danger')
        return redirect(url_for('admin.profile'))
    
    # Şifreyi güncelle
    user.update_password(new_password)
    
    Log.log_action(
        action="password_change",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={}
    )
    
    flash('Şifreniz başarıyla değiştirildi.', 'success')
    return redirect(url_for('admin.profile'))

@bp.route('/update_notification_settings', methods=['POST'])
@admin_required
def update_notification_settings():
    """Bildirim ayarlarını güncelleme"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Form verilerini al
    email_notifications = 'email_notifications' in request.form
    media_approval_notifications = 'media_approval_notifications' in request.form
    screen_status_notifications = 'screen_status_notifications' in request.form
    new_user_notifications = 'new_user_notifications' in request.form
    
    # Bildirim ayarlarını güncelle (gelecekte gerekirse)
    notification_settings = {
        'email': email_notifications,
        'media_approval': media_approval_notifications,
        'screen_status': screen_status_notifications,
        'new_user': new_user_notifications
    }
    
    # MongoDB'ye kaydetme işlemi burada yapılabilir
    # user.update(notification_settings=notification_settings)
    
    Log.log_action(
        action="notification_settings_update",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details=notification_settings
    )
    
    flash('Bildirim ayarlarınız başarıyla güncellendi.', 'success')
    return redirect(url_for('admin.profile'))

@bp.route('/regenerate_api_key', methods=['POST'])
@admin_required
def regenerate_api_key():
    """API anahtarını yenileme"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.dashboard'))
    
    # Yeni API anahtarı oluştur
    import uuid
    new_api_key = str(uuid.uuid4())
    
    # Kullanıcının API anahtarını güncelle
    user.update(api_key=new_api_key)
    
    Log.log_action(
        action="api_key_regenerate",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={}
    )
    
    flash('API anahtarınız başarıyla yenilendi.', 'success')
    return redirect(url_for('admin.profile'))

@bp.route('/users/<user_id>/assign-supervisor', methods=['POST'])
@admin_required
def assign_supervisor(user_id):
    """Kullanıcıya denetmen (supervisor) atama"""
    user = User.find_by_id(user_id)
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.users'))
    
    supervisor_id = request.form.get('supervisor_id')
    
    # Supervisor ID boş ise, atamayı kaldır
    if not supervisor_id or supervisor_id == "":
        user.update(supervisor_id=None)
        flash('Kullanıcının denetmen ataması kaldırıldı.', 'success')
        
        Log.log_action(
            action="user_unassign_supervisor",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"user_id": user.id, "user_name": user.name}
        )
    else:
        # Atanacak supervisor'ın varlığını kontrol et
        supervisor = User.find_by_id(supervisor_id)
        if not supervisor:
            flash('Seçilen denetmen bulunamadı.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user.id))
            
        # Supervisor rolünü kontrol et
        if not supervisor.is_supervisor() and not supervisor.is_admin():
            flash('Seçilen kullanıcı denetmen yetkisine sahip değil.', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user.id))
        
        # Kullanıcıya supervisor ata
        user.update(supervisor_id=supervisor_id)
        flash(f'Kullanıcıya denetmen olarak {supervisor.name} atandı.', 'success')
        
        Log.log_action(
            action="user_assign_supervisor",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={
                "user_id": user.id, 
                "user_name": user.name,
                "supervisor_id": supervisor.id,
                "supervisor_name": supervisor.name
            }
        )
    
    return redirect(url_for('admin.edit_user', user_id=user.id))

@bp.route('/media/upload', methods=['GET', 'POST'])
@admin_required
def upload_media():
    """Admin medya yükleme sayfası"""
    if request.method == 'POST':
        try:
            # Form verilerini al
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            display_time = request.form.get('display_time', '10')
            is_public = True if request.form.get('is_public') == 'on' else False
            assign_to_user = request.form.get('assign_to_user')
            
            # Dosya kontrolü
            if 'file' not in request.files:
                flash('Dosya seçilmedi.', 'danger')
                return redirect(request.url)
                
            file = request.files['file']
            
            if file.filename == '':
                flash('Dosya seçilmedi.', 'danger')
                return redirect(request.url)
            
            # Dosya türünü kontrol et
            from werkzeug.utils import secure_filename
            import uuid
            
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'webm', 'mov'}
            file_extension = file.filename.rsplit('.', 1)[1].lower()
            
            if file_extension not in allowed_extensions:
                flash('Bu dosya türü desteklenmiyor.', 'danger')
                return redirect(request.url)
            
            # Dosya türünü belirle
            if file_extension in ['jpg', 'jpeg', 'png', 'gif']:
                file_type = 'image'
            else:
                file_type = 'video'
            
            # Admin tarafından yüklenen medya için kullanıcı ID'si admin ID'si olur
            user_id = session['user_id']
            
            # Admin yüklediği için otomatik onaylı olacak
            status = Media.STATUS_ACTIVE
            
            # Medya oluştur
            media_data = {
                'title': title,
                'description': description,
                'category': category,
                'display_time': display_time,
                'status': status,
                'is_public': is_public,
                'user_id': user_id
            }
            
            # Medya oluştur - burada dosya yalnızca bir kez okunur ve kaydedilir
            media = Media.create(data=media_data, file=file)
            
            # Log kaydı
            Log.log_action(
                action=Log.TYPE_MEDIA_CREATE,
                user_id=user_id,
                ip_address=request.remote_addr,
                details={
                    "media_id": str(media['_id']),
                    "title": title,
                    "file_type": file_type,
                    "is_public": is_public
                }
            )
            
            # Eğer bir kullanıcıya atanması isteniyorsa
            if assign_to_user:
                # Yeni MediaShare kullanarak paylaşım kaydı oluştur
                from app.models.media import MediaShare
                if MediaShare.create(
                    media_id=str(media['_id']), 
                    user_id=assign_to_user, 
                    assigned_by=user_id
                ):
                    flash(f'Medya başarıyla yüklendi ve kullanıcıya atandı.', 'success')
                    # Log kaydı
                    Log.log_action(
                        action=Log.TYPE_MEDIA_ASSIGN_TO_USER,
                        user_id=user_id,
                        ip_address=request.remote_addr,
                        details={
                            "media_id": str(media['_id']),
                            "title": title,
                            "assigned_to": assign_to_user
                        }
                    )
                else:
                    flash(f'Medya yüklendi, ancak kullanıcıya atanırken bir hata oluştu.', 'warning')
            else:
                flash(f'Medya başarıyla yüklendi.', 'success')
            
            return redirect(url_for('admin.media'))
            
        except ValueError as e:
            flash(f'Hata: {str(e)}', 'danger')
            return redirect(request.url)
        except Exception as e:
            flash(f'Beklenmeyen bir hata oluştu: {str(e)}', 'danger')
            return redirect(request.url)
        
    # GET isteği için kullanıcı listesini getir
    users = User.find_all(role=User.ROLE_USER)
    
    return render_template('admin/upload_media.html', users=users)

@bp.route('/media/make_public/<media_id>', methods=['POST'])
@admin_required
def make_media_public(media_id):
    """Medyayı herkese açık hale getir"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('admin.media'))
    
    # Medyayı public yap
    Media.update(media_id, {'is_public': True})
    
    # Log kaydı
    Log.log_action(
        action="media_make_public",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={
            "media_id": media_id,
            "media_title": media.get('title'),
            "media_type": media.get('file_type')
        }
    )
    
    flash('Medya başarıyla herkese açık hale getirildi.', 'success')
    
    # Yönlendirme
    referer = request.referrer
    if referer and '/view_media/' in referer:
        return redirect(referer)
    else:
        return redirect(url_for('admin.media'))

@bp.route('/media/make_private/<media_id>', methods=['POST'])
@admin_required
def make_media_private(media_id):
    """Medyayı özel hale getir"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('admin.media'))
    
    # Medyayı private yap
    Media.update(media_id, {'is_public': False})
    
    # Log kaydı
    Log.log_action(
        action="media_make_private",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={
            "media_id": media_id,
            "media_title": media.get('title'),
            "media_type": media.get('file_type')
        }
    )
    
    flash('Medya başarıyla özel hale getirildi.', 'success')
    
    # Yönlendirme
    referer = request.referrer
    if referer and '/view_media/' in referer:
        return redirect(referer)
    else:
        return redirect(url_for('admin.media'))

@bp.route('/api/admin/users-list')
@admin_required
def api_users_list():
    """Kullanıcı listesini JSON olarak döndürür (JavaScript için API)"""
    users = User.find_all(role=User.ROLE_USER)
    users_list = []
    
    for user in users:
        users_list.append({
            "id": str(user.id),
            "name": user.name,
            "email": user.email
        })
    
    return jsonify({"users": users_list})

@bp.route('/media/assign-to-user', methods=['POST'])
@admin_required
def assign_media_to_user():
    """Medyayı belirli bir kullanıcıya ata"""
    media_id = request.form.get('media_id')
    user_id = request.form.get('assign_user_id')
    
    if not media_id or not user_id:
        flash('Kullanıcı veya medya seçilmedi.', 'danger')
        return redirect(url_for('admin.media'))
    
    # Medya ve kullanıcıyı kontrol et
    media = Media.find_by_id(media_id)
    user = User.find_by_id(user_id)
    
    if not media or not user:
        flash('Medya veya kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.media'))
    
    # MediaShare modeli ile medyayı kullanıcıya ata
    from app.models.media import MediaShare
    admin_id = session['user_id']
    
    try:
        if MediaShare.create(media_id=media_id, user_id=user_id, assigned_by=admin_id):
            # Log kaydı
            Log.log_action(
                action=Log.TYPE_MEDIA_ASSIGN_TO_USER,
                user_id=admin_id,
                ip_address=request.remote_addr,
                details={
                    "media_id": media_id,
                    "user_id": user_id,
                    "media_title": media.get('title')
                }
            )
            
            flash(f'Medya başarıyla {user.name} kullanıcısına atandı.', 'success')
        else:
            flash('Medya atanırken bir hata oluştu.', 'danger')
    except Exception as e:
        flash(f'Hata: {str(e)}', 'danger')
    
    return redirect(url_for('admin.view_media', media_id=media_id)) 

@bp.route('/users/view_screens/<user_id>')
@admin_required
def view_user_screens(user_id):
    """Kullanıcının ekranlarını detaylı bir şekilde görüntüler"""
    # Kullanıcı bilgilerini al
    user = User.find_by_id(user_id)
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('admin.users'))
    
    # Kullanıcının ekranlarını ve ilişkili detayları al
    screens_data = get_user_screens_detail(user_id)
    
    # Detay sayfasını render et
    return render_template(
        'admin/user_screens.html',
        user=user,
        screens_data=screens_data
    )

@bp.route('/api/admin/screen-details/<screen_id>')
@admin_required
def api_screen_details(screen_id):
    """Ekran detaylarını JSON formatında döner"""
    try:
        # Gelişmiş ekran detaylarını al
        screen_details = get_screen_detail(screen_id)
        if not screen_details:
            return jsonify({"error": "Ekran bulunamadı"}), 404
            
        return jsonify(screen_details)
    except Exception as e:
        current_app.logger.error(f"API ekran detayları hatası: {str(e)}")
        return jsonify({"error": str(e)}), 500

##################################################
# PLAYLIST YÖNETİMİ 
##################################################

@bp.route('/playlists')
@admin_required
def admin_playlists():
    """Admin - Tüm playlistleri listeler"""
    from app.models.playlist import Playlist
    from app.models.user import User
    from app.models.playlist_media import PlaylistMedia
    from app.models.screen_playlist import ScreenPlaylist
    
    # Tüm playlistleri getir
    playlists = Playlist.find_all()
    
    # Playlistler için kullanıcı bilgisi ve medya sayısını ekle
    for playlist in playlists:
        # Kullanıcı adını ekle
        user_id = playlist.user_id
        user = User.find_by_id(user_id)
        playlist.user_name = user.name if user else "Bilinmiyor"
        
        # Medya sayısını ekle
        playlist_media = PlaylistMedia.find_by_playlist(playlist.id)
        playlist.media_count = len(playlist_media) if playlist_media else 0
        
        # Playlist'in atandığı ekran sayısını ekle
        try:
            screen_playlists = ScreenPlaylist.find_by_playlist_id(playlist.id)
            playlist.screen_count = len(screen_playlists) if screen_playlists else 0
        except Exception as e:
            current_app.logger.error(f"Ekran sayısı alınırken hata: {str(e)}")
            playlist.screen_count = 0
    
    return render_template('admin/playlists.html', playlists=playlists)

@bp.route('/playlists/view/<playlist_id>')
@admin_required
def view_playlist(playlist_id):
    """Admin - Playlist detayı"""
    from app.models.playlist import Playlist
    from app.models.playlist_media import PlaylistMedia
    from app.models.media import Media
    from app.models.screen_playlist import ScreenPlaylist
    from app.models.screen import Screen
    
    # Playlist'i getir
    playlist = Playlist.find_by_id(playlist_id)
    
    if not playlist:
        flash('Playlist bulunamadı.', 'danger')
        return redirect(url_for('admin.admin_playlists'))
    
    # Kullanıcı bilgisini ekle
    from app.models.user import User
    user_id = playlist.user_id
    user = User.find_by_id(user_id)
    playlist.user_name = user.name if user else "Bilinmiyor"
    
    # Playlist'e ait medyaları getir
    playlist_media_relations = PlaylistMedia.find_by_playlist(playlist_id)
    media_list = []
    
    for relation in playlist_media_relations:
        # PlaylistMedia sözlük olarak döndüğü için, media_id'ye sözlük erişimi ile ulaşacağız
        media_id = relation['media_id'] if isinstance(relation, dict) else relation.media_id
        media = Media.find_by_id(media_id)
        if media:
            # media bir nesne veya sözlük olabilir
            if isinstance(media, dict):
                # Eğer sözlük ise, doğrudan media sözlüğünü kullan
                media_dict = media.copy()
                # _id'yi id'ye çevir
                media_dict['id'] = str(media['_id'])
            else:
                # Eğer nesne ise, to_dict metodunu kullan
                media_dict = media.to_dict() if hasattr(media, 'to_dict') else dict(media)
                media_dict['id'] = media.id

            # Sıralama bilgisini ekle
            media_dict['order'] = relation['order'] if isinstance(relation, dict) else relation.order
            media_list.append(media_dict)
    
    # Playlist'in atandığı ekranları getir
    try:
        # find_by_playlist yerine find_by_playlist_id kullanılmalı
        screen_playlists = ScreenPlaylist.find_by_playlist_id(playlist_id)
        screens = []
        
        for sp in screen_playlists:
            # ScreenPlaylist için de aynı kontrolü yapalım
            screen_id = sp['screen_id'] if isinstance(sp, dict) else sp.screen_id
            screen = Screen.find_by_id(screen_id)
            if screen:
                screens.append(screen)
    except Exception as e:
        current_app.logger.error(f"Ekranları getirirken hata: {str(e)}")
        screens = []
    
    return render_template('admin/view_playlist.html', 
                          playlist=playlist, 
                          media_list=sorted(media_list, key=lambda x: x['order']),
                          screens=screens) 