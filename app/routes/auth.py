from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app, jsonify
from werkzeug.security import check_password_hash
from app.models.user import User
from app.models.logs import Log
import secrets
import datetime
from flask_wtf.csrf import CSRFProtect
from app import csrf

bp = Blueprint('auth', __name__)

@bp.route('/', methods=['GET'])
def index():
    """Ana sayfa"""
    current_user = None # Başlangıçta None olarak ayarla
    if 'user_id' in session:
        user = User.find_by_id(session['user_id'])
        if user:
            current_user = user # Template'e göndermek için atama (gerçi redirect olacak)
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            elif user.is_supervisor():
                return redirect(url_for('supervisor.dashboard'))
            else: # Normal kullanıcı
                return redirect(url_for('user.dashboard'))
        else:
            # Geçersiz user_id session'da kalmışsa temizle
            session.pop('user_id', None)

    # Kullanıcı giriş yapmamışsa veya geçersiz session varsa index'i render et
    # current_user None olacak ve base.html bunu handle edebilmeli (login butonu gösterir)
    return render_template('index.html', current_user=current_user)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Kullanıcı giriş sayfası"""
    # Zaten oturum açılmışsa dashboard'a yönlendir
    if 'user_id' in session:
        print(f"Login: Zaten oturum açılmış. user_id: {session['user_id']}")
        user = User.find_by_id(session['user_id'])
        if user:
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            elif user.is_supervisor():
                return redirect(url_for('supervisor.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
        else:
            print("Login: Kullanıcı bulunamadı, session temizleniyor")
            session.clear()

    # POST isteği: Giriş işlemi
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"Login: Giriş denemesi için email: {email}")
        
        user = User.find_by_email(email)
        
        if not user:
            print(f"Login: Kullanıcı bulunamadı, email: {email}")
            flash('Geçersiz e-posta veya şifre.', 'danger')
            return render_template('auth/login.html')
            
        if not user.verify_password(password):
            print(f"Login: Şifre doğrulanmadı, kullanıcı: {user.name}")
            flash('Geçersiz e-posta veya şifre.', 'danger')
            return render_template('auth/login.html')
        
        if user.status != User.STATUS_ACTIVE:
            print(f"Login: Kullanıcı aktif değil, durum: {user.status}")
            flash('Hesabınız aktif değil. Lütfen yönetici ile iletişime geçin.', 'danger')
            return render_template('auth/login.html')
            
        # Kullanıcı giriş bilgilerini doğrula ve oturum oluştur
        session['user_id'] = user.id
        user.update_last_login()
        
        print(f"Login: Giriş başarılı, user_id: {user.id}, rol: {user.role}")
        
        # Log kaydı oluştur
        Log.log_action(
            action="user_login",
            user_id=user.id,
            ip_address=request.remote_addr,
            details={"email": email}
        )
        
        # Kullanıcı rolüne göre yönlendir
        if user.is_admin():
            return redirect(url_for('admin.dashboard'))
        elif user.is_supervisor():
            return redirect(url_for('supervisor.dashboard'))
        else:
            return redirect(url_for('user.dashboard'))
    
    return render_template('auth/login.html')

@bp.route('/logout')
def logout():
    """Çıkış işlemi"""
    if 'user_id' in session:
        Log.log_action(
            action=Log.TYPE_LOGOUT,
            user_id=session['user_id'],
            ip_address=request.remote_addr
        )
        session.pop('user_id', None)
    
    return redirect(url_for('auth.login'))

@bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password_request():
    """Şifre sıfırlama isteği - Artık forgot_password kullanılacak"""
    return redirect(url_for('auth.forgot_password'))

@bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_old(token):
    """Eski şifre sıfırlama metodu - Yeni endpoint'e yönlendir"""
    return redirect(url_for('auth.reset_password', token=token))

