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
                          active_screens_count=active_screens_count)

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
        
        Log.log_action(
            action=Log.TYPE_SCREEN_CREATE,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"screen_id": str(screen['_id']), "name": name}
        )
        
        flash('Ekran başarıyla oluşturuldu.', 'success')
        return redirect(url_for('user.screens'))
    
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
        
        # Çözünürlük kontrolü
        if request.form.get('resolution') == 'custom':
            width = request.form.get('width')
            height = request.form.get('height')
            resolution = f"{width}x{height}"
        else:
            resolution = request.form.get('resolution')
        
        # Ekranı güncelle
        screen.update(
            name=name,
            orientation=orientation,
            resolution=resolution,
            location=location,
            description=description,
            status=status,
            refresh_rate=int(refresh_rate),
            show_clock=show_clock
        )
        
        flash(f'"{name}" ekranı başarıyla güncellendi.', 'success')
        return redirect(url_for('user.screens'))
    
    return render_template('user/edit_screen.html', screen=screen)

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
    form_media_id = request.form.get('media_id')
    force_delete = request.form.get('force_delete') == '1'
    
    print(f"DELETE_MEDIA ÇAĞRILDI: media_id={media_id}, form_media_id={form_media_id}, force_delete={force_delete}")
    
    if not media_id:
        media_id = form_media_id
    
    if not media_id:
        flash('Geçersiz medya ID.', 'danger')
        return redirect(url_for('user.media'))
    
    try:
        # Basit Silme İşlemi - Hiçbir kontrol yapılmadan
        print(f"ID BİLGİSİ: {media_id}, Tip: {type(media_id)}")
        
        # Medya bilgilerini önce al (silmeden önce)
        # MongoDB'yi doğrudan kullan
        from pymongo import MongoClient
        from bson.objectid import ObjectId
        
        # Mevcut mongo bağlantısını kullan, Flask-PyMongo'dan
        db = mongo.db
        
        # Önce medya bilgilerini al
        try:
            media_collection = db.media
            media_info = media_collection.find_one({'_id': ObjectId(media_id)})
            
            if not media_info:
                # medias koleksiyonunda da ara
                if 'medias' in db.list_collection_names():
                    media_info = db.medias.find_one({'_id': ObjectId(media_id)})
            
            if media_info:
                print(f"Medya bilgileri bulundu: {media_info}")
                # Dosya adını al
                filename = media_info.get('filename')
                print(f"Silinecek dosya: {filename}")
                
                # Dosya yollarını belirleme
                upload_paths = [
                    os.path.join('app', 'static', 'uploads', filename),
                    os.path.join('static', 'uploads', filename),
                    os.path.join('/root/bulutvizyonServer/app/static/uploads', filename),
                    os.path.join('/uploads', filename)
                ]
                
                # Dosyayı fiziksel olarak silmeye çalış
                for path in upload_paths:
                    if os.path.exists(path):
                        print(f"Dosya bulundu: {path}")
                        try:
                            os.remove(path)
                            print(f"Dosya başarıyla silindi: {path}")
                            break
                        except OSError as e:
                            print(f"Dosya silme hatası: {e}")
                else:
                    print(f"Dosya bulunamadı. Kontrol edilen yollar: {upload_paths}")
            else:
                print(f"Medya bilgileri bulunamadı: {media_id}")
        except Exception as e:
            print(f"Medya bilgileri alma hatası: {str(e)}")
            
        # Medya kaydını MongoDB'den sil
        try:
            media_collection = db.media
            result = media_collection.delete_one({'_id': ObjectId(media_id)})
            print(f"Silme sonucu: {result.deleted_count}")
            
            if result.deleted_count > 0:
                flash('Medya başarıyla silindi.', 'success')
            else:
                # Alternatif koleksiyon adlarını dene
                if 'medias' in db.list_collection_names():
                    print("'medias' koleksiyonu deneniyor")
                    result = db.medias.delete_one({'_id': ObjectId(media_id)})
                    print(f"medias koleksiyonu silme sonucu: {result.deleted_count}")
                    
                    if result.deleted_count > 0:
                        flash('Medya başarıyla silindi.', 'success')
                    else:
                        flash('Medya veritabanından silindi ancak dosya silinirken sorun oluştu.', 'warning')
                else:
                    flash('Medya veritabanından silindi ancak dosya silinirken sorun oluştu.', 'warning')
        except Exception as e:
            print(f"MongoDB silme hatası: {str(e)}")
            flash(f'Medya silinirken bir hata oluştu: {str(e)}', 'danger')
        
    except Exception as e:
        print(f"Genel hata: {str(e)}")
        import traceback
        print(traceback.format_exc())
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
        return jsonify({'success': False, 'message': 'Ekran bulunamadı.'}), 404
    
    # Ekranın kullanıcıya ait olup olmadığını kontrol et
    if screen.user_id != session['user_id']:
        return jsonify({'success': False, 'message': 'Bu ekrana erişim izniniz yok.'}), 403
    
    # İçerik sıralamasını al
    content_order = request.json.get('content_order', [])
    
    # Her bir içerik için sıra numarasını güncelle
    from app.models.screen_media import ScreenMedia
    success = True
    for index, content_id in enumerate(content_order):
        screen_media = ScreenMedia.find_by_id(content_id)
        if screen_media and screen_media.screen_id == int(screen_id):
            if not screen_media.update(order=index + 1):
                success = False
    
    if success:
        return jsonify({'success': True, 'message': 'İçerik sıralaması güncellendi.'}), 200
    else:
        return jsonify({'success': False, 'message': 'İçerik sıralaması güncellenirken bir hata oluştu.'}), 500

