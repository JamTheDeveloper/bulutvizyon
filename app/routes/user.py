from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.models.user import User
from app.models.screen import Screen
from app.models.media import Media, MediaShare
from app.models.logs import Log
from app.models.screen_content import ScreenContent
import os
import uuid
import datetime
from werkzeug.utils import secure_filename
from PIL import Image
from functools import wraps
import time
from flask_login import login_required, current_user
from app.utils.decorators import user_required, supervisor_required
from app import mongo
import math
from pymongo import MongoClient
from bson.objectid import ObjectId

bp = Blueprint('user', __name__)

def login_required(f):
    """Giriş yapılmış mı kontrolü yapan decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/guide')
def guide():
    """Kullanım kılavuzu sayfası - herkes erişebilir"""
    return render_template('user/guide.html')

@bp.route('/dashboard')
@user_required
def dashboard():
    """Kullanıcı ana sayfası"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    # User kontrolü
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Kullanıcının ekranlarını ve medyalarını getir
    screens = Screen.find_by_user(user_id)
    media_items = Media.find_by_user(user_id)
    
    # Görüntülenecek istatistikler
    media_count = len(media_items)
    screen_count = len(screens)
    pending_media_count = sum(1 for m in media_items if hasattr(m, 'status') and m.status == Media.STATUS_PENDING)
    active_media_count = sum(1 for m in media_items if hasattr(m, 'status') and m.status == Media.STATUS_ACTIVE)
    
    # Kullanıcının paket bilgisine göre izin verilen ekran sayısı
    allowed_screen_count = 3  # Varsayılan olarak (Standart paket)
    if hasattr(user, 'package') and user.package:
        package = user.package
        if package == 'standard':
            allowed_screen_count = 3
        elif package == 'pro':
            allowed_screen_count = 10
        elif package == 'enterprise':
            allowed_screen_count = 999  # Sınırsız temsili
    
    # Kullanıcının paket bilgisini getir
    # NOT: Paket modeli kaldırıldı, paket bilgisi doğrudan kullanıcı nesnesinden alınıyor
    user_package = {
        "display_name": user.package.capitalize() if hasattr(user, 'package') and user.package else "Standart",
        "description": f"{user.package.capitalize() if hasattr(user, 'package') and user.package else 'Standart'} paket ile {allowed_screen_count} ekran kullanabilirsiniz."
    }
    
    # Son eklenen medyalar (en fazla 5 adet)
    recent_media = sorted(media_items, key=lambda x: x.created_at if hasattr(x, 'created_at') else datetime.datetime.now(), reverse=True)[:5]
    
    # Kullanıcının toplam görüntülenme sayısı
    total_views = 0
    for media in media_items:
        total_views += media.views if hasattr(media, 'views') and media.views else 0
    
    # Aktif ekran sayısı
    active_screens_count = sum(1 for screen in screens if hasattr(screen, 'status') and screen.status == Screen.STATUS_ACTIVE)
    
    # Kullanıcının playlistlerini getir
    from app.models.playlist import Playlist
    playlists = Playlist.find_by_user(user_id, status=Playlist.STATUS_ACTIVE)
    
    return render_template('user/dashboard.html', 
                          user=user,
                          screens=screens[:5],  # Son 5 ekran
                          recent_media=recent_media,  # Son 5 medya
                          media_count=media_count,
                          screen_count=screen_count,
                          pending_media_count=pending_media_count,
                          active_media_count=active_media_count,
                          allowed_screen_count=allowed_screen_count,
                          total_views=total_views,
                          active_screens_count=active_screens_count,
                          playlists=playlists[:5])  # Son 5 playlist

@bp.route('/profile')
@user_required
def profile():
    """Kullanıcı profil sayfası"""
    try:
        user_id = session['user_id']
        user = User.find_by_id(user_id)
        
        if not user:
            flash('Kullanıcı bulunamadı.', 'danger')
            return redirect(url_for('auth.logout'))
        
        # Kullanıcı istatistikleri
        total_screens = len(Screen.find_by_user(user_id))
        media_items = Media.find_by_user(user_id)
        total_media = len(media_items)
        active_media = sum(1 for m in media_items if hasattr(m, 'status') and m.status == Media.STATUS_ACTIVE)
        
        # Görüntülenme sayısı
        total_views = 0
        for media in media_items:
            total_views += media.views if hasattr(media, 'views') and media.views else 0
        
        stats = {
            'total_screens': total_screens,
            'total_media': total_media,
            'active_media': active_media,
            'total_views': total_views
        }
        
        # Kullanım istatistikleri
        # Paket bilgisi - gerçek değerler yerine örnek değerler
        max_screens = 5
        max_media = 100
        storage_limit = "1 GB"  # Varsayılan olarak
        
        if hasattr(user, 'package') and user.package:
            package = user.package
            if isinstance(package, dict):
                max_screens = package.get('max_screens', max_screens)
                max_media = package.get('max_media', max_media) 
                storage_limit = package.get('storage_limit', storage_limit)
            elif hasattr(package, 'max_screens'):
                max_screens = package.max_screens
                max_media = package.max_media if hasattr(package, 'max_media') else max_media
                storage_limit = package.storage_limit if hasattr(package, 'storage_limit') else storage_limit
        
        # Depolama kullanımı
        storage_used = 0
        for media in media_items:
            file_size = media.file_size if hasattr(media, 'file_size') and media.file_size else 0
            storage_used += file_size
        
        # MB cinsinden depolama
        storage_used_mb = storage_used / (1024 * 1024)
        storage_limit_mb = 1024  # Varsayılan olarak 1 GB
        
        try:
            if isinstance(storage_limit, str) and "GB" in storage_limit:
                storage_limit_mb = float(storage_limit.replace("GB", "").strip()) * 1024
            elif isinstance(storage_limit, str) and "MB" in storage_limit:
                storage_limit_mb = float(storage_limit.replace("MB", "").strip())
        except:
            pass
        
        # Yüzdelik kullanım
        storage_percentage = min(int((storage_used_mb / storage_limit_mb) * 100), 100) if storage_limit_mb > 0 else 0
        screen_percentage = min(int((total_screens / max_screens) * 100), 100) if max_screens > 0 else 0
        media_percentage = min(int((total_media / max_media) * 100), 100) if max_media > 0 else 0
        
        usage_stats = {
            "storage_used": f"{storage_used_mb:.1f} MB",
            "storage_limit": f"{storage_limit_mb} MB",
            "storage_percentage": storage_percentage,
            "screens_used": total_screens,
            "max_screens": max_screens,
            "screen_percentage": screen_percentage,
            "media_used": total_media,
            "max_media": max_media,
            "media_percentage": media_percentage
        }
        
        # Bildirim ayarları
        notifications = {
            'email': True,
            'media_approval': True,
            'screen_status': True
        }
        
        return render_template('user/profile.html', 
                              user=user,
                              stats=stats,
                              usage_stats=usage_stats,
                              notifications=notifications)
    except Exception as e:
        flash(f'Profil sayfası yüklenirken bir hata oluştu: {str(e)}', 'danger')
        return redirect(url_for('user.dashboard'))

@bp.route('/update_profile', methods=['POST'])
@user_required
def update_profile():
    """Profil bilgilerini güncelle"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('auth.logout'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    
    # Alanlar boş mu kontrolü
    if not name or not email:
        flash('Ad Soyad ve E-posta alanları gereklidir.', 'danger')
        return redirect(url_for('user.profile'))
    
    # Email başka bir kullanıcı tarafından kullanılıyor mu?
    if email != user.email:
        existing_user = User.find_by_email(email)
        if existing_user and existing_user.id != user.id:
            flash('Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor.', 'danger')
            return redirect(url_for('user.profile'))
    
    # Kullanıcı bilgilerini güncelle
    user.update(
        name=name,
        email=email,
        phone=phone
    )
    
    Log.log_action(
        action="profile_update",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={"fields": ["name", "email", "phone"]}
    )
    
    flash('Profil bilgileriniz başarıyla güncellendi.', 'success')
    return redirect(url_for('user.profile'))

@bp.route('/change_password', methods=['POST'])
@user_required
def change_password():
    """Şifre değiştirme"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('auth.logout'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Alanlar boş mu kontrolü
    if not current_password or not new_password or not confirm_password:
        flash('Tüm şifre alanları gereklidir.', 'danger')
        return redirect(url_for('user.profile'))
    
    # Mevcut şifre doğru mu?
    if not user.verify_password(current_password):
        flash('Mevcut şifre yanlış.', 'danger')
        return redirect(url_for('user.profile'))
    
    # Yeni şifreler eşleşiyor mu?
    if new_password != confirm_password:
        flash('Yeni şifreler eşleşmiyor.', 'danger')
        return redirect(url_for('user.profile'))
    
    # Şifre uzunluğu kontrolü
    if len(new_password) < 6:
        flash('Şifre en az 6 karakter uzunluğunda olmalıdır.', 'danger')
        return redirect(url_for('user.profile'))
    
    # Şifreyi güncelle
    user.update_password(new_password)
    
    Log.log_action(
        action="password_change",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={}
    )
    
    flash('Şifreniz başarıyla değiştirildi.', 'success')
    return redirect(url_for('user.profile'))

@bp.route('/update_notification_settings', methods=['POST'])
@user_required
def update_notification_settings():
    """Bildirim ayarlarını güncelleme"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Form verilerini al
    email_notifications = 'email_notifications' in request.form
    media_approval_notifications = 'media_approval_notifications' in request.form
    screen_status_notifications = 'screen_status_notifications' in request.form
    
    # Bildirim ayarlarını güncelle (gelecekte gerekirse)
    notification_settings = {
        'email': email_notifications,
        'media_approval': media_approval_notifications,
        'screen_status': screen_status_notifications
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
    return redirect(url_for('user.profile'))

@bp.route('/screens')
@user_required
def screens():
    """Kullanıcının ekran listesi"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    # Kullanıcının ekranlarını getir
    screens_list = Screen.find_by_user(user_id)
    
    # İstatistikler - Screen nesnesine uygun olarak güncellendi
    active_count = sum(1 for screen in screens_list if screen.status == Screen.STATUS_ACTIVE)
    inactive_count = sum(1 for screen in screens_list if screen.status == Screen.STATUS_INACTIVE)
    
    # Paket limitleri için
    screen_count = len(screens_list)
    
    # Kullanıcının paket bilgisini kontrol et
    if not hasattr(user, 'package') or not user.package or user.package not in ['standard', 'pro', 'enterprise']:
        # Paket bilgisi yoksa veya bilinmeyen bir paket ise, varsayılan olarak standart paket ata
        user.update(package='standard')
        allowed_screen_count = 3  # Standart paket için ekran limiti
    else:
        # Paket sözlüğü
        package_limits = {
            'standard': 3,
            'pro': 10,
            'enterprise': 999  # Pratik olarak sınırsız
        }
        allowed_screen_count = package_limits.get(user.package, 3)
    
    return render_template('user/screens.html', 
                          screens=screens_list,
                          active_count=active_count,
                          inactive_count=inactive_count,
                          screen_count=screen_count,
                          allowed_screen_count=allowed_screen_count)

@bp.route('/screens/create', methods=['GET', 'POST'])
@user_required
def create_screen():
    """Ekran oluşturma sayfası"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    screen_count = Screen.count_by_user(user_id)
    
    # Paket limitleri için
    if not hasattr(user, 'package') or not user.package or user.package not in ['standard', 'pro', 'enterprise']:
        allowed_screen_count = 3  # Standart paket için ekran limiti
    else:
        # Paket sözlüğü
        package_limits = {
            'standard': 3,
            'pro': 10,
            'enterprise': 999  # Pratik olarak sınırsız
        }
        allowed_screen_count = package_limits.get(user.package, 3)
    
    if screen_count >= allowed_screen_count:
        flash('Maksimum ekran sayısına ulaştınız.', 'danger')
        return redirect(url_for('user.screens'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        location = request.form.get('location')
        orientation = request.form.get('orientation')
        resolution = request.form.get('resolution')
        
        # Özel çözünürlük kontrolü
        if resolution == 'custom':
            width = request.form.get('width')
            height = request.form.get('height')
            if width and height:
                resolution = f"{width}x{height}"
        
        refresh_rate = int(request.form.get('refresh_rate', 15))
        show_clock = 'show_clock' in request.form
        status = 'status' in request.form
        
        # Screen.create metodunu kullan
        screen_data = {
            'name': name,
            'description': description,
            'location': location,
            'orientation': orientation,
            'resolution': resolution,
            'refresh_rate': refresh_rate,
            'show_clock': show_clock,
            'status': Screen.STATUS_ACTIVE if status else Screen.STATUS_INACTIVE,
            'user_id': session['user_id']
        }
        
        screen = Screen.create(screen_data)
        screen_id = screen['_id']
        
        Log.log_action(
            action=Log.TYPE_SCREEN_CREATE,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"screen_id": str(screen_id), "name": name}
        )
        
        flash('Ekran başarıyla oluşturuldu.', 'success')
        
        # Kullanıcının playlistleri var mı kontrol et
        from app.models.playlist import Playlist
        user_playlists = Playlist.find_by_user(user_id, status=Playlist.STATUS_ACTIVE)
        
        # Playlist varsa içerik yönetim sayfasına, yoksa playlist oluşturma sayfasına yönlendir
        if user_playlists and len(user_playlists) > 0:
            flash('Ekranınıza içerik eklemek için playlist seçebilirsiniz.', 'info')
            return redirect(url_for('user.assign_playlist_to_screen', screen_id=screen_id))
        else:
            flash('Ekranınıza içerik eklemek için önce bir playlist oluşturun.', 'info')
            return redirect(url_for('user.create_playlist'))
    
    return render_template('user/create_screen.html', 
                          screen_count=screen_count, 
                          allowed_screen_count=allowed_screen_count)

@bp.route('/screens/<screen_id>/edit', methods=['GET', 'POST'])
@user_required
def edit_screen(screen_id):
    """Ekran düzenleme"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen:
        flash('Ekran bulunamadı.', 'warning')
        return redirect(url_for('user.screens'))
    
    # Ekranın kullanıcıya ait olup olmadığını kontrol et
    if screen.user_id != session['user_id']:
        flash('Bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        orientation = request.form.get('orientation')
        status = request.form.get('status', 'inactive')
        location = request.form.get('location')
        description = request.form.get('description')
        refresh_rate = request.form.get('refresh_rate', 15)
        show_clock = True if request.form.get('show_clock') else False
        
        # Panel türü ve boyutlar
        screen_type = request.form.get('screen_type')
        panel_type = request.form.get('panel_type')
        width_cm = request.form.get('width_cm')
        height_cm = request.form.get('height_cm')
        
        # Çözünürlük kontrolü
        if request.form.get('resolution') == 'custom':
            width = request.form.get('width')
            height = request.form.get('height')
            resolution = f"{width}x{height}"
        else:
            resolution = request.form.get('resolution')
        
        # Update işlemine panel_type ve boyutları ekle
        update_data = {
            'name': name,
            'orientation': orientation,
            'resolution': resolution,
            'location': location,
            'description': description,
            'status': status,
            'refresh_rate': int(refresh_rate),
            'show_clock': show_clock
        }
        
        # Ekstra alanlar
        if screen_type:
            update_data['screen_type'] = screen_type
        if panel_type:
            update_data['panel_type'] = panel_type
        if width_cm:
            update_data['width_cm'] = float(width_cm)
        if height_cm:
            update_data['height_cm'] = float(height_cm)
            
        # Ekranı güncelle
        screen.update(**update_data)
        
        flash(f'"{name}" ekranı başarıyla güncellendi.', 'success')
        return redirect(url_for('user.screens'))
    
    # Ekran verileri için hazırlık
    screen_data = {
        'id': screen.id,
        'name': screen.name,
        'orientation': screen.orientation,
        'resolution': screen.resolution,
        'location': screen.location or '',
        'description': screen.description or '',
        'status': screen.status,
        'refresh_rate': screen.refresh_rate or 15,
        'show_clock': screen.show_clock,
        'api_key': screen.api_key
    }
    
    # Ekstra alanlar (varsa)
    if hasattr(screen, 'screen_type'):
        screen_data['screen_type'] = screen.screen_type
    if hasattr(screen, 'panel_type'):
        screen_data['panel_type'] = screen.panel_type
    if hasattr(screen, 'width_cm'):
        screen_data['width_cm'] = screen.width_cm
    if hasattr(screen, 'height_cm'):
        screen_data['height_cm'] = screen.height_cm
    
    return render_template('user/edit_screen.html', screen=screen_data)

@bp.route('/screens/delete/<screen_id>', methods=['POST'])
@user_required
def delete_screen(screen_id):
    """Ekran silme"""
    from bson.objectid import ObjectId
    from app.models.screen_content import ScreenContent  # İlişkili içerik modeli
    
    screen = Screen.find_by_id(screen_id)
    
    if not screen:
        flash('Ekran bulunamadı.', 'warning')
        return redirect(url_for('user.screens'))
    
    # Ekranın kullanıcıya ait olup olmadığını kontrol et
    if screen.user_id != session['user_id']:
        flash('Bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    Log.log_action(
        action=Log.TYPE_SCREEN_DELETE,
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={"screen_id": screen_id, "name": screen.name}
    )
    
    try:
        # 1. İlişkili içerikleri doğrudan silelim
        ScreenContent.delete_by_screen(screen_id)
        
        # 2. Ekranı silelim
        if isinstance(screen_id, str):
            try:
                obj_id = ObjectId(screen_id)
            except:
                obj_id = screen_id
        else:
            obj_id = screen_id
            
        # Ekranı sil
        result = mongo.db.screens.delete_one({'_id': obj_id})
        
        if result.deleted_count > 0:
            flash('Ekran başarıyla silindi.', 'success')
        else:
            flash('Ekran silinirken bir hata oluştu.', 'danger')
            
    except Exception as e:
        # Hata logunu yazdır
        import traceback
        print(f"Ekran silme hatası: {str(e)}")
        print(traceback.format_exc())
        flash('Ekran silinirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('user.screens'))

@bp.route('/media')
@login_required
def media():
    """Kullanıcı medya sayfası"""
    from app.models.media import Media, MediaShare
    page = request.args.get('page', 1, type=int)
    limit = 12
    skip = (page - 1) * limit
    
    user_id = session['user_id']
    
    # Filtre parametrelerini al
    media_type = request.args.get('type')
    status = request.args.get('status')
    category = request.args.get('category')
    
    # Kullanıcının medyalarını getir - MediaShare sistemini kullanır
    media_items = Media.find_by_user(user_id, status=status, limit=limit, skip=skip)
    
    # Filtreleme işlemleri
    if media_type:
        media_items = [m for m in media_items if m.get('file_type') == media_type]
    
    if category:
        media_items = [m for m in media_items if m.get('category') == category]
    
    # Toplam medya sayısını getir
    total_count = Media.count_by_user(user_id)
    
    # Sayfalandırma
    total_pages = math.ceil(total_count / limit)
    
    return render_template('user/media.html', 
                          media_list=media_items,  # Burayı media_list olarak düzelttim
                          total_pages=total_pages, 
                          current_page=page,
                          active_page='media')

@bp.route('/media/upload', methods=['GET', 'POST'])
@user_required
def upload_media():
    """Medya yükleme sayfası"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Dosya seçilmedi.', 'danger')
            return render_template('user/upload_media.html')
            
        file = request.files['file']
        
        if file.filename == '':
            flash('Dosya seçilmedi.', 'danger')
            return render_template('user/upload_media.html')
            
        # Dosya boyut kontrolü
        if len(file.read()) > current_app.config['MAX_CONTENT_LENGTH']:
            flash('Dosya boyutu çok büyük.', 'danger')
            return render_template('user/upload_media.html')
            
        # Dosyayı başa sar
        file.seek(0)
        
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        display_time = int(request.form.get('display_time', 10))
        
        # "is_public" değişkeninin adı ile form alanı aynı olmalı
        is_public = True if request.form.get('is_public') == '1' else False
        
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        # Kullanıcı bilgisi
        user = User.find_by_id(session['user_id'])
        
        # Medya durumunu belirle: supervisor yok ise direkt aktif, varsa onay gerekiyor
        media_status = Media.STATUS_ACTIVE if not user.has_supervisor() else Media.STATUS_PENDING
        
        # Media.create metodunu kullanarak medya oluştur
        media_data = {
            'title': title,
            'description': description,
            'category': category,
            'display_time': display_time,
            'is_public': is_public,
            'start_date': start_date,
            'end_date': end_date,
            'user_id': session['user_id'],
            'status': media_status
        }
        
        # Debug bilgisi ekle
        print(f"Medya oluşturuluyor - is_public: {is_public}, form değeri: {request.form.get('is_public')}")
        
        media = Media.create(media_data, file)
        
        Log.log_action(
            action=Log.TYPE_MEDIA_UPLOAD,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"media_id": media.get('_id'), "title": title, "file_type": media.get('file_type')}
        )
        
        if media_status == Media.STATUS_ACTIVE:
            flash('Medya başarıyla yüklendi ve aktif duruma getirildi.', 'success')
        else:
            flash('Medya başarıyla yüklendi ve onay için gönderildi.', 'success')
            
        return redirect(url_for('user.media'))
        
    return render_template('user/upload_media.html')

@bp.route('/media/edit/<media_id>', methods=['GET', 'POST'])
@user_required
def edit_media(media_id):
    """Medya düzenleme sayfası"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('user.media'))
        
    # Kullanıcı ID'lerini string formatında karşılaştır
    if str(media.get('user_id')) != str(session['user_id']):
        # Paylaşılan medya kontrolü
        shared_with_user = MediaShare.media_is_shared_with_user(media_id, session['user_id'])
        if not shared_with_user:
            flash('Bu medyaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('user.media'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        display_time = int(request.form.get('display_time', 10))
        
        # "is_public" değişkeninin adı ile form alanı aynı olmalı
        is_public = True if request.form.get('is_public') == '1' else False
        
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if start_date:
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        if end_date:
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        # Kullanıcı bilgisi
        user = User.find_by_id(session['user_id'])
        
        # Medya durumunu belirle: supervisor yok ise direkt aktif, varsa onay gerekiyor
        media_status = Media.STATUS_ACTIVE if not user.has_supervisor() else Media.STATUS_PENDING
        
        # Medyayı güncelle
        Media.update(media_id, {
            'title': title,
            'description': description,
            'category': category,
            'display_time': display_time,
            'is_public': is_public,
            'start_date': start_date,
            'end_date': end_date,
            'status': media_status,  # Kullanıcının supervisor durumuna göre
            'approved_by': None if media_status == Media.STATUS_PENDING else session['user_id'],
            'approved_at': None if media_status == Media.STATUS_PENDING else datetime.datetime.utcnow()
        })
        
        # Debug bilgisi ekle
        print(f"Medya güncelleniyor - is_public: {is_public}, form değeri: {request.form.get('is_public')}")
        
        if media_status == Media.STATUS_ACTIVE:
            flash('Medya başarıyla güncellendi ve aktif duruma getirildi.', 'success')
        else:
            flash('Medya başarıyla güncellendi ve yeniden onay için gönderildi.', 'success')
            
        return redirect(url_for('user.media'))
    
    return render_template('user/edit_media.html', media=media)

@bp.route('/media/delete/<media_id>', methods=['POST', 'GET'])
@bp.route('/media/delete/<media_id>/', methods=['POST', 'GET'])
@bp.route('/media/delete/', methods=['POST'])
@bp.route('/media/delete', methods=['POST'])
@user_required
def delete_media(media_id=None):
    """Medya silme"""
    # Form'dan veya URL'den media_id al
    from flask import current_app
    form_media_id = request.form.get('media_id')
    force_delete = request.form.get('force_delete') == '1'
    
    current_app.logger.info(f"DELETE_MEDIA ÇAĞRILDI: media_id={media_id}, form_media_id={form_media_id}, force_delete={force_delete}")
    current_app.logger.info(f"REQUEST FORM: {request.form}")
    current_app.logger.info(f"REQUEST METHOD: {request.method}")
    current_app.logger.info(f"REQUEST PATH: {request.path}")
    
    # URL'den gelen media_id'ye öncelik ver, yoksa form'dan al
    if not media_id or media_id == '':
        media_id = form_media_id
    
    # Özel debug log - media_id'nin içeriğini ve türünü kontrol et
    current_app.logger.info(f"MEDIA ID: '{media_id}' - TİP: {type(media_id)}")
    
    # Media ID'yi temizle ve kontrol et
    if isinstance(media_id, str):
        # Boşluk ve diğer sorunlu karakterleri temizle
        media_id = media_id.strip()
        current_app.logger.info(f"Temizlenmiş MEDIA ID: '{media_id}', uzunluk: {len(media_id)}")
        current_app.logger.info(f"MEDIA ID hex karakterleri: {' '.join([hex(ord(c)) for c in media_id])}")
    
    if not media_id or (isinstance(media_id, str) and media_id.strip() == ''):
        current_app.logger.error("HATA: Media ID bulunamadı!")
        flash('Geçersiz medya ID.', 'danger')
        return redirect(url_for('user.media'))
    
    try:
        # Silme işlemi için Media.delete metodu kullanılıyor
        from app.models.media import Media
        from bson.objectid import ObjectId
        
        # ObjectId dönüşümü ve medya bilgilerini al
        try:
            object_id = ObjectId(media_id) if isinstance(media_id, str) else media_id
            media_info = Media.find_by_id(object_id)
            
            if not media_info:
                current_app.logger.warning(f"Silinecek medya bulunamadı: {object_id}")
                flash('Belirtilen medya bulunamadı.', 'warning')
                return redirect(url_for('user.media'))
            
            # Kullanıcı yetkisi kontrolü
            if str(media_info.get('user_id')) != str(session['user_id']):
                current_app.logger.warning(f"Medyayı silmeye çalışan kullanıcının yetkisi yok. Medya sahibi: {media_info.get('user_id')}, İstek yapan: {session['user_id']}")
                flash('Bu medyayı silme yetkiniz yok.', 'danger')
                return redirect(url_for('user.media'))
            
            # Media.delete ile silme işlemini başlat
            current_app.logger.info(f"Media.delete çağrılıyor: {object_id}")
            if Media.delete(object_id):
                current_app.logger.info(f"Medya başarıyla silindi: {object_id}")
                flash('Medya ve tüm ilişkili içerikler başarıyla silindi.', 'success')
            else:
                current_app.logger.error(f"Medya silme işlemi başarısız: {object_id}")
                flash('Medya silinirken bir hata oluştu.', 'danger')
        
        except Exception as e:
            current_app.logger.error(f"Medya silme işleminde hata: {str(e)}")
            import traceback
            current_app.logger.error(traceback.format_exc())
            flash(f'Medya silme işleminde bir hata oluştu: {str(e)}', 'danger')
    
    except Exception as e:
        current_app.logger.error(f"Genel hata: {str(e)}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        flash(f'Medya silme işleminde bir hata oluştu: {str(e)}', 'danger')
    
    return redirect(url_for('user.media'))

@bp.route('/media/view/<media_id>')
@user_required
def view_media(media_id) :
    """Medya önizleme sayfası"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('user.media'))
        
    # Kullanıcı ID'lerini string formatında karşılaştır
    if str(media.get('user_id')) != str(session['user_id']):
        # Paylaşılan medya kontrolü
        shared_with_user = MediaShare.media_is_shared_with_user(media_id, session['user_id'])
        if not shared_with_user and not media.get('is_public'):
            flash('Bu medyaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('user.media'))
    
    file_url = f"/uploads/{media.get('filename')}"
    
    return render_template('user/view_media.html', media=media, file_url=file_url)

@bp.route('/public-library')
@user_required
def public_library():
    """Herkese açık medya kütüphanesi"""
    category = request.args.get('category')
    search = request.args.get('search')
    file_type = request.args.get('type')
    
    # Medya listesini al
    media_list = Media.find_public(limit=100, category=category, search=search)
    
    # Dosya tipine göre filtrele (varsa)
    if file_type:
        media_list = [m for m in media_list if m.get('file_type') == file_type]
    
    # Mevcut kategorileri al
    categories = set()
    for media in media_list:
        if media.get('category'):
            categories.add(media.get('category'))
    
    return render_template(
        'user/public_library.html',
        media_list=media_list,
        categories=sorted(categories),
        selected_category=category
    )

@bp.route('/screens/<screen_id>')
@user_required
def view_screen(screen_id):
    """Ekran detaylarını görüntüle"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        flash('Böyle bir ekran bulunamadı veya bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    from app.models.screen_content import ScreenContent
    screen_content = ScreenContent.find_by_screen_id(screen_id)
    
    return render_template('user/view_screen.html', 
                          screen=screen,
                          screen_content=screen_content)

@bp.route('/screens/<screen_id>/edit', methods=['GET', 'POST'])
@user_required
def edit_screen_content(screen_id):
    """Ekran düzenleme"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        flash('Böyle bir ekran bulunamadı veya bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        orientation = request.form.get('orientation')
        status = 'active' if request.form.get('status') else 'inactive'
        location = request.form.get('location')
        description = request.form.get('description')
        refresh_rate = request.form.get('refresh_rate', 15)
        show_clock = True if request.form.get('show_clock') else False
        
        # Çözünürlük kontrolü
        if request.form.get('resolution') == 'custom':
            width = request.form.get('width')
            height = request.form.get('height')
            resolution = f"{width}x{height}"
        else:
            resolution = request.form.get('resolution')
        
        # Ekranı güncelle
        Screen.update(screen_id, {
            'name': name,
            'orientation': orientation,
            'resolution': resolution,
            'location': location,
            'description': description,
            'status': status,
            'refresh_rate': refresh_rate,
            'show_clock': show_clock
        })
        
        flash(f'"{name}" ekranı başarıyla güncellendi.', 'success')
        return redirect(url_for('user.screens'))
    
    return render_template('user/edit_screen.html', screen=screen)

@bp.route('/screens/<screen_id>/delete', methods=['POST'])
@user_required
def delete_screen_content(screen_id):
    """Ekran silme"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        flash('Böyle bir ekran bulunamadı veya bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    name = screen.name
    Screen.delete(screen_id)
    
    flash(f'"{name}" ekranı ve ilişkili tüm içerikler başarıyla silindi.', 'success')
    return redirect(url_for('user.screens'))

@bp.route('/screens/<screen_id>/preview')
@user_required
def preview_screen(screen_id):
    """Ekran önizleme sayfası"""
    import traceback
    
    try:
        # Ekranı bul
        screen = Screen.find_by_id(screen_id)
        
        if not screen:
            flash('Ekran bulunamadı.', 'warning')
            return redirect(url_for('user.screens'))
        
        # Ekranın kullanıcıya ait olup olmadığını kontrol et
        if screen.user_id != session['user_id']:
            flash('Bu ekrana erişim izniniz yok.', 'danger')
            return redirect(url_for('user.screens'))
        
        # Ekran içeriğini al
        from app.models.screen_content import ScreenContent
        screen_content_list = ScreenContent.find_by_screen_id(screen_id)
        
        print(f"DEBUG - preview_screen: Bulunan içerik sayısı: {len(screen_content_list)}")
        
        # Her içerik için medya bilgilerini ekle
        screen_contents_with_media = []
        for content in screen_content_list:
            try:
                media_id = content.get('media_id')
                print(f"DEBUG - preview_screen: İçerik için medya getiriliyor: {media_id}")
                
                media = Media.find_by_id(media_id)
                if not media:
                    print(f"DEBUG - preview_screen: Medya bulunamadı: {media_id}")
                    continue
                
                # İçerik nesnesine medya bilgisini ekle
                content_with_media = dict(content)
                content_with_media['media'] = media
                screen_contents_with_media.append(content_with_media)
                
                print(f"DEBUG - preview_screen: İçerik eklendi: ID: {content.get('_id')}, Media: {media.get('title')}")
            except Exception as e:
                print(f"DEBUG - preview_screen: İçerik işleme hatası: {str(e)}")
                print(traceback.format_exc())
        
        print(f"DEBUG - preview_screen: İşlenen toplam içerik sayısı: {len(screen_contents_with_media)}")
        
        # Önizleme URL'sini oluştur - str() ile ID'yi stringe çevirelim
        api_key = screen.api_key
        preview_url = url_for('main.viewer', api_key=api_key, _external=True)
        
        return render_template('user/preview_screen.html', 
                            screen=screen, 
                            screen_content=screen_contents_with_media,
                            preview_url=preview_url)
    except Exception as e:
        print(f"DEBUG - preview_screen genel hata: {str(e)}")
        print(traceback.format_exc())
        flash('Önizleme yüklenirken bir hata oluştu.', 'danger')
        return redirect(url_for('user.screens'))

@bp.route('/screens/<screen_id>/regenerate_api_key', methods=['POST'])
@user_required
def regenerate_api_key(screen_id):
    # Ekranı bul
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'warning')
        return redirect(url_for('user.screens'))
    
    # Ekranın kullanıcıya ait olup olmadığını kontrol et
    if screen.user_id != session['user_id']:
        flash('Bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    # Yeni API key oluştur
    import uuid
    new_api_key = str(uuid.uuid4())
    
    # Veritabanında güncelle
    if screen.update(api_key=new_api_key):
        # Log oluştur
        Log.create(
            user_id=session['user_id'],
            action='API anahtarı yenilendi',
            details=f'Ekran ID: {screen_id}',
            ip_address=request.remote_addr
        )
        flash('API anahtarı başarıyla yenilendi.', 'success')
    else:
        flash('API anahtarı yenilenirken bir hata oluştu.', 'danger')
    
    # Eğer önizleme sayfasından geliyorsa, oraya geri dön
    referrer = request.referrer
    if referrer and 'preview' in referrer:
        return redirect(url_for('user.preview_screen', screen_id=screen_id))
    
    # Aksi takdirde içerik yönetimi sayfasına yönlendir
    return redirect(url_for('user.manage_screen_content', screen_id=screen_id))

@bp.route('/screens/<screen_id>/save-content', methods=['POST'])
@user_required
def save_screen_content_order(screen_id):
    # Ekranı bul
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('user.screens'))
    
    # Ekranın kullanıcıya ait olup olmadığını kontrol et
    if screen.user_id != session['user_id']:
        flash('Bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    # İçerik sıralamasını al - JSON veya form verisi olarak gönderilebilir
    content_order = []
    
    if request.is_json:
        # JSON verisi kontrolü
        content_order = request.json.get('content_order', [])
    else:
        # Form verisi kontrolü
        content_ids = request.form.getlist('content_ids[]')
        if content_ids:
            content_order = content_ids
    
    # Her bir içerik için sıra numarasını güncelle
    from app.models.screen_media import ScreenMedia
    success = True
    for index, content_id in enumerate(content_order):
        screen_media = ScreenMedia.find_by_id(content_id)
        if screen_media and screen_media.screen_id == int(screen_id):
            if not screen_media.update(order=index + 1):
                success = False
    
    if success:
        flash('İçerik sıralaması güncellendi.', 'success')
    else:
        flash('İçerik sıralaması güncellenirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('user.manage_screen_content', screen_id=screen_id))

@bp.route('/screens/<screen_id>/content', methods=['GET'])
@user_required
def manage_screen_content(screen_id):
    """Ekran içeriklerini yönetme"""
    import traceback
    
    try:
        print(f"DEBUG - manage_screen_content başladı: screen_id={screen_id}, tip={type(screen_id)}")
        
        # Ekranı kontrol et
        screen = Screen.find_by_id(screen_id)
        print(f"DEBUG - Ekran bulundu mu: {screen is not None}")
        
        if not screen:
            flash('Ekran bulunamadı.', 'danger')
            return redirect(url_for('user.screens'))
        
        # Ekranın kullanıcıya ait olup olmadığını kontrol et
        user_id = session.get('user_id')
        print(f"DEBUG - Oturum user_id: {user_id}, Ekran user_id: {screen.user_id}")
        
        if str(screen.user_id) != str(user_id):
            flash('Bu ekrana erişim izniniz yok.', 'danger')
            return redirect(url_for('user.screens'))
        
        # Ekran içeriklerini getir
        from app.models.screen_content import ScreenContent
        try:
            screen_content_list = ScreenContent.find_by_screen_id(screen_id)
            print(f"DEBUG - Ekran içerikleri bulundu: {len(screen_content_list)}")
        except Exception as e:
            print(f"DEBUG - Ekran içerik getirme hatası: {str(e)}")
            traceback.print_exc()
            screen_content_list = []
        
        # Medya bilgilerini ekle - her content için ilgili medyayı getir
        from app.models.media import Media
        for content in screen_content_list:
            try:
                # İçerik dict yada object olabilir
                if isinstance(content, dict):
                    media_id = content.get('media_id')
                    media = Media.find_by_id(media_id)
                    if media:
                        content['media'] = media
                else:  # Nesne ise
                    media_id = content.media_id if hasattr(content, 'media_id') else None
                    if media_id:
                        media = Media.find_by_id(media_id)
                        if media:
                            content.media = media
            except Exception as e:
                print(f"DEBUG - Medya bilgisi ekleme hatası: {str(e)}")
                traceback.print_exc()
        
        # Kullanıcının tüm medyalarını getir
        try:
            from app.models.media import Media
            user_media = Media.find_by_user(user_id, status=Media.STATUS_ACTIVE)
            print(f"DEBUG - Kullanıcı medyaları bulundu: {len(user_media)}")
        except Exception as e:
            print(f"DEBUG - Kullanıcı medyası getirme hatası: {str(e)}")
            traceback.print_exc()
            user_media = []
        
        # Tüm herkese açık (public) medyaları getir
        try:
            public_media = Media.find_public()
            print(f"DEBUG - Public medyalar bulundu: {len(public_media)}")
        except Exception as e:
            print(f"DEBUG - Public medya getirme hatası: {str(e)}")
            traceback.print_exc()
            public_media = []
        
        # Playlist ekranı var mı kontrol et
        try:
            from app.models.screen_playlist import ScreenPlaylist
            assigned_playlist = None
            screen_playlist = ScreenPlaylist.find_by_screen_id(screen_id)
            
            if screen_playlist:
                # Playlist bilgilerini getir
                from app.models.playlist import Playlist
                assigned_playlist = Playlist.find_by_id(screen_playlist.get('playlist_id'))
                print(f"DEBUG - Atanmış playlist bulundu: {assigned_playlist is not None}")
        except Exception as e:
            print(f"DEBUG - Playlist kontrol hatası: {str(e)}")
            traceback.print_exc()
            assigned_playlist = None
        
        # Kullanıcının playlistlerini getir
        from app.models.playlist import Playlist
        user_playlists = Playlist.find_by_user(session['user_id'], status=Playlist.STATUS_ACTIVE)
        
        # Public playlist'leri getir
        public_playlists = Playlist.find_public()
        
        # Kullanıcının kendi oluşturduğu public playlist'leri filtrele
        public_playlists = [p for p in public_playlists if str(p.user_id) != str(session['user_id'])]
        
        # DENEME P3 playlistini özel olarak bul ve güncelle
        from app.models.playlist_media import PlaylistMedia
        for playlist in user_playlists + public_playlists:
            if 'DENEME P3' in playlist.name:
                print(f"DEBUG - DENEME P3 playlist bulundu: id={playlist.id}, eski media_count={playlist.media_count}")
                # Gerçek medya sayısını hesapla
                media_list = PlaylistMedia.find_by_playlist(playlist.id)
                real_count = len(media_list)
                # Güncelle
                if playlist.media_count != real_count:
                    print(f"DEBUG - Medya sayısını güncelliyorum: {playlist.media_count} -> {real_count}")
                    # Bellek nesnesini güncelle
                    playlist.media_count = real_count
                    # Veritabanını güncelle (çalışmazsa hata vermemesi için ObjectId kontrolünü es geçiyoruz)
                    try:
                        # Direkt MongoDB güncellemesi
                        mongo.db.playlists.update_one(
                            {"$or": [
                                {"_id": playlist.id}, 
                                {"_id": ObjectId(playlist.id) if isinstance(playlist.id, str) else str(playlist.id)}
                            ]},
                            {"$set": {"media_count": real_count}}
                        )
                        print(f"DEBUG - Veritabanı güncellendi: {playlist.name} ID: {playlist.id} count={real_count}")
                    except Exception as db_error:
                        print(f"DEBUG - Veritabanı güncellemesi başarısız: {str(db_error)}")
        
        # Şablona verileri gönder
        print("DEBUG - Şablon render ediliyor")
        return render_template('user/manage_screen_content.html',
                              screen=screen,
                              screen_content=screen_content_list,
                              user_media=user_media,
                              public_media=public_media,
                              user_playlists=user_playlists,
                              public_playlists=public_playlists,
                              assigned_playlist=assigned_playlist)
                              
    except Exception as e:
        print(f"DEBUG - manage_screen_content genel hata: {str(e)}")
        print(traceback.format_exc())
        flash('Beklenmeyen bir hata oluştu.', 'danger')
        return redirect(url_for('user.screens'))

@bp.route('/screens/<screen_id>/content/add', methods=['POST'])
@user_required
def add_screen_content(screen_id):
    """Ekrana içerik ekleme"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Ekrana erişim izniniz yok.'}), 403
    
    data = request.get_json()
    media_id = data.get('media_id')
    display_time = data.get('display_time')
    
    media = Media.find_by_id(media_id)
    if not media:
        return jsonify({'success': False, 'message': 'Medya bulunamadı.'}), 404
    
    # Medya sahibi kontrolü - nesne veya sözlük olma durumuna göre kontrol et
    user_id_from_media = None
    if hasattr(media, 'user_id'):
        user_id_from_media = media.user_id
    elif isinstance(media, dict):
        user_id_from_media = media.get('user_id')
    
    is_public_media = False
    if hasattr(media, 'is_public'):
        is_public_media = media.is_public
    elif isinstance(media, dict):
        is_public_media = media.get('is_public', False)
    
    if str(user_id_from_media) != str(session['user_id']) and not is_public_media:
        return jsonify({'success': False, 'message': 'Bu medyaya erişim izniniz yok.'}), 403
    
    # İçerik ekle
    from app.models.screen_content import ScreenContent
    content = ScreenContent.create(
        screen_id=screen_id,
        media_id=media_id,
        display_time=display_time
    )
    
    # Oluşturulan içeriğin ID'sini döndür
    content_id = str(content.get('_id') if isinstance(content, dict) else content.id if hasattr(content, 'id') else None)
    
    return jsonify({'success': True, 'content_id': content_id})

@bp.route('/screens/<screen_id>/content/remove', methods=['POST'])
@user_required
def remove_screen_content(screen_id):
    """Ekrandan içerik kaldırma"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Ekrana erişim izniniz yok.'}), 403
    
    data = request.get_json()
    content_id = data.get('content_id')
    
    from app.models.screen_content import ScreenContent
    content = ScreenContent.find_by_id(content_id)
    
    # Content nesnesinden screen_id alırken kontrol
    content_screen_id = None
    if hasattr(content, 'screen_id'):
        content_screen_id = content.screen_id
    elif isinstance(content, dict):
        content_screen_id = content.get('screen_id')
    
    if not content or str(content_screen_id) != str(screen_id):
        return jsonify({'success': False, 'message': 'İçerik bulunamadı.'}), 404
    
    # İçeriği sil
    ScreenContent.delete(content_id)
    
    return jsonify({'success': True})

@bp.route('/screens/<screen_id>/content/update', methods=['POST'])
@user_required
def update_screen_content(screen_id):
    """Ekran içeriği güncelleme"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        flash('Bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    content_id = request.form.get('content_id')
    display_time = request.form.get('display_time')
    
    from app.models.screen_content import ScreenContent
    content = ScreenContent.find_by_id(content_id)
    
    # Content nesnesinden screen_id alırken kontrol
    content_screen_id = None
    if hasattr(content, 'screen_id'):
        content_screen_id = content.screen_id
    elif isinstance(content, dict):
        content_screen_id = content.get('screen_id')
    
    if not content or str(content_screen_id) != str(screen_id):
        flash('İçerik bulunamadı.', 'danger')
        return redirect(url_for('user.manage_screen_content', screen_id=screen_id))
    
    # İçeriği güncelle
    ScreenContent.update(content_id, {'display_time': display_time})
    
    flash('İçerik başarıyla güncellendi.', 'success')
    return redirect(url_for('user.manage_screen_content', screen_id=screen_id))

@bp.route('/screens/<screen_id>/content/save', methods=['POST'])
@user_required
def save_screen_content(screen_id):
    """Ekran içerik sıralamasını kaydetme"""
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        flash('Bu ekrana erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    content_ids = request.form.getlist('content_ids[]')
    
    # İçerik sıralamasını güncelle
    from app.models.screen_content import ScreenContent
    ScreenContent.reorder_screen_contents(screen_id, content_ids)
    
    flash('İçerik sıralaması başarıyla kaydedildi.', 'success')
    return redirect(url_for('user.manage_screen_content', screen_id=screen_id))

@bp.route('/packages')
@user_required
def packages():
    """Paket yükseltme sayfası"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    # Örnek paketler - gerçekte veritabanından gelebilir
    packages = [
        {
            "id": "basic",
            "name": "Temel Paket",
            "price": "99 TL / ay",
            "description": "Küçük işletmeler için dijital ekran yönetimi",
            "max_screens": 3,
            "max_media": 50,
            "storage_limit": "500 MB",
            "features": [
                "3 ekran desteği",
                "Basit medya yönetimi",
                "Email desteği"
            ]
        },
        {
            "id": "standard",
            "name": "Standart Paket",
            "price": "199 TL / ay",
            "description": "Orta ölçekli işletmeler için gelişmiş yönetim",
            "max_screens": 10,
            "max_media": 150,
            "storage_limit": "2 GB",
            "features": [
                "10 ekran desteği",
                "Gelişmiş medya yönetimi",
                "Öncelikli email desteği",
                "İleri raporlama"
            ]
        },
        {
            "id": "premium",
            "name": "Premium Paket",
            "price": "399 TL / ay",
            "description": "Büyük işletmeler için kurumsal çözüm",
            "max_screens": 30,
            "max_media": 500,
            "storage_limit": "5 GB",
            "features": [
                "30 ekran desteği",
                "Sınırsız medya yükleme",
                "7/24 teknik destek",
                "Özel API erişimi",
                "Gelişmiş analitik"
            ]
        }
    ]
    
    return render_template('user/packages.html', user=user, packages=packages)

@bp.route('/upgrade_package/<package_id>', methods=['GET', 'POST'])
@user_required
def upgrade_package(package_id):
    """Paketi yükseltme sayfası"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('auth.logout'))
    
    # Tüm paketleri al
    packages = [
        {
            "id": "free",
            "name": "NöbetmatikPro",
            "price": "Ücretsiz",
            "description": "Temel dijital ekran yönetimi",
            "max_screens": 3,
            "max_media": 20,
            "storage_limit": "1 GB",
            "features": [
                "3 ekran desteği",
                "Temel medya yönetimi",
                "Email desteği"
            ]
        },
        {
            "id": "basic",
            "name": "Başlangıç Paketi",
            "price": "199 TL / ay",
            "description": "Küçük işletmeler için dijital ekran yönetimi",
            "max_screens": 3,
            "max_media": 50,
            "storage_limit": "1 GB",
            "features": [
                "3 ekran desteği",
                "Basit medya yönetimi",
                "Email desteği",
                "Temel raporlama"
            ]
        },
        {
            "id": "standard",
            "name": "Profesyonel Paket",
            "price": "399 TL / ay",
            "description": "Orta ölçekli işletmeler için gelişmiş yönetim",
            "max_screens": 5,
            "max_media": 150,
            "storage_limit": "5 GB",
            "features": [
                "5 ekran desteği",
                "Gelişmiş medya yönetimi",
                "Öncelikli email desteği",
                "İleri raporlama"
            ]
        },
        {
            "id": "premium",
            "name": "Kurumsal Paket",
            "price": "699 TL / ay",
            "description": "Büyük işletmeler için kurumsal çözüm",
            "max_screens": 20,
            "max_media": 500,
            "storage_limit": "10 GB",
            "features": [
                "20 ekran desteği",
                "Sınırsız medya yükleme",
                "7/24 teknik destek",
                "Özel API erişimi",
                "Gelişmiş analitik"
            ]
        }
    ]
    
    # Seçilen paketi bul
    selected_package = next((p for p in packages if p['id'] == package_id), None)
    
    if not selected_package:
        flash('Geçersiz paket seçimi.', 'danger')
        return redirect(url_for('user.packages'))
    
    if request.method == 'POST':
        # Burada ödeme işlemi gerçekleştirilecek
        # Şimdilik sadece kullanıcı paketini güncelliyoruz
        user.update(package=package_id)
        
        Log.log_action(
            action="package_upgrade",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"package": package_id}
        )
        
        flash(f"Paketiniz {selected_package['name']} olarak yükseltildi.", 'success')
        return redirect(url_for('user.profile'))
    
    return render_template('user/upgrade_package.html', 
                           user=user,
                           package=selected_package)

@bp.route('/add-to-screens', methods=['POST'])
@user_required
def add_to_screens():
    """Medyayı seçili ekranlara ekle"""
    media_id = request.form.get('media_id')
    screen_ids = request.form.getlist('screen_ids[]')
    
    if not media_id or not screen_ids:
        flash('Lütfen bir medya ve en az bir ekran seçin.', 'warning')
        return redirect(url_for('user.public_library'))
    
    # Medya bilgilerini al
    media = Media.find_by_id(media_id)
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('user.public_library'))
    
    # Kullanıcının ekranlarına medyayı ekle
    success_count = 0
    for screen_id in screen_ids:
        # Önce ekranın kullanıcıya ait olduğunu doğrula
        screen = Screen.find_by_id(screen_id)
        
        # Screen nesnesinden user_id almak için kontrol
        screen_user_id = None
        if hasattr(screen, 'user_id'):
            screen_user_id = screen.user_id
        elif isinstance(screen, dict):
            screen_user_id = screen.get('user_id')
            
        if not screen or str(screen_user_id) != str(session['user_id']):
            continue
        
        # Ekrana medyayı ekle
        if ScreenContent.add_media_to_screen(screen_id, media_id):
            success_count += 1
    
    if success_count > 0:
        flash(f'Medya {success_count} ekranınıza başarıyla eklendi.', 'success')
        # Log ekle
        media_title = ''
        if hasattr(media, 'title'):
            media_title = media.title
        elif isinstance(media, dict):
            media_title = media.get('title', '')
            
        Log.log_action(
            action=Log.TYPE_CONTENT_ADD,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"media_title": media_title, "screen_count": success_count}
        )
    else:
        flash('Medya ekranlara eklenirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('user.public_library'))

##################################################
# PLAYLIST YÖNETİMİ 
##################################################

@bp.route('/playlists')
@user_required
def playlists():
    """Kullanıcının playlist'lerini listeler"""
    import traceback
    user_id = session['user_id']
    
    # Playlistleri getir
    from app.models.playlist import Playlist
    user_playlists = Playlist.find_by_user(user_id, status=Playlist.STATUS_ACTIVE)
    
    # Public playlistleri getir
    public_playlists = Playlist.find_public()
    
    # Kullanıcının kendi oluşturduğu public playlist'leri filtrele
    public_playlists = [p for p in public_playlists if str(p.user_id) != str(user_id)]
    
    # Tüm playlist medya sayılarını güncelle
    from app.models.playlist_media import PlaylistMedia
    all_playlists = user_playlists + public_playlists
    for playlist in all_playlists:
        try:
            # Veritabanında medya sayısını güncelle
            media_count = playlist.update_media_count()
            # Nesne özelliğine güncel sayıyı ata
            playlist.media_count = media_count
            print(f"DEBUG - Playlist medya sayısı güncellendi: id={playlist.id}, name={playlist.name}, count={media_count}")
        except Exception as e:
            print(f"DEBUG - Playlist medya sayısı güncellenirken hata: {str(e)}")
            traceback.print_exc()
    
    return render_template('user/playlists.html', 
                          user_playlists=user_playlists,
                          public_playlists=public_playlists,
                          active_page='playlists')
    
@bp.route('/playlists/create', methods=['GET', 'POST'])
@user_required
def create_playlist():
    """Yeni playlist oluşturma"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = True if request.form.get('is_public') == '1' else False
        
        if not name:
            flash('Lütfen playlist adını girin.', 'warning')
            return redirect(request.url)
        
        # Playlist oluştur
        from app.models.playlist import Playlist
        
        playlist_data = {
            'name': name,
            'description': description,
            'user_id': session['user_id'],
            'is_public': is_public,
            'status': Playlist.STATUS_ACTIVE
        }
        
        playlist = Playlist.create(playlist_data)
        
        # Log kaydı
        Log.log_action(
            action="playlist_create",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"playlist_id": str(playlist['_id']), "name": name}
        )
        
        flash('Playlist başarıyla oluşturuldu.', 'success')
        return redirect(url_for('user.edit_playlist', playlist_id=str(playlist['_id'])))
    
    return render_template('user/create_playlist.html')

@bp.route('/playlists/<playlist_id>')
@user_required
def view_playlist(playlist_id):
    """Playlist detaylarını görüntüle"""
    from app.models.playlist import Playlist
    
    playlist = Playlist.find_by_id(playlist_id)
    
    if not playlist:
        flash('Playlist bulunamadı.', 'danger')
        return redirect(url_for('user.playlists'))
    
    # Erişim kontrolü - yalnızca sahibi ve public playlistler görüntülenebilir
    if str(playlist.user_id) != str(session['user_id']) and not playlist.is_public:
        flash('Bu playlist\'e erişim izniniz yok.', 'danger')
        return redirect(url_for('user.playlists'))
    
    # Playlist'teki medyaları getir
    from app.models.playlist_media import PlaylistMedia
    playlist_media = PlaylistMedia.find_by_playlist(playlist_id)
    
    return render_template('user/view_playlist.html',
                          playlist=playlist,
                          playlist_media=playlist_media)

@bp.route('/playlists/<playlist_id>/edit', methods=['GET', 'POST'])
@user_required
def edit_playlist(playlist_id):
    """Playlist düzenleme"""
    from app.models.playlist import Playlist
    
    playlist = Playlist.find_by_id(playlist_id)
    
    if not playlist:
        flash('Playlist bulunamadı.', 'danger')
        return redirect(url_for('user.playlists'))
    
    # Erişim kontrolü - yalnızca sahibi düzenleyebilir
    if str(playlist.user_id) != str(session['user_id']):
        flash('Bu playlist\'i düzenleme yetkiniz yok.', 'danger')
        return redirect(url_for('user.playlists'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_public = True if request.form.get('is_public') == '1' else False
        
        if not name:
            flash('Lütfen playlist adını girin.', 'warning')
            return redirect(request.url)
        
        # Playlist güncelle
        playlist.update(
            name=name,
            description=description,
            is_public=is_public
        )
        
        # Log kaydı
        Log.log_action(
            action="playlist_update",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"playlist_id": playlist_id, "name": name}
        )
        
        # Playlist'i kullanan ekranları bul ve güncelle
        try:
            from app.models.screen_playlist import ScreenPlaylist
            import traceback
            
            # Bu playlist'in atanmış olduğu ekranları bul
            screen_playlists = ScreenPlaylist.find_by_playlist_id(playlist_id)
            
            if screen_playlists:
                updated_screens = 0
                
                for screen_playlist in screen_playlists:
                    screen_id = screen_playlist.get('screen_id') if isinstance(screen_playlist, dict) else getattr(screen_playlist, 'screen_id', None)
                    
                    if screen_id:
                        # Ekranı güncelle
                        refresh_result = ScreenPlaylist.refresh_screen_playlist(screen_id)
                        
                        if refresh_result['success']:
                            updated_screens += 1
                
                if updated_screens > 0:
                    flash(f'Playlist güncellendi ve {updated_screens} ekran otomatik olarak yenilendi.', 'success')
                else:
                    flash('Playlist başarıyla güncellendi.', 'success')
            else:
                flash('Playlist başarıyla güncellendi.', 'success')
        except Exception as e:
            print(f"ERROR - Playlist ekran güncelleme hatası: {str(e)}")
            traceback.print_exc()
            flash('Playlist güncellendi ancak ilişkili ekranlar güncellenirken hata oluştu.', 'warning')
        
        return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))
    
    # Kullanıcının medyaları
    from app.models.media import Media
    user_media = Media.find_by_user(session['user_id'], status=Media.STATUS_ACTIVE)
    
    # Kütüphane medyaları
    library_media = Media.find_public()
    
    # Playlist'teki medyaları getir
    from app.models.playlist_media import PlaylistMedia
    playlist_media = PlaylistMedia.find_by_playlist(playlist_id)
    
    # Playlist'te olmayan medyaları filtrele
    assigned_media_ids = [item['media_id'] for item in playlist_media]
    
    # Media nesnelerine erişim kontrolü
    available_user_media = []
    for m in user_media:
        media_id = None
        if hasattr(m, 'id'):
            media_id = m.id
        elif hasattr(m, '_id'):
            media_id = m._id
        elif isinstance(m, dict) and '_id' in m:
            media_id = m['_id']
        
        if media_id and str(media_id) not in [str(id) for id in assigned_media_ids]:
            available_user_media.append(m)
    
    # Kütüphane medyaları için de aynı kontrolü yap
    available_library_media = []
    for m in library_media:
        media_id = None
        if hasattr(m, 'id'):
            media_id = m.id
        elif hasattr(m, '_id'):
            media_id = m._id
        elif isinstance(m, dict) and '_id' in m:
            media_id = m['_id']
        
        if media_id and str(media_id) not in [str(id) for id in assigned_media_ids]:
            available_library_media.append(m)
    
    return render_template('user/edit_playlist.html',
                          playlist=playlist,
                          playlist_media=playlist_media,
                          available_user_media=available_user_media,
                          available_library_media=available_library_media)

@bp.route('/playlists/<playlist_id>/delete', methods=['POST'])
@user_required
def delete_playlist(playlist_id):
    """Playlist silme"""
    from app.models.playlist import Playlist
    
    playlist = Playlist.find_by_id(playlist_id)
    
    if not playlist:
        flash('Playlist bulunamadı.', 'danger')
        return redirect(url_for('user.playlists'))
    
    # Erişim kontrolü - yalnızca sahibi silebilir
    # Nesne veya sözlük olabileceği için her iki durumu da kontrolü
    user_id_from_playlist = playlist.user_id if hasattr(playlist, 'user_id') else playlist.get('user_id')
    
    if str(user_id_from_playlist) != str(session['user_id']):
        flash('Bu playlist\'i silme yetkiniz yok.', 'danger')
        return redirect(url_for('user.playlists'))
    
    # Playlist'i sil - ID ile çağırıyoruz
    Playlist.delete(playlist_id)
    
    # Log kaydı
    # Nesne veya sözlük olabileceği için her iki durumu da kontrolü
    playlist_name = playlist.name if hasattr(playlist, 'name') else playlist.get('name')
    
    Log.log_action(
        action="playlist_delete",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={"playlist_id": playlist_id, "name": playlist_name}
    )
    
    flash('Playlist başarıyla silindi.', 'success')
    return redirect(url_for('user.playlists'))

@bp.route('/playlists/<playlist_id>/add_media', methods=['POST'])
@user_required
def add_media_to_playlist(playlist_id):
    """Playlist'e medya ekleme"""
    try:
        from app.models.playlist import Playlist
        import traceback, json
        
        print(f"Add media request received: playlist_id={playlist_id}")
        print(f"Request path: {request.path}")
        print(f"Request method: {request.method}")
        
        # CSRF token ve request parametreleri için debug logları
        csrf_token = request.headers.get('X-CSRF-Token')
        print(f"CSRF token: {csrf_token}")
        print(f"All headers: {dict(request.headers)}")
        
        # İstek içeriğini kontrol et
        print(f"Content type: {request.content_type}")
        request_data = request.get_data(as_text=True)
        print(f"Raw request data: {request_data}")
        
        # JSON verisi almaya çalış
        json_data = None
        try:
            if request.is_json:
                json_data = request.get_json(silent=True)
                print(f"Request.get_json() result: {json_data}")
            else:
                print("Request is not JSON format")
                
            # Eğer json_data alınamadıysa, manuel parse dene
            if json_data is None and request_data:
                try:
                    json_data = json.loads(request_data)
                    print(f"Manually parsed JSON: {json_data}")
                except Exception as je:
                    print(f"Manual JSON parse error: {str(je)}")
        except Exception as je:
            print(f"JSON parsing error: {str(je)}")
        
        # JSON verisi hala alınamadıysa form verilerini dene
        if json_data is None:
            print("Trying form data")
            try:
                media_id = request.form.get('media_id')
                display_time = request.form.get('display_time')
                if media_id:
                    json_data = {'media_id': media_id, 'display_time': display_time}
                    print(f"Form data parsed: {json_data}")
            except Exception as fe:
                print(f"Form data error: {str(fe)}")
        
        # Hala veri yoksa, manuel olarak istek verilerini inceleyelim
        if not json_data:
            print("No valid data found, checking request args and other sources")
            
            # URL query parametrelerini kontrol et
            if request.args:
                media_id = request.args.get('media_id')
                if media_id:
                    display_time = request.args.get('display_time')
                    json_data = {'media_id': media_id, 'display_time': display_time}
                    print(f"Args data: {json_data}")
        
        if not json_data:
            print("No data could be extracted from the request")
            return jsonify({'success': False, 'message': 'Geçersiz istek verisi.'}), 400
        
        # Playlist kontrolü
        playlist = Playlist.find_by_id(playlist_id)
        if not playlist:
            print(f"Playlist not found: {playlist_id}")
            return jsonify({'success': False, 'message': 'Playlist bulunamadı.'}), 404
        
        # Playlist sahibi kontrolü - Doğrudan user_id özniteliğine erişim sorun çıkarabilir
        playlist_user_id = None
        if hasattr(playlist, 'user_id'):
            playlist_user_id = playlist.user_id
        elif isinstance(playlist, dict):
            playlist_user_id = playlist.get('user_id')
        else:
            print(f"Cannot determine playlist owner: {type(playlist)}")
            return jsonify({'success': False, 'message': 'Playlist erişim sorunu.'}), 500
            
        if str(playlist_user_id) != str(session['user_id']):
            print(f"Playlist access denied: user_id={session['user_id']}, playlist.user_id={playlist_user_id}")
            return jsonify({'success': False, 'message': 'Bu playlist\'e erişim izniniz yok.'}), 403
        
        # JSON verisinden medya ID'yi al
        media_id = json_data.get('media_id')
        display_time = json_data.get('display_time')
        
        print(f"Extracted media_id: {media_id}, display_time: {display_time}")
        
        if not media_id:
            print("Media ID missing")
            return jsonify({'success': False, 'message': 'Media ID belirtilmedi.'}), 400
        
        # Medya kontrolü
        media = Media.find_by_id(media_id)
        if not media:
            print(f"Media not found: {media_id}")
            return jsonify({'success': False, 'message': 'Medya bulunamadı.'}), 404
            
        print(f"Media found: {type(media)}")
            
        # Medya public mi kontrolü - dict veya nesne olma durumunu kapsayacak şekilde
        is_public = False
        if hasattr(media, 'is_public'):
            is_public = media.is_public
        elif isinstance(media, dict):
            is_public = media.get('is_public', False)
        
        # Medya user_id kontrolü - dict veya nesne olma durumunu kapsayacak şekilde
        media_user_id = None
        if hasattr(media, 'user_id'):
            media_user_id = media.user_id
        elif isinstance(media, dict):
            media_user_id = media.get('user_id')
        
        print(f"Media access check: is_public={is_public}, media_user_id={media_user_id}, session_user_id={session['user_id']}")
        
        # Medya sahibi kontrolü
        if not is_public and str(media_user_id) != str(session['user_id']):
            print(f"Media access denied: user_id={session['user_id']}, media.user_id={media_user_id}")
            return jsonify({'success': False, 'message': 'Bu medyaya erişim izniniz yok.'}), 403
        
        # Medya zaten playlist'te mi kontrol et
        from app.models.playlist_media import PlaylistMedia
        existing = PlaylistMedia.find_by_playlist_and_media(playlist_id, media_id)
        if existing:
            print(f"Media already in playlist: {media_id}")
            return jsonify({'success': False, 'message': 'Bu medya zaten playlist\'te bulunuyor.'}), 409
        
        # Display time düzeltme ve file_type kontrolü
        file_type = None
        if hasattr(media, 'file_type'):
            file_type = media.file_type
        elif isinstance(media, dict):
            file_type = media.get('file_type')
            
        print(f"Media file_type: {file_type}")
        
        if file_type == 'video':
            # Videolar için display_time null olmalı
            display_time = None
        elif not display_time:
            # Gösterim süresi belirtilmediyse varsayılan değer
            display_time = 10
        
        # Medyayı playliste ekle
        print(f"Creating playlist media: playlist_id={playlist_id}, media_id={media_id}, display_time={display_time}")
        
        try:
            new_playlist_media = PlaylistMedia.create(
                playlist_id=playlist_id,
                media_id=media_id,
                display_time=display_time
            )
            
            if new_playlist_media:
                print(f"Playlist media created successfully: {new_playlist_media}")
                # Yeni eklenen medyanın ID'sini döndür
                return jsonify({
                    'success': True, 
                    'media_id': str(media_id),
                    'message': 'Medya başarıyla playlist\'e eklendi.'
                })
            else:
                print("Failed to create playlist media")
                return jsonify({'success': False, 'message': 'Medya eklenirken bir hata oluştu.'}), 500
        except Exception as ce:
            print(f"Error creating playlist media: {str(ce)}")
            print(traceback.format_exc())
            return jsonify({'success': False, 'message': f'Playlist media oluşturma hatası: {str(ce)}'}), 500
            
    except Exception as e:
        import traceback
        print(f"General error: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': f'Beklenmeyen bir hata oluştu: {str(e)}'}), 500

@bp.route('/playlists/<playlist_id>/remove_media', methods=['POST'])
@user_required
def remove_media_from_playlist(playlist_id):
    """Playlist'ten medya kaldırma"""
    from app.models.playlist import Playlist
    
    playlist = Playlist.find_by_id(playlist_id)
    
    if not playlist:
        flash('Playlist bulunamadı.', 'danger')
        return redirect(url_for('user.playlists'))
    
    # Erişim kontrolü - yalnızca sahibi kaldırabilir
    if str(playlist.user_id) != str(session['user_id']):
        flash('Bu playlist\'ten medya kaldırma yetkiniz yok.', 'danger')
        return redirect(url_for('user.playlists'))
    
    media_id = request.form.get('media_id')
    
    if not media_id:
        flash('Geçersiz medya ID.', 'warning')
        return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))
    
    # Medyayı playlist'ten kaldır
    from app.models.playlist_media import PlaylistMedia
    result = PlaylistMedia.remove_from_playlist(playlist_id, media_id)
    
    if result:
        # Log kaydı
        Log.log_action(
            action="playlist_remove_media",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"playlist_id": playlist_id, "media_id": media_id}
        )
        
        flash('Medya playlist\'ten kaldırıldı.', 'success')
    else:
        flash('Medya kaldırılırken bir hata oluştu.', 'danger')
        
    return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))

@bp.route('/playlists/<playlist_id>/reorder', methods=['POST'])
@user_required
def reorder_playlist_media(playlist_id):
    """Playlist medya sıralamasını güncelleme"""
    from app.models.playlist import Playlist
    import traceback
    
    playlist = Playlist.find_by_id(playlist_id)
    
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist bulunamadı'})
    
    # Erişim kontrolü - yalnızca sahibi düzenleyebilir
    if str(playlist.user_id) != str(session['user_id']):
        return jsonify({'success': False, 'message': 'Bu playlist\'i düzenleme yetkiniz yok'})
    
    # JSON verisini al
    try:
        data = request.get_json()
        media_order = data.get('media_order', [])
    except Exception as e:
        return jsonify({'success': False, 'message': f'Geçersiz veri formatı: {str(e)}'})
    
    if not media_order:
        return jsonify({'success': False, 'message': 'Sıralama bilgisi bulunamadı'})
    
    # Sıralamayı güncelle
    try:
        from app.models.playlist_media import PlaylistMedia
        result = PlaylistMedia.reorder_playlist_media(playlist_id, media_order)
        
        if result:
            # Playlist'i kullanan ekranları bul ve güncelle
            try:
                from app.models.screen_playlist import ScreenPlaylist
                
                # Bu playlist'in atanmış olduğu ekranları bul
                screen_playlists = ScreenPlaylist.find_by_playlist_id(playlist_id)
                
                updated_screens = 0
                if screen_playlists:
                    for screen_playlist in screen_playlists:
                        screen_id = screen_playlist.get('screen_id') if isinstance(screen_playlist, dict) else getattr(screen_playlist, 'screen_id', None)
                        
                        if screen_id:
                            # Ekranı güncelle
                            refresh_result = ScreenPlaylist.refresh_screen_playlist(screen_id)
                            
                            if refresh_result['success']:
                                updated_screens += 1
                    
                # Log kaydı
                from app.models.log import Log
                Log.log_action(
                    action="playlist_reorder",
                    user_id=session['user_id'],
                    ip_address=request.remote_addr,
                    details={"playlist_id": playlist_id, "updated_screens": updated_screens}
                )
                
                return jsonify({
                    'success': True, 
                    'message': 'Sıralama güncellendi',
                    'updated_screens': updated_screens
                })
            except Exception as e:
                print(f"ERROR - Sıralama sonrası ekran güncelleme hatası: {str(e)}")
                traceback.print_exc()
                
                # Temel başarı mesajı döndür
                return jsonify({'success': True, 'message': 'Sıralama güncellendi, ancak ilişkili ekranlar güncellenemedi'})
        else:
            return jsonify({'success': False, 'message': 'Sıralama güncellenirken bir hata oluştu'})
    except Exception as e:
        print(f"ERROR - Playlist sıralama hatası: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Bir hata oluştu: {str(e)}'})

@bp.route('/screens/<screen_id>/assign_playlist', methods=['GET', 'POST'])
@user_required
def assign_playlist_to_screen(screen_id):
    """Ekrana playlist atama"""
    import traceback
    from bson.objectid import ObjectId
    
    try:
        # Ekranı kontrol et
        screen = Screen.find_by_id(screen_id)
        
        if not screen or screen.user_id != session['user_id']:
            flash('Ekran bulunamadı veya erişim izniniz yok.', 'danger')
            return redirect(url_for('user.screens'))
        
        # URL'den gelen playlist_id'yi kontrol et
        playlist_id_from_url = request.args.get('playlist_id')
        
        if request.method == 'POST' or playlist_id_from_url:
            # Form'dan veya URL'den playlist_id al
            playlist_id = request.form.get('playlist_id') or playlist_id_from_url
            
            if not playlist_id:
                flash('Lütfen bir playlist seçin.', 'warning')
                return redirect(url_for('user.assign_playlist_to_screen', screen_id=screen_id))
            
            # Playlist'i kontrol et
            from app.models.playlist import Playlist
            playlist = Playlist.find_by_id(playlist_id)
            
            if not playlist:
                flash('Seçilen playlist bulunamadı.', 'danger')
                return redirect(url_for('user.assign_playlist_to_screen', screen_id=screen_id))
            
            # Erişim kontrolü - kullanıcının kendi playlist'i veya public playlist olmalı
            playlist_user_id = getattr(playlist, 'user_id', None) if hasattr(playlist, 'user_id') else playlist.get('user_id') if isinstance(playlist, dict) else None
            playlist_is_public = getattr(playlist, 'is_public', False) if hasattr(playlist, 'is_public') else playlist.get('is_public', False) if isinstance(playlist, dict) else False
            
            if str(playlist_user_id) != str(session['user_id']) and not playlist_is_public:
                flash('Bu playlist\'e erişim yetkiniz yok.', 'danger')
                return redirect(url_for('user.assign_playlist_to_screen', screen_id=screen_id))
            
            try:
                # Önce ekrandaki tüm içerikleri temizle
                from app.models.screen_content import ScreenContent
                print(f"Mevcut ekran içeriklerini temizleme: {screen_id}")
                delete_count = ScreenContent.delete_by_screen(screen_id)
                print(f"Silinen içerik sayısı: {delete_count}")
                
                # Playlist'teki medyaları ekrana ekle
                from app.models.playlist_media import PlaylistMedia
                playlist_media = PlaylistMedia.find_by_playlist(playlist_id)
                print(f"Playlist medya sayısı: {len(playlist_media)}")
                
                created_contents = []
                for index, item in enumerate(playlist_media):
                    print(f"Ekrana eklenecek medya işleniyor: {index+1}/{len(playlist_media)}")
                    print(f"İşlenen öğe tipi: {type(item)}, içerik: {item}")
                    
                    # Media ID alınması
                    media_id = None
                    try:
                        if isinstance(item, dict) and 'media_id' in item:
                            media_id = item['media_id']
                            print(f"Item'dan (dict) medya ID: {media_id}")
                        elif hasattr(item, 'media_id'):
                            media_id = item.media_id
                            print(f"Item'dan (object) medya ID: {media_id}")
                    except Exception as e:
                        print(f"Media ID alınırken hata: {str(e)}")
                        
                    # Media nesnesine erişim
                    media = None
                    try:
                        if isinstance(item, dict) and 'media' in item:
                            media = item['media']
                            print(f"Media item içinden bulundu (dict)")
                        elif hasattr(item, 'media'):
                            media = item.media
                            print(f"Media item içinden bulundu (object)")
                    except Exception as e:
                        print(f"Media nesnesi alınırken hata: {str(e)}")
                    
                    # Media ID kontrolü - media nesnesi varsa ondan da alabiliriz
                    if not media_id and media:
                        try:
                            if hasattr(media, 'id'):
                                media_id = media.id
                                print(f"Media.id: {media_id}")
                            elif hasattr(media, '_id'):
                                media_id = media._id
                                print(f"Media._id: {media_id}")
                            elif isinstance(media, dict):
                                if '_id' in media:
                                    media_id = media['_id']
                                    print(f"Media['_id']: {media_id}")
                                elif 'id' in media:
                                    media_id = media['id']
                                    print(f"Media['id']: {media_id}")
                        except Exception as e:
                            print(f"Media nesnesinden ID alınırken hata: {str(e)}")
                    
                    if not media_id:
                        print(f"Geçersiz medya ID, bu içerik atlanıyor: {item}")
                        continue
                        
                    # String formatına çevir
                    if not isinstance(media_id, str):
                        media_id = str(media_id)
                        
                    # Display time kontrolü
                    display_time = None
                    try:
                        if isinstance(item, dict) and 'display_time' in item:
                            display_time = item['display_time']
                        elif hasattr(item, 'display_time'):
                            display_time = item.display_time
                    except Exception as e:
                        print(f"Display time alınırken hata: {str(e)}")
                    
                    # Varsayılan gösterim süresi 10 saniye
                    if not display_time:
                        display_time = 10
                    
                    # Sıralama
                    order = index
                    try:
                        if isinstance(item, dict) and 'order' in item:
                            order = item['order']
                        elif hasattr(item, 'order'):
                            order = item.order
                    except Exception as e:
                        print(f"Order alınırken hata: {str(e)}")
                    
                    # Yeni içerik oluştur
                    try:
                        print(f"Ekrana içerik ekleniyor: media_id={media_id}, display_time={display_time}, order={order}")
                        content = ScreenContent.create({
                            'screen_id': screen_id,
                            'media_id': media_id,
                            'display_time': display_time,
                            'order': order
                        })
                        
                        content_id = None
                        if isinstance(content, dict) and '_id' in content:
                            content_id = content['_id']
                        elif hasattr(content, 'id'):
                            content_id = content.id
                        elif hasattr(content, '_id'):
                            content_id = content._id
                        
                        print(f"İçerik eklendi: {content_id}")
                        created_contents.append(content)
                    except Exception as e:
                        print(f"İçerik ekleme hatası: {str(e)}")
                        print(traceback.format_exc())
                
                print(f"Toplam oluşturulan içerik sayısı: {len(created_contents)}")
                if len(created_contents) != len(playlist_media):
                    print(f"DİKKAT: Playlist'teki tüm medyalar ekrana aktarılamadı! Playlist: {len(playlist_media)}, Eklenen: {len(created_contents)}")
                
                # Ekran-Playlist ilişkisi oluştur/güncelle
                from app.models.screen_playlist import ScreenPlaylist
                try:
                    screen_playlist = ScreenPlaylist.create({
                        'screen_id': screen_id,
                        'playlist_id': playlist_id
                    })
                    print(f"Ekran-Playlist ilişkisi oluşturuldu: {screen_playlist.get('_id') if isinstance(screen_playlist, dict) else screen_playlist}")
                except Exception as e:
                    print(f"Ekran-Playlist ilişkisi oluşturma hatası: {str(e)}")
                    print(traceback.format_exc())
                
                # Log kaydı
                Log.log_action(
                    action="screen_assign_playlist",
                    user_id=session['user_id'],
                    ip_address=request.remote_addr,
                    details={"screen_id": screen_id, "playlist_id": playlist_id}
                )
                
                flash(f'Playlist ekrana başarıyla atandı. Toplam {len(created_contents)} medya içeriği eklendi.', 'success')
                return redirect(url_for('user.manage_screen_content', screen_id=screen_id))
            except Exception as e:
                print(f"Genel hata: {str(e)}")
                print(traceback.format_exc())
                flash('Playlist atanırken bir hata oluştu: ' + str(e), 'danger')
                return redirect(url_for('user.assign_playlist_to_screen', screen_id=screen_id))
        
        # Kullanıcının playlist'lerini getir
        from app.models.playlist import Playlist
        user_playlists = Playlist.find_by_user(session['user_id'], status=Playlist.STATUS_ACTIVE)
        
        # Public playlist'leri getir
        public_playlists = Playlist.find_public()
        
        # Kullanıcının kendi oluşturduğu public playlist'leri filtrele
        public_playlists = [p for p in public_playlists if str(p.user_id) != str(session['user_id'])]
        
        # Playlist'lere medya sayısı ekle
        from app.models.playlist_media import PlaylistMedia
        for playlist in user_playlists + public_playlists:
            try:
                # PlaylistMedia.find_by_playlist ile gerçek sayıyı al
                media_list = PlaylistMedia.find_by_playlist(playlist.id)
                
                # Medya sayısını güncelle ve belleğe al
                real_count = len(media_list) if media_list else 0
                playlist.media_count = real_count
                
                # Veritabanında da güncelle
                from app.models.playlist import Playlist
                Playlist.update_media_count(playlist.id)
                
                print(f"DEBUG - Playlist medya sayısı güncellendi: playlist_id={playlist.id}, name={playlist.name}, count={real_count}")
            except Exception as e:
                print(f"DEBUG - Playlist medya sayısı alınırken hata: {str(e)}")
                traceback.print_exc()
                playlist.media_count = 0
        
        return render_template('user/assign_playlist.html',
                              screen=screen,
                              user_playlists=user_playlists,
                              public_playlists=public_playlists)
    except Exception as e:
        print(f"assign_playlist_to_screen ana fonksiyon hatası: {str(e)}")
        print(traceback.format_exc())
        flash('Beklenmeyen bir hata oluştu.', 'danger')
        return redirect(url_for('user.screens'))

@bp.route('/screens/<screen_id>/remove_playlist', methods=['POST'])
@user_required
def remove_playlist_from_screen(screen_id):
    """Ekrandan playlist kaldırma"""
    import traceback
    
    print(f"DEBUG - remove_playlist_from_screen çağrıldı: screen_id={screen_id}")
    
    # Ekranı kontrol et
    screen = Screen.find_by_id(screen_id)
    
    if not screen or str(screen.user_id) != str(session['user_id']):
        print(f"DEBUG - Ekran bulunamadı veya erişim hatası: screen={screen}, user_id={session.get('user_id')}")
        return jsonify({'success': False, 'message': 'Ekran bulunamadı veya erişim izniniz yok.'}), 404
    
    try:
        # Ekran-Playlist ilişkisini sil
        from app.models.screen_playlist import ScreenPlaylist
        delete_result = ScreenPlaylist.delete_by_screen(screen_id)
        print(f"DEBUG - ScreenPlaylist.delete_by_screen sonucu: {delete_result}")
        
        # Ekran içeriklerini temizle
        from app.models.screen_content import ScreenContent
        content_delete_result = ScreenContent.delete_by_screen(screen_id)
        print(f"DEBUG - ScreenContent.delete_by_screen sonucu: {content_delete_result}")
        
        # Log kaydı
        Log.log_action(
            action="screen_remove_playlist",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"screen_id": screen_id}
        )
        
        print(f"DEBUG - Playlist başarıyla kaldırıldı")
        return jsonify({'success': True})
    except Exception as e:
        print(f"DEBUG - Playlist kaldırma hatası: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500 

@bp.route('/add_to_playlists', methods=['POST'])
@user_required
def add_to_playlists():
    """Medyayı seçilen playlistlere ekler"""
    try:
        import traceback
        
        # Form verilerini al
        media_id = request.form.get('media_id')
        playlist_ids = request.form.getlist('playlist_ids[]')
        
        print(f"DEBUG - add_to_playlists başladı: media_id={media_id}, playlist_ids={playlist_ids}")
        
        if not media_id or not playlist_ids:
            print(f"DEBUG - Medya veya playlist seçilmedi: media_id={media_id}, playlist_ids={playlist_ids}")
            flash('Geçersiz istek. Medya veya playlist seçilmedi.', 'warning')
            return redirect(url_for('user.public_library'))
        
        # Medya bilgilerini kontrol et
        from app.models.media import Media
        media = Media.find_by_id(media_id)
        
        if not media:
            print(f"DEBUG - Medya bulunamadı: media_id={media_id}")
            flash('Seçilen medya bulunamadı.', 'danger')
            return redirect(url_for('user.public_library'))
        
        # Media nesnesinin ID ve başlığını al
        media_obj_id = None
        media_title = "Bilinmeyen Medya"
        
        if hasattr(media, 'id'):
            media_obj_id = media.id
        elif hasattr(media, '_id'):
            media_obj_id = media._id
        elif isinstance(media, dict) and '_id' in media:
            media_obj_id = media['_id']
            
        if hasattr(media, 'title'):
            media_title = media.title
        elif isinstance(media, dict):
            media_title = media.get('title', 'Bilinmeyen Medya')
            
        print(f"DEBUG - Medya bulundu: id={media_obj_id}, title={media_title}")
        
        # Display time kontrolü
        display_time = 10  # Varsayılan değer
        if hasattr(media, 'display_time'):
            display_time = media.display_time
        elif isinstance(media, dict):
            display_time = media.get('display_time', 10)
        
        # Her playlist için ekleme işlemini yapacağız
        from app.models.playlist import Playlist
        from app.models.playlist_media import PlaylistMedia
        
        success_count = 0
        error_count = 0
        already_exists_count = 0
        
        for playlist_id in playlist_ids:
            print(f"DEBUG - Playlist ID inceleniyor: {playlist_id}")
            
            try:
                # Playlist'i kontrol et
                playlist = Playlist.find_by_id(playlist_id)
                
                if not playlist:
                    print(f"DEBUG - Playlist bulunamadı: playlist_id={playlist_id}")
                    error_count += 1
                    continue
                
                # Playlist kullanıcıya ait mi kontrol et
                if str(playlist.user_id) != str(session['user_id']):
                    print(f"DEBUG - Playlist kullanıcıya ait değil: playlist_id={playlist_id}, playlist.user_id={playlist.user_id}, session.user_id={session['user_id']}")
                    error_count += 1
                    continue
                
                print(f"DEBUG - Playlist bulundu: id={playlist.id}, name={playlist.name}")
                
                # Medya zaten bu playlist'te mi kontrol et - find_one ile doğrudan yapıyoruz
                existing = PlaylistMedia.find_one({
                    'playlist_id': playlist_id,
                    'media_id': media_id
                })
                
                if existing:
                    print(f"DEBUG - Medya zaten bu playliste ekli: playlist_id={playlist_id}, media_id={media_id}")
                    already_exists_count += 1
                    continue
                
                # Medyayı playlist'e ekle
                # Playlist'teki son sırayı bul
                last_order = PlaylistMedia.get_max_order(playlist_id)
                order = last_order + 1 if last_order is not None else 0
                
                playlist_media = {
                    'playlist_id': playlist_id,
                    'media_id': media_id,
                    'order': order,
                    'display_time': display_time,
                    'created_at': datetime.datetime.utcnow()
                }
                
                created_item = PlaylistMedia.create(playlist_media)
                
                if created_item:
                    print(f"DEBUG - Medya playliste eklendi: playlist_id={playlist_id}, media_id={media_id}, order={order}")
                    # Playlist medya sayısını güncelle
                    try:
                        Playlist.update_media_count(playlist_id)
                        print(f"DEBUG - Playlist medya sayısı güncellendi")
                    except Exception as count_error:
                        print(f"DEBUG - Playlist medya sayısı güncellenirken hata: {str(count_error)}")
                    
                    success_count += 1
                    
                    # Log kaydet
                    Log.log_action(
                        action="add_media_to_playlist",
                        user_id=session['user_id'],
                        ip_address=request.remote_addr,
                        details={
                            "playlist_id": playlist_id,
                            "media_id": media_id,
                            "media_title": media_title
                        }
                    )
                else:
                    print(f"DEBUG - Medya playliste eklenemedi: playlist_id={playlist_id}, media_id={media_id}")
                    error_count += 1
            except Exception as playlist_error:
                print(f"DEBUG - Playlist işleme hatası: {str(playlist_error)}")
                print(traceback.format_exc())
                error_count += 1
        
        print(f"DEBUG - İşlem sonuçları: success_count={success_count}, error_count={error_count}, already_exists_count={already_exists_count}")
        
        # Sonuçları raporla
        success_message = None
        info_message = None
        warning_message = None
        
        if success_count > 0:
            if success_count == 1:
                success_message = 'Medya başarıyla playliste eklendi.'
            else:
                success_message = f'Medya başarıyla {success_count} playliste eklendi.'
        
        if already_exists_count > 0:
            if already_exists_count == 1:
                if success_count == 0:
                    info_message = 'Bu medya zaten seçilen playliste eklenmiş.'
                else:
                    info_message = 'Bazı playlistlerde bu medya zaten mevcut.'
            else:
                info_message = f'{already_exists_count} playlistte bu medya zaten mevcut.'
        
        if error_count > 0:
            warning_message = f'{error_count} playliste ekleme işlemi başarısız oldu. Sistem yöneticisiyle iletişime geçin.'
        
        # Hiçbir işlem yapılmadıysa
        if success_count == 0 and error_count == 0 and already_exists_count == 0:
            warning_message = 'Hiçbir işlem yapılmadı. Lütfen tekrar deneyin.'
        
        # Flash mesajlarını göster
        if success_message:
            flash(success_message, 'success')
        if info_message:
            flash(info_message, 'info')
        if warning_message:
            flash(warning_message, 'warning')
            
        return redirect(url_for('user.public_library'))
    
    except Exception as e:
        import traceback
        print(f"Playliste medya ekleme genel hatası: {str(e)}")
        print(traceback.format_exc())
        flash('Playliste eklenirken beklenmeyen bir hata oluştu. Lütfen tekrar deneyin.', 'danger')
        return redirect(url_for('user.public_library'))

@bp.route('/playlists/refresh-counts', methods=['POST'])
@user_required
def refresh_playlist_counts():
    """Tüm playlistlerin medya sayılarını yeniler"""
    from app.models.playlist import Playlist
    
    # Tüm playlist'lerin medya sayılarını güncelle
    result = Playlist.update_all_media_counts()
    
    flash(f"{result['updated_playlist_count']} playlist'in medya sayısı güncellendi.", 'success')
    return redirect(url_for('user.playlists'))

@bp.route('/screens/<screen_id>/refresh_playlist', methods=['POST'])
@user_required
def refresh_screen_playlist(screen_id):
    """Ekrandaki playlist'i yeniler"""
    import traceback
    
    try:
        # Ekranı kontrol et
        from app.models.screen import Screen
        screen = Screen.find_by_id(screen_id)
        
        if not screen or screen.user_id != session['user_id']:
            flash('Ekran bulunamadı veya erişim izniniz yok.', 'danger')
            return redirect(url_for('user.screens'))
        
        # Playlist yenileme işlemini yap
        from app.models.screen_playlist import ScreenPlaylist
        result = ScreenPlaylist.refresh_screen_playlist(screen_id)
        
        if result['success']:
            flash(result['message'], 'success')
        else:
            flash(result['message'], 'danger')
            
        return redirect(url_for('user.manage_screen_content', screen_id=screen_id))
        
    except Exception as e:
        print(f"ERROR - Ekran playlist yenileme hatası: {str(e)}")
        traceback.print_exc()
        flash('Beklenmeyen bir hata oluştu.', 'danger')
        return redirect(url_for('user.screens'))