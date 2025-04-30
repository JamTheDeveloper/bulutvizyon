from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, current_app
from app.models.user import User
from app.models.screen import Screen
from app.models.media import Media
from app.models.logs import Log
from app.models.screen_media import ScreenMedia
from app.utils.decorators import supervisor_required
import os
from bson import ObjectId
from functools import wraps
from datetime import datetime

bp = Blueprint('supervisor', __name__)

@bp.route('/dashboard')
@supervisor_required
def dashboard():
    """Denetmen dashboard sayfası"""
    pending_media_count = len(Media.find_pending())
    
    user = User.find_by_id(session['user_id'])
    
    # Admin tüm medyaları görüntüleyebilir
    if user.is_admin():
        media_list = Media.find_all()
        pending_media = Media.find_pending()
    else:
        # Denetmenler sadece kendilerine atanmış kullanıcıların medyalarını görüntüleyebilir
        # TODO: Denetmene atanmış kullanıcıları getirme
        managed_users = User.find_all()  # Şimdilik tüm kullanıcılar
        managed_user_ids = [user.id for user in managed_users]
        
        media_list = []
        for media in Media.find_all():
            if media.user_id in managed_user_ids:
                media_list.append(media)
                
        pending_media = []
        for media in Media.find_pending():
            if media.user_id in managed_user_ids:
                pending_media.append(media)
    
    # Kullanıcı ve ekran sayıları
    user_count = len(User.find_all())
    screen_count = len(Screen.find_all())
    media_count = len(media_list)
    
    # Son eklenen medyaları getir (en fazla 4 tane)
    recent_media = sorted(media_list, key=lambda x: x.created_at, reverse=True)[:4]
    
    # Örnek etkinlik verileri
    import datetime
    
    recent_activities = [
        {
            'icon': 'upload',
            'color': 'primary',
            'title': 'Yeni Medya Yüklendi',
            'description': 'Kullanıcı yeni bir medya yükledi ve onay bekliyor',
            'time': datetime.datetime.now() - datetime.timedelta(minutes=5)
        },
        {
            'icon': 'check',
            'color': 'success',
            'title': 'Medya Onaylandı',
            'description': 'Bekleyen bir medya içeriği onaylandı',
            'time': datetime.datetime.now() - datetime.timedelta(hours=1)
        },
        {
            'icon': 'desktop',
            'color': 'info',
            'title': 'Yeni Ekran Eklendi',
            'description': 'Kullanıcı yeni bir ekran oluşturdu',
            'time': datetime.datetime.now() - datetime.timedelta(hours=3)
        },
        {
            'icon': 'user',
            'color': 'warning',
            'title': 'Yeni Kullanıcı',
            'description': 'Yeni bir kullanıcı kaydoldu',
            'time': datetime.datetime.now() - datetime.timedelta(days=1)
        }
    ]
    
    # Disk kullanımı (örnek değer)
    disk_usage = 45
    
    return render_template(
        'supervisor/dashboard.html', 
        pending_media_count=pending_media_count,
        pending_media=pending_media,
        user_count=user_count,
        screen_count=screen_count,
        media_count=media_count,
        recent_media=recent_media,
        recent_activities=recent_activities,
        disk_usage=disk_usage
    )

@bp.route('/media')
@supervisor_required
def media():
    """Medya listesi sayfası"""
    user = User.find_by_id(session['user_id'])
    
    # Admin tüm medyaları görüntüleyebilir
    if user.is_admin():
        media_list = Media.find_all()
    else:
        # Denetmenler sadece kendilerine atanmış kullanıcıların medyalarını görüntüleyebilir
        # TODO: Denetmene atanmış kullanıcıları getirme
        managed_users = User.find_all()  # Şimdilik tüm kullanıcılar
        managed_user_ids = [user.id for user in managed_users]
        
        media_list = []
        for media in Media.find_all():
            if media.user_id in managed_user_ids:
                media_list.append(media)
    
    return render_template('supervisor/media.html', media_list=media_list)

@bp.route('/media/pending')
@supervisor_required
def pending_media():
    """Onay bekleyen medya listesi sayfası"""
    user = User.find_by_id(session['user_id'])
    
    # Admin tüm medyaları görüntüleyebilir
    if user.is_admin():
        media_list = Media.find_pending()
    else:
        # Denetmenler sadece kendilerine atanmış kullanıcıların medyalarını görüntüleyebilir
        # TODO: Denetmene atanmış kullanıcıları getirme
        managed_users = User.find_all()  # Şimdilik tüm kullanıcılar
        managed_user_ids = [user.id for user in managed_users]
        
        media_list = []
        for media in Media.find_pending():
            if media.user_id in managed_user_ids:
                media_list.append(media)
    
    return render_template('supervisor/pending_media.html', media_list=media_list)

@bp.route('/media/view/<media_id>')
@supervisor_required
def view_media(media_id):
    """Medya detay sayfası"""
    media = Media.find_by_id(media_id)
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('supervisor.media'))
    
    # Erişim kontrolü
    user = User.find_by_id(session['user_id'])
    if not user.is_admin():
        # TODO: Denetmenin bu medyaya erişim yetkisi var mı kontrolü
        # Şimdilik tüm medyalara erişim var
        pass
    
    # Medya yükleyicisi
    media_user = User.find_by_id(media.user_id)
    
    # Kullanıcı istatistikleri
    user_media_count = 0
    user_screen_count = 0
    user_other_media = []
    
    if media_user:
        # Kullanıcının toplam medya sayısı
        user_media = Media.find_by_user(media_user.id)
        user_media_count = len(user_media)
        
        # Kullanıcının ekran sayısı
        user_screens = Screen.find_by_user(media_user.id)
        user_screen_count = len(user_screens)
        
        # Kullanıcının diğer medyaları (en fazla 5 tane)
        user_other_media = user_media[:5]
    
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
    
    return render_template(
        'supervisor/view_media.html', 
        media=media, 
        user=media_user,
        user_media_count=user_media_count,
        user_screen_count=user_screen_count,
        user_other_media=user_other_media,
        assigned_screens=assigned_screens
    )