@bp.route('/screens/<screen_id>/content', methods=['GET'])
@user_required
def manage_screen_content(screen_id):
    """Ekran içeriklerini yönetme"""
    import traceback
    
    try:
        # Ekranı kontrol et
        screen = Screen.find_by_id(screen_id)
        
        if not screen or screen.user_id != session['user_id']:
            flash('Ekran bulunamadı veya erişim izniniz yok.', 'danger')
            return redirect(url_for('user.screens'))
        
        # Ekran içeriklerini getir
        from app.models.screen_content import ScreenContent
        screen_content_list = ScreenContent.find_by_screen_id(screen_id)
        
        print(f"DEBUG - Ekran içerikleri bulundu: {len(screen_content_list)}")
        
        # Her içerik için medya bilgilerini ekle
        screen_contents_with_media = []
        for content in screen_content_list:
            try:
                media_id = content.get('media_id')
                print(f"DEBUG - İçerik için medya getiriliyor: {media_id}")
                
                media = Media.find_by_id(media_id)
                if not media:
                    print(f"DEBUG - Medya bulunamadı: {media_id}")
                    continue
                
                # İçerik nesnesine medya bilgisini ekle
                content_with_media = dict(content)
                content_with_media['media'] = media
                screen_contents_with_media.append(content_with_media)
                
                print(f"DEBUG - İçerik eklendi: ID: {content.get('_id')}, Media: {media.get('title')}")
            except Exception as e:
                print(f"DEBUG - İçerik işleme hatası: {str(e)}")
                print(traceback.format_exc())
        
        print(f"DEBUG - Toplam işlenen içerik sayısı: {len(screen_contents_with_media)}")
        
        # Atanmış playlist'i getir
        assigned_playlist = None
        from app.models.screen_playlist import ScreenPlaylist
        screen_playlist = ScreenPlaylist.find_by_screen_id(screen_id)
        
        if screen_playlist:
            print(f"DEBUG - Ekrana atanmış playlist bulundu: {screen_playlist.get('playlist_id')}")
            # Playlist detaylarını getir
            from app.models.playlist import Playlist
            playlist = Playlist.find_by_id(screen_playlist.get('playlist_id'))
            
            if playlist:
                # Playlist medyalarını getir
                from app.models.playlist_media import PlaylistMedia
                playlist_media = PlaylistMedia.find_by_playlist(screen_playlist.get('playlist_id'))
                
                assigned_playlist = {
                    'id': str(playlist.id),
                    'name': playlist.name,
                    'media_items': []
                }
                
                for item in playlist_media:
                    media = item.get('media')
                    if media:
                        assigned_playlist['media_items'].append({
                            'id': str(media.get('_id')),
                            'name': media.get('title'),
                            'media_type': media.get('file_type'),
                            'display_time': item.get('display_time')
                        })
                
                print(f"DEBUG - Atanmış playlist: {assigned_playlist}")
            else:
                print(f"DEBUG - Playlist bulunamadı: {screen_playlist.get('playlist_id')}")
        else:
            print(f"DEBUG - Ekrana atanmış playlist bulunamadı")
        
        # Kullanıcının medyaları ve kütüphane medyalarını da ekleyelim
        user_media = Media.find_by_user(session['user_id'], status=Media.STATUS_ACTIVE)
        library_media = Media.find_public()
        
        # Sözlükleri Media nesnelerine dönüştür
        user_media_objects = []
        for media in user_media:
            media_obj = Media(
                _id=media['_id'],
                user_id=media.get('user_id'),
                title=media.get('title', ''),
                filename=media.get('filename', ''),
                file_type=media.get('file_type', ''),
                file_size=media.get('file_size', 0),
                status=media.get('status', Media.STATUS_ACTIVE),
                category=media.get('category'),
                description=media.get('description'),
                duration=media.get('duration'),
                display_time=media.get('display_time', 10),
                is_public=media.get('is_public', False),
                views=media.get('views', 0),
                created_at=media.get('created_at'),
                updated_at=media.get('updated_at')
            )
            user_media_objects.append(media_obj)
        
        library_media_objects = []
        for media in library_media:
            media_obj = Media(
                _id=media['_id'],
                user_id=media.get('user_id'),
                title=media.get('title', ''),
                filename=media.get('filename', ''),
                file_type=media.get('file_type', ''),
                file_size=media.get('file_size', 0),
                status=media.get('status', Media.STATUS_ACTIVE),
                category=media.get('category'),
                description=media.get('description'),
                duration=media.get('duration'),
                display_time=media.get('display_time', 10),
                is_public=media.get('is_public', False),
                views=media.get('views', 0),
                created_at=media.get('created_at'),
                updated_at=media.get('updated_at')
            )
            library_media_objects.append(media_obj)
        
        return render_template('user/manage_screen_content.html',
                             screen=screen, 
                             screen_content=screen_contents_with_media,
                             assigned_playlist=assigned_playlist,
                             user_media=user_media_objects,
                             library_media=library_media_objects)
    except Exception as e:
        print(f"DEBUG - Genel hata: {str(e)}")
        print(traceback.format_exc())
        flash('İçerik yükleme sırasında bir hata oluştu.', 'danger')
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
    
    # Medya sahibi kontrolü
    if media.get('user_id') != session['user_id'] and not media.get('public'):
        return jsonify({'success': False, 'message': 'Bu medyaya erişim izniniz yok.'}), 403
    
    # İçerik ekle
    from app.models.screen_content import ScreenContent
    content = ScreenContent.create(
        screen_id=screen_id,
        media_id=media_id,
        display_time=display_time
    )
    
    return jsonify({'success': True, 'content_id': content.get('_id')})

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
    if not content or content.get('screen_id') != screen_id:
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
    if not content or content.get('screen_id') != screen_id:
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
        if not screen or str(screen.get('user_id')) != str(current_user.id):
            continue
        
        # Ekrana medyayı ekle
        if ScreenContent.add_media_to_screen(screen_id, media_id):
            success_count += 1
    
    if success_count > 0:
        flash(f'Medya {success_count} ekranınıza başarıyla eklendi.', 'success')
        # Log ekle
        Log.create(
            user_id=current_user.id,
            action=Log.TYPE_CONTENT_ADD,
            details=f"Medya ({media.get('title')}) {success_count} ekrana eklendi"
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
    user_id = session['user_id']
    
    # Playlistleri getir
    from app.models.playlist import Playlist
    user_playlists = Playlist.find_by_user(user_id, status=Playlist.STATUS_ACTIVE)
    
    # Public playlistleri getir
    public_playlists = Playlist.find_public()
    
    # Kullanıcının kendi oluşturduğu public playlist'leri filtrele
    public_playlists = [p for p in public_playlists if str(p.user_id) != str(user_id)]
    
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
        
        flash('Playlist başarıyla güncellendi.', 'success')
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
    available_user_media = [m for m in user_media if str(m.get('_id')) not in [str(id) for id in assigned_media_ids]]
    available_library_media = [m for m in library_media if str(m.get('_id')) not in [str(id) for id in assigned_media_ids]]
    
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
    from app.models.playlist import Playlist
    import traceback
    
    print(f"DEBUG - add_media_to_playlist başlatıldı - playlist_id: {playlist_id}")
    print(f"DEBUG - form verileri: {request.form}")
    
    try:
        playlist = Playlist.find_by_id(playlist_id)
        
        if not playlist:
            print(f"DEBUG - Playlist bulunamadı: {playlist_id}")
            flash('Playlist bulunamadı.', 'danger')
            return redirect(url_for('user.playlists'))
        
        # Erişim kontrolü - yalnızca sahibi ekleyebilir
        if str(playlist.user_id) != str(session['user_id']):
            print(f"DEBUG - Erişim hatası: playlist.user_id: {playlist.user_id}, session.user_id: {session['user_id']}")
            flash('Bu playlist\'e medya ekleme yetkiniz yok.', 'danger')
            return redirect(url_for('user.playlists'))
        
        media_id = request.form.get('media_id')
        display_time = request.form.get('display_time')
        
        print(f"DEBUG - media_id: {media_id}, display_time: {display_time}")
        
        if not media_id:
            print("DEBUG - media_id boş")
            flash('Lütfen bir medya seçin.', 'warning')
            return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))
        
        # Medyayı kontrol et
        from app.models.media import Media
        media = Media.find_by_id(media_id)
        
        if not media:
            print(f"DEBUG - Medya bulunamadı: {media_id}")
            flash('Seçilen medya bulunamadı.', 'danger')
            return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))
        
        # Medya erişim kontrolü - kullanıcının kendi medyası veya public medya olmalı
        if str(media.get('user_id')) != str(session['user_id']) and not media.get('is_public'):
            print(f"DEBUG - Medya erişim hatası: media.user_id: {media.get('user_id')}, session.user_id: {session['user_id']}")
            flash('Bu medyaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))
        
        # Display time'ı sayıya çevir
        try:
            display_time = int(display_time) if display_time else None
        except ValueError:
            display_time = None
        
        print(f"DEBUG - Dönüştürülmüş display_time: {display_time}")
        
        # Medyayı playlist'e ekle
        from app.models.playlist_media import PlaylistMedia
        print(f"DEBUG - PlaylistMedia.create çağrılıyor: playlist_id: {playlist_id}, media_id: {media_id}")
        
        try:
            result = PlaylistMedia.create({
                'playlist_id': playlist_id,
                'media_id': media_id,
                'display_time': display_time
            })
            print(f"DEBUG - PlaylistMedia.create sonucu: {result}")
        except Exception as e:
            print(f"DEBUG - PlaylistMedia.create hatası: {str(e)}")
            print(traceback.format_exc())
            flash('Medya eklenirken bir hata oluştu.', 'danger')
            return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))
        
        # Log kaydı
        Log.log_action(
            action="playlist_add_media",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"playlist_id": playlist_id, "media_id": media_id}
        )
        
        flash('Medya playlist\'e başarıyla eklendi.', 'success')
        return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))
    except Exception as e:
        print(f"DEBUG - Genel hata: {str(e)}")
        print(traceback.format_exc())
        flash('Beklenmeyen bir hata oluştu.', 'danger')
        return redirect(url_for('user.edit_playlist', playlist_id=playlist_id))

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
    
    playlist = Playlist.find_by_id(playlist_id)
    
    if not playlist:
        return jsonify({'success': False, 'message': 'Playlist bulunamadı.'}), 404
    
    # Erişim kontrolü - yalnızca sahibi düzenleyebilir
    if str(playlist.user_id) != str(session['user_id']):
        return jsonify({'success': False, 'message': 'Bu playlist\'i düzenleme yetkiniz yok.'}), 403
    
    data = request.get_json()
    media_order = data.get('media_order', [])
    
    if not media_order:
        return jsonify({'success': False, 'message': 'Geçersiz sıralama verisi.'}), 400
    
    # Sıralamayı güncelle
    from app.models.playlist_media import PlaylistMedia
    result = PlaylistMedia.reorder_playlist_media(playlist_id, media_order)
    
    if result:
        # Log kaydı
        Log.log_action(
            action="playlist_reorder",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"playlist_id": playlist_id}
        )
        
        return jsonify({'success': True, 'message': 'Sıralama güncellendi.'}), 200
    else:
        return jsonify({'success': False, 'message': 'Sıralama güncellenirken bir hata oluştu.'}), 500