@bp.route('/first-login', methods=['GET', 'POST'])
def first_login():
    """İlk giriş şifre değiştirme"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    user = User.find_by_id(session['user_id'])
    
    if not user or user.status != User.STATUS_PENDING:
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if password != password_confirm:
            flash('Şifreler eşleşmiyor.', 'danger')
        else:
            user.password = User.hash_password(password)
            user.status = User.STATUS_ACTIVE
            user.save()
            
            flash('Şifreniz başarıyla güncellendi.', 'success')
            
            if user.is_admin():
                return redirect(url_for('admin.dashboard'))
            elif user.is_supervisor():
                return redirect(url_for('supervisor.dashboard'))
            else:
                return redirect(url_for('user.dashboard'))
    
    return render_template('auth/first_login.html')

@bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Şifre sıfırlama isteği sayfası"""
    if request.method == 'POST':
        email = request.form.get('email')
        
        if not email:
            flash('Lütfen e-posta adresinizi girin.', 'danger')
            return render_template('auth/forgot_password.html')
        
        # Kullanıcı kontrolü
        user = User.find_by_email(email)
        if not user:
            # Güvenlik için kullanıcı bulunamadı mesajı verme
            flash('Eğer hesabınız varsa, şifre sıfırlama bağlantısı e-posta adresinize gönderildi.', 'info')
            return render_template('auth/forgot_password.html')
        
        # Token oluştur
        import secrets
        token = secrets.token_urlsafe(32)
        
        # Token'ı veritabanına kaydet (24 saat geçerli)
        from datetime import datetime, timedelta
        expires = datetime.now() + timedelta(hours=24)
        user.update(
            reset_token=token,
            reset_token_expires=expires
        )
        
        # Şifre sıfırlama e-postası gönder
        reset_url = url_for('auth.reset_password', token=token, _external=True)
        
        try:
            # Basit e-posta içeriği - Yalnızca ASCII karakterler
            from app.utils.email import Mailer
            mailer = Mailer()
            simple_content = """
            <html>
            <body>
                <p>Merhaba,</p>
                <p>Sifrenizi sifirlamak icin asagidaki baglantiya tiklayin:</p>
                <p><a href="{}">Sifremi Sifirla</a></p>
                <p>Baglanti: {}</p>
                <p>Tesekkurler,<br>BulutVizyon</p>
            </body>
            </html>
            """.format(reset_url, reset_url)
            
            result = mailer.sendHTML(
                to=email,
                subject="BulutVizyon - Sifre Sifirlama", 
                content=simple_content
            )
            
            if not result:
                # E-posta gönderilemezse hatayı kaydet
                current_app.logger.error(f"Şifre sıfırlama e-postası gönderilemedi: {email}")
                flash('E-posta gönderilirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
                return render_template('auth/forgot_password.html')
                
        except Exception as e:
            current_app.logger.error(f"Şifre sıfırlama e-postası hazırlanırken hata: {str(e)}")
            flash('E-posta gönderilirken bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger')
            return render_template('auth/forgot_password.html')
        
        # Log kaydı
        Log.log_action(
            action="password_reset_request",
            user_id=user.id,
            ip_address=request.remote_addr,
            details={"email": email}
        )
        
        flash('Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/forgot_password.html')

@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Şifre sıfırlama"""
    # Token doğrulaması
    if not token:
        flash('Geçersiz veya süresi dolmuş token.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Kullanıcıyı token ile bul
    user = User.find_by_reset_token(token)
    if not user:
        flash('Geçersiz veya süresi dolmuş token.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Token süresi dolmuş mu kontrolü
    from datetime import datetime
    if user.reset_token_expires < datetime.now():
        flash('Şifre sıfırlama bağlantısının süresi dolmuş. Lütfen yeni bir şifre sıfırlama bağlantısı talep edin.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Şifre boş mu kontrolü
        if not password or not confirm_password:
            flash('Şifre alanları gereklidir.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Şifreler eşleşiyor mu kontrolü
        if password != confirm_password:
            flash('Şifreler eşleşmiyor.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Şifre uzunluğu kontrolü
        if len(password) < 6:
            flash('Şifre en az 6 karakter uzunluğunda olmalıdır.', 'danger')
            return render_template('auth/reset_password.html', token=token)
        
        # Şifreyi güncelle ve token'ları sıfırla
        user.set_password(password)
        user.update(
            reset_token=None,
            reset_token_expires=None
        )
        
        # Log kaydı
        Log.log_action(
            action="password_reset_success",
            user_id=user.id,
            ip_address=request.remote_addr,
            details={}
        )
        
        flash('Şifreniz başarıyla sıfırlandı. Şimdi giriş yapabilirsiniz.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/reset_password.html', token=token)

@bp.route('/about')
def about():
    """Hakkımızda sayfası"""
    return render_template('pages/about.html')

@bp.route('/faq')
def faq():
    """Sıkça Sorulan Sorular sayfası"""
    return render_template('pages/faq.html')
    
@bp.route('/delivery')
def delivery():
    """Teslimat Bilgileri sayfası"""
    return render_template('pages/delivery.html')
    
@bp.route('/privacy')
def privacy():
    """Gizlilik İlkeleri sayfası"""
    return render_template('pages/privacy.html')
    
@bp.route('/refund')
def refund():
    """İade Koşulları sayfası"""
    return render_template('pages/refund.html')
    
@bp.route('/terms')
def terms():
    """Şartlar ve Koşullar sayfası"""
    return render_template('pages/terms.html')

@bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """İletişim sayfası"""
    success_message = None
    error_message = None
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        # Form alanlarını kontrol et
        if not name or not email or not subject or not message:
            error_message = "Lütfen tüm alanları doldurun."
            return render_template('pages/contact.html', error_message=error_message)
        
        try:
            # E-posta gönderme işlemi
            from app.utils.email import Mailer
            mailer = Mailer()
            
            # E-posta içeriği
            email_content = f"""
            <html>
            <body>
                <h3>İletişim Formu Mesajı</h3>
                <p><strong>Gönderen:</strong> {name}</p>
                <p><strong>E-posta:</strong> {email}</p>
                <p><strong>Konu:</strong> {subject}</p>
                <p><strong>Mesaj:</strong></p>
                <p>{message}</p>
            </body>
            </html>
            """
            
            # E-postayı gönder
            result = mailer.sendHTML(
                to="satis@elektrobil.com.tr",
                subject=f"İletişim Formu: {subject}",
                content=email_content
            )
            
            if result:
                success_message = "Mesajınız başarıyla gönderildi. En kısa sürede size dönüş yapacağız."
                
                # Log kaydı oluştur
                Log.log_action(
                    action="contact_form_submit",
                    user_id=session.get('user_id'),
                    ip_address=request.remote_addr,
                    details={"name": name, "email": email, "subject": subject}
                )
            else:
                error_message = "Mesajınız gönderilirken bir hata oluştu. Lütfen daha sonra tekrar deneyin."
        
        except Exception as e:
            current_app.logger.error(f"İletişim formu e-posta gönderimi hatası: {str(e)}")
            error_message = "Mesajınız gönderilirken bir hata oluştu. Lütfen daha sonra tekrar deneyin."
    
    return render_template('pages/contact.html', success_message=success_message, error_message=error_message) 