@bp.route('/media/approve/<media_id>', methods=['POST'])
@supervisor_required
def approve_media(media_id):
    """Medya onaylama"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('supervisor.media'))
    
    # Medyayı onayla - sınıf metodunu çağır
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
    
    # Kullanıcı email'i doğru mu kontrol et
    if user and hasattr(user, 'email') and user.email:
        # Email bildirim gönder
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
        return redirect(url_for('supervisor.media'))

@bp.route('/media/reject/<media_id>', methods=['POST'])
@supervisor_required
def reject_media(media_id):
    """Medya reddetme"""
    media = Media.find_by_id(media_id)
    
    if not media:
        flash('Medya bulunamadı.', 'danger')
        return redirect(url_for('supervisor.media'))
    
    # Red sebebi
    reason = request.form.get('reason', 'İçerik politikamıza uygun değil')
    
    # Medyayı reddet - sınıf metodunu çağır
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
    
    # Kullanıcı email'i doğru mu kontrol et
    if user and hasattr(user, 'email') and user.email:
        # Email bildirim gönder
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
        return redirect(url_for('supervisor.media'))

@bp.route('/media/approve-all', methods=['POST'])
@supervisor_required
def approve_all_media():
    """Tüm bekleyen medyaları onaylama"""
    user = User.find_by_id(session['user_id'])
    
    # Admin tüm medyaları görüntüleyebilir
    if user.is_admin():
        pending_media = Media.find_pending()
    else:
        # Denetmenler sadece kendilerine atanmış kullanıcıların medyalarını görüntüleyebilir
        # TODO: Denetmene atanmış kullanıcıları getirme
        managed_users = User.find_all()  # Şimdilik tüm kullanıcılar
        managed_user_ids = [user.id for user in managed_users]
        
        pending_media = []
        for media in Media.find_pending():
            if media.user_id in managed_user_ids:
                pending_media.append(media)
    
    onay_sayisi = 0
    for media in pending_media:
        # Nesne metodu yerine sınıf metodunu kullan
        Media.update(media.id, {
            'status': Media.STATUS_ACTIVE,
            'approved_by': session['user_id'],
            'approved_at': datetime.now()
        })
        onay_sayisi += 1
        
        Log.log_action(
            action=Log.TYPE_MEDIA_APPROVE,
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={"media_id": media.id, "user_id": media.user_id}
        )
    
    flash(f'{onay_sayisi} adet medya başarıyla onaylandı.', 'success')
    return redirect(url_for('supervisor.pending_media'))

@bp.route('/users')
@supervisor_required
def users():
    """Kullanıcı listesi sayfası"""
    user = User.find_by_id(session['user_id'])
    
    # Admin tüm kullanıcıları görüntüleyebilir
    if user.is_admin():
        users_list = User.find_all()
    else:
        # Denetmenler sadece kendilerine atanmış kullanıcıları görüntüleyebilir
        # TODO: Denetmene atanmış kullanıcıları getirme
        users_list = User.find_all()  # Şimdilik tüm kullanıcılar
    
    return render_template('supervisor/users.html', users=users_list)

@bp.route('/screens/view/<screen_id>')
@supervisor_required
def view_screen(screen_id):
    """Ekran detay sayfası"""
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
    # Yetki kontrolü - Süpervizör sadece kendi ekranlarını görebilir
    if session['user_role'] != 'admin' and screen.user_id != session['user_id']:
        flash('Bu ekranı görüntüleme yetkiniz yok.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
    user = User.find_by_id(screen.user_id)
    
    # Ekrana atanmış medyaları getir
    screen_media_relations = ScreenMedia.find_by_screen(screen_id)
    
    # Medya detaylarını al ve sırala
    assigned_media = []
    for relation in screen_media_relations:
        media = Media.find_by_id(relation.media_id)
        if media:
            # Medya bilgilerine ilişki bilgilerini ekle
            media_dict = media.to_dict()
            media_dict['order'] = relation.order
            media_dict['screen_media_id'] = relation.id
            media_dict['display_time'] = relation.display_time
            assigned_media.append(media_dict)
    
    # Medyaları sıralama sırasına göre sırala
    assigned_media = sorted(assigned_media, key=lambda x: x['order'])
    
    # Ekrana atanabilecek medyaları getir (aktif ve atanmamış olanlar)
    assigned_media_ids = [m['id'] for m in assigned_media]
    available_media = []
    
    # Aktif medyaları getir ve zaten atanmışları filtrele
    for media in Media.find_all(status=Media.STATUS_ACTIVE):
        if media.id not in assigned_media_ids:
            # Yetki kontrolü - Süpervizör sadece kendi medyalarını atayabilir
            if session['user_role'] == 'admin' or media.user_id == session['user_id']:
                available_media.append(media)
    
    return render_template('supervisor/view_screen.html', 
                          screen=screen, 
                          user=user, 
                          assigned_media=assigned_media,
                          available_media=available_media)

@bp.route('/screens/assign_media/<screen_id>', methods=['POST'])
@supervisor_required
def assign_media_to_screen(screen_id):
    """Ekrana medya atama"""
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
    # Yetki kontrolü - Süpervizör sadece kendi ekranlarında düzenleme yapabilir
    if session['user_role'] != 'admin' and screen.user_id != session['user_id']:
        flash('Bu ekranda değişiklik yapma yetkiniz yok.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
    media_id = request.form.get('media_id')
    display_time = request.form.get('display_time')
    
    if not media_id:
        flash('Medya seçilmedi.', 'danger')
        return redirect(url_for('supervisor.view_screen', screen_id=screen_id))
    
    # Medya aktif mi kontrol et
    media = Media.find_by_id(media_id)
    if not media or media.status != Media.STATUS_ACTIVE:
        flash('Medya aktif değil veya bulunamadı.', 'danger')
        return redirect(url_for('supervisor.view_screen', screen_id=screen_id))
    
    # Yetki kontrolü - Süpervizör sadece kendi medyalarını atayabilir
    if session['user_role'] != 'admin' and media.user_id != session['user_id']:
        flash('Bu medyayı atama yetkiniz yok.', 'danger')
        return redirect(url_for('supervisor.view_screen', screen_id=screen_id))
    
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
    return redirect(url_for('supervisor.view_screen', screen_id=screen_id))

@bp.route('/screens/remove_media/<screen_id>/<media_id>', methods=['POST'])
@supervisor_required
def remove_media_from_screen(screen_id, media_id):
    """Ekrandan medya kaldırma"""
    # Ekran ve medya kontrolü
    screen = Screen.find_by_id(screen_id)
    media = Media.find_by_id(media_id)
    
    if not screen or not media:
        flash('Ekran veya medya bulunamadı.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
    # Yetki kontrolü - Süpervizör sadece kendi ekranlarında düzenleme yapabilir
    if session['user_role'] != 'admin' and screen.user_id != session['user_id']:
        flash('Bu ekranda değişiklik yapma yetkiniz yok.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
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
    return redirect(url_for('supervisor.view_screen', screen_id=screen_id))

@bp.route('/screens/reorder_media/<screen_id>', methods=['POST'])
@supervisor_required
def reorder_screen_media(screen_id):
    """Ekrandaki medyaları yeniden sıralama"""
    screen = Screen.find_by_id(screen_id)
    if not screen:
        flash('Ekran bulunamadı.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
    # Yetki kontrolü - Süpervizör sadece kendi ekranlarında düzenleme yapabilir
    if session['user_role'] != 'admin' and screen.user_id != session['user_id']:
        flash('Bu ekranda değişiklik yapma yetkiniz yok.', 'danger')
        return redirect(url_for('supervisor.screens'))
    
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
@supervisor_required
def profile():
    """Denetmen profil sayfası"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('supervisor.dashboard'))
    
    # Kullanıcı istatistikleri - Onayladığı ve reddettiği medya sayısı
    logs = mongo.db.logs.find({
        "user_id": user_id,
        "action": {"$in": ["media_approve", "media_reject"]}
    })
    
    approved_media = 0
    rejected_media = 0
    
    for log in logs:
        if log.get('action') == 'media_approve':
            approved_media += 1
        elif log.get('action') == 'media_reject':
            rejected_media += 1
    
    # Bekleyen medya sayısı
    pending_media = Media.count(status='pending')
    
    # Yönetilen ekran sayısı (denetmen kendi ekranlarını yönetir)
    managed_screens = Screen.count(user_id=user_id) if session['user_role'] != 'admin' else Screen.count()
    
    stats = {
        'approved_media': approved_media,
        'rejected_media': rejected_media,
        'pending_media': pending_media,
        'managed_screens': managed_screens
    }
    
    # Son etkinlikler
    recent_logs = Log.find_by_user(user_id, limit=5)
    activities = []
    
    action_colors = {
        'media_approve': 'success',
        'media_reject': 'danger',
        'screen_media_assign': 'primary',
        'screen_media_remove': 'warning',
        'login': 'info'
    }
    
    action_icons = {
        'media_approve': 'check',
        'media_reject': 'times',
        'screen_media_assign': 'plus',
        'screen_media_remove': 'minus',
        'login': 'sign-in-alt'
    }
    
    action_titles = {
        'media_approve': 'Medya Onaylandı',
        'media_reject': 'Medya Reddedildi',
        'screen_media_assign': 'Ekrana Medya Atandı',
        'screen_media_remove': 'Ekrandan Medya Kaldırıldı',
        'login': 'Giriş Yapıldı'
    }
    
    for log in recent_logs:
        action = log.get('action')
        activities.append({
            'title': action_titles.get(action, action.replace('_', ' ').title()),
            'description': f"ID: {log.get('details', {}).get('media_id', 'N/A') if 'media' in action else log.get('details', {}).get('screen_id', 'N/A')}",
            'time': log.get('timestamp'),
            'icon': action_icons.get(action, 'dot-circle'),
            'color': action_colors.get(action, 'secondary')
        })
    
    # Bildirim ayarları
    notifications = {
        'email': True,
        'media_approval': True,
        'screen_status': True
    }
    
    return render_template('supervisor/profile.html', user=user, stats=stats, activities=activities, notifications=notifications)

@bp.route('/update_profile', methods=['POST'])
@supervisor_required
def update_profile():
    """Profil bilgilerini güncelle"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('supervisor.dashboard'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    
    # Alanlar boş mu kontrolü
    if not name or not email:
        flash('Ad Soyad ve E-posta alanları gereklidir.', 'danger')
        return redirect(url_for('supervisor.profile'))
    
    # Email başka bir kullanıcı tarafından kullanılıyor mu?
    if email != user.email:
        existing_user = User.find_by_email(email)
        if existing_user and existing_user.id != user.id:
            flash('Bu e-posta adresi başka bir kullanıcı tarafından kullanılıyor.', 'danger')
            return redirect(url_for('supervisor.profile'))
    
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
    return redirect(url_for('supervisor.profile'))

@bp.route('/change_password', methods=['POST'])
@supervisor_required
def change_password():
    """Şifre değiştirme"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('supervisor.dashboard'))
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Alanlar boş mu kontrolü
    if not current_password or not new_password or not confirm_password:
        flash('Tüm şifre alanları gereklidir.', 'danger')
        return redirect(url_for('supervisor.profile'))
    
    # Mevcut şifre doğru mu?
    if not user.verify_password(current_password):
        flash('Mevcut şifre yanlış.', 'danger')
        return redirect(url_for('supervisor.profile'))
    
    # Yeni şifreler eşleşiyor mu?
    if new_password != confirm_password:
        flash('Yeni şifreler eşleşmiyor.', 'danger')
        return redirect(url_for('supervisor.profile'))
    
    # Şifre uzunluğu kontrolü
    if len(new_password) < 6:
        flash('Şifre en az 6 karakter uzunluğunda olmalıdır.', 'danger')
        return redirect(url_for('supervisor.profile'))
    
    # Şifreyi güncelle
    user.update_password(new_password)
    
    Log.log_action(
        action="password_change",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={}
    )
    
    flash('Şifreniz başarıyla değiştirildi.', 'success')
    return redirect(url_for('supervisor.profile'))

@bp.route('/update_notification_settings', methods=['POST'])
@supervisor_required
def update_notification_settings():
    """Bildirim ayarlarını güncelleme"""
    user_id = session['user_id']
    user = User.find_by_id(user_id)
    
    if not user:
        flash('Kullanıcı bulunamadı.', 'danger')
        return redirect(url_for('supervisor.dashboard'))
    
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
    return redirect(url_for('supervisor.profile')) 