@bp.route('/screens/<screen_id>/assign_playlist', methods=['GET', 'POST'])
@user_required
def assign_playlist_to_screen(screen_id):
    """Ekrana playlist atama"""
    import traceback
    
    # Ekranı kontrol et
    screen = Screen.find_by_id(screen_id)
    
    if not screen or screen.user_id != session['user_id']:
        flash('Ekran bulunamadı veya erişim izniniz yok.', 'danger')
        return redirect(url_for('user.screens'))
    
    if request.method == 'POST':
        playlist_id = request.form.get('playlist_id')
        
        if not playlist_id:
            flash('Lütfen bir playlist seçin.', 'warning')
            return redirect(request.url)
        
        # Playlist'i kontrol et
        from app.models.playlist import Playlist
        playlist = Playlist.find_by_id(playlist_id)
        
        if not playlist:
            flash('Seçilen playlist bulunamadı.', 'danger')
            return redirect(request.url)
        
        # Erişim kontrolü - kullanıcının kendi playlist'i veya public playlist olmalı
        if str(playlist.user_id) != str(session['user_id']) and not playlist.is_public:
            flash('Bu playlist\'e erişim yetkiniz yok.', 'danger')
            return redirect(request.url)
        
        try:
            # Önce ekrandaki tüm içerikleri temizle
            from app.models.screen_content import ScreenContent
            print(f"DEBUG - Mevcut ekran içeriklerini temizleme: {screen_id}")
            delete_count = ScreenContent.delete_by_screen(screen_id)
            print(f"DEBUG - Silinen içerik sayısı: {delete_count}")
            
            # Playlist'teki medyaları ekrana ekle
            from app.models.playlist_media import PlaylistMedia
            playlist_media = PlaylistMedia.find_by_playlist(playlist_id)
            print(f"DEBUG - Playlist medya sayısı: {len(playlist_media)}")
            print(f"DEBUG - Playlist medyalar: {playlist_media}")
            
            created_contents = []
            for index, item in enumerate(playlist_media):
                media = item.get('media')
                if media:
                    print(f"DEBUG - Ekrana ekleniyor: Media ID: {media.get('_id')}, Sıra: {index}, Gösterim süresi: {item.get('display_time')}")
                    # ScreenContent oluştur
                    content_data = {
                        'screen_id': screen_id,
                        'media_id': str(media.get('_id')),
                        'order': index,
                        'display_time': item.get('display_time')
                    }
                    try:
                        content = ScreenContent.create(content_data)
                        print(f"DEBUG - Ekran içeriği oluşturuldu: {content.get('_id')}")
                        created_contents.append(content)
                    except Exception as e:
                        print(f"DEBUG - Ekran içeriği oluşturma hatası: {str(e)}")
                        print(traceback.format_exc())
                else:
                    print(f"DEBUG - Medya bulunamadı veya geçersiz: {item}")
            
            print(f"DEBUG - Toplam oluşturulan içerik sayısı: {len(created_contents)}")
            
            # Ekran-Playlist ilişkisi oluştur/güncelle
            from app.models.screen_playlist import ScreenPlaylist
            screen_playlist = ScreenPlaylist.create({
                'screen_id': screen_id,
                'playlist_id': playlist_id
            })
            print(f"DEBUG - Ekran-Playlist ilişkisi oluşturuldu: {screen_playlist.get('_id')}")
            
            # Log kaydı
            Log.log_action(
                action="screen_assign_playlist",
                user_id=session['user_id'],
                ip_address=request.remote_addr,
                details={"screen_id": screen_id, "playlist_id": playlist_id}
            )
            
            flash('Playlist ekrana başarıyla atandı.', 'success')
            return redirect(url_for('user.manage_screen_content', screen_id=screen_id))
        except Exception as e:
            print(f"DEBUG - Genel hata: {str(e)}")
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
    
    return render_template('user/assign_playlist.html',
                          screen=screen,
                          user_playlists=user_playlists,
                          public_playlists=public_playlists)

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
        
        print(f"DEBUG - Medya bulundu: id={media.get('_id')}, title={media.get('title')}")
        
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
                    'display_time': media.get('display_time', 10),
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
                            "media_title": media.get('title', '')
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