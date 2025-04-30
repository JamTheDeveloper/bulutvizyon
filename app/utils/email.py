import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid
from flask import current_app, render_template
from flask_mail import Mail, Message
from datetime import datetime
from email.header import Header

logger = logging.getLogger(__name__)

class Mailer:
    def __init__(self):
        self.server = os.environ.get('MAIL_SERVER', 'mail.elektrobil.com.tr')
        self.username = os.environ.get('MAIL_USERNAME', 'bulutvizyon@elektrobil.com.tr')
        self.port = int(os.environ.get('MAIL_PORT', 587))
        self.password = os.environ.get('MAIL_PASSWORD', '')
        self.from_email = os.environ.get('MAIL_DEFAULT_SENDER', 'bulutvizyon@elektrobil.com.tr')

    def send(self, **kwargs):
        try:
            # Sadece bir HTML veya düz metin içerik kullan, multipart yerine
            if kwargs['content_type'] == 'html':
                msg = MIMEText(kwargs['content'].encode('utf-8'), 'html', _charset='utf-8')
            else:
                msg = MIMEText(kwargs['content'].encode('utf-8'), 'plain', _charset='utf-8')
            
            # Header ile UTF-8 kodlamalı konu ve adresler ekle
            msg['Subject'] = Header(kwargs['subject'], 'utf-8')
            msg['From'] = self.from_email
            msg['To'] = kwargs['to']
            msg['Message-ID'] = make_msgid()
            
            # SMTP bağlantısı
            s = smtplib.SMTP(self.server, self.port)
            try:
                try:
                    s.starttls()
                except Exception as e:
                    logger.warning(f"TLS başlatma hatası (önemli değil): {str(e)}")
                
                # Giriş yap ve gönder
                s.login(self.username, self.password)
                
                # RFC 5322 uyumlu mesaj metni oluştur
                msg_str = msg.as_string()
                logger.info(f"E-posta gönderiliyor: Kime={kwargs['to']}, Konu='{kwargs['subject']}'")
                s.sendmail(self.from_email, kwargs['to'], msg_str.encode('utf-8'))
                
                logger.info(f"E-posta başarıyla gönderildi: {kwargs['to']}")
                return True
            except Exception as e:
                logger.error(f"E-posta '{kwargs['to']}' adresine gönderilemedi: {str(e)}", exc_info=True)
                return False
            finally:
                try:
                    s.quit()
                except:
                    pass
        except Exception as e:
            logger.error(f"E-posta hazırlanırken hata: {str(e)}", exc_info=True)
            return False

    def sendHTML(self, **kwargs):
        kwargs['content_type'] = "html"
        return self.send(**kwargs)

    def sendText(self, **kwargs):
        kwargs['content_type'] = "plain"
        return self.send(**kwargs)

# Flask uygulaması için yardımcı fonksiyonlar
def send_email(to, subject, template):
    """E-posta gönderme fonksiyonu"""
    mailer = Mailer()
    return mailer.sendHTML(
        to=to,
        subject=subject,
        content=template
    )

def send_welcome_email(to_email, name, initial_password, login_url):
    """Yeni kullanıcıya hoşgeldin e-postası gönderir"""
    subject = f"BulutVizyon'a Hoş Geldiniz, {name}!"
    
    template = render_template(
        'emails/welcome.html',
        name=name,
        email=to_email,
        initial_password=initial_password,
        login_url=login_url,
        company_name=current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        company_address=current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        now=datetime.now()
    )
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=to_email,
            subject=subject,
            content=template
        )
        logger.info(f"Hoşgeldin e-postası şu adrese gönderildi: {to_email}")
        return result
    except Exception as e:
        logger.error(f"Hoşgeldin e-postası gönderilirken hata oluştu: {str(e)}")
        return False

def send_password_reset_email(email, reset_url):
    """Şifre sıfırlama e-postası gönderir"""
    subject = "BulutVizyon - Şifre Sıfırlama"
    
    template = render_template(
        'emails/reset_password.html',
        reset_url=reset_url,
        company_name=current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        company_address=current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        now=datetime.now()
    )
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=email,
            subject=subject,
            content=template
        )
        logger.info(f"Şifre sıfırlama e-postası şu adrese gönderildi: {email}")
        return result
    except Exception as e:
        logger.error(f"Şifre sıfırlama e-postası gönderilirken hata oluştu: {str(e)}")
        return False

def send_media_notification(email, name, media_title, status, reason=None):
    """Medya onay/red bildirim e-postası gönderir"""
    if status == 'approved':
        subject = f"BulutVizyon - Medyanız Onaylandı: {media_title}"
        template_file = 'emails/media_approved.html'
    else:
        subject = f"BulutVizyon - Medyanız Reddedildi: {media_title}"
        template_file = 'emails/media_rejected.html'
    
    template = render_template(
        template_file,
        name=name,
        media_title=media_title,
        reason=reason,
        company_name=current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        company_address=current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        now=datetime.now()
    )
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=email,
            subject=subject,
            content=template
        )
        logger.info(f"Medya bildirim e-postası şu adrese gönderildi: {email}")
        return result
    except Exception as e:
        logger.error(f"Medya bildirim e-postası gönderilirken hata oluştu: {str(e)}")
        return False

def send_screen_status_notification(email, name, screen_name, status):
    """Ekran durum değişikliği bildirim e-postası gönderir"""
    status_text = "aktif" if status == "active" else "devre dışı"
    subject = f"BulutVizyon - Ekran Durumu Değişti: {screen_name}"
    
    template = render_template(
        'emails/screen_status.html',
        name=name,
        screen_name=screen_name,
        status=status_text,
        company_name=current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        company_address=current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        now=datetime.now()
    )
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=email,
            subject=subject,
            content=template
        )
        logger.info(f"Ekran durum değişikliği e-postası şu adrese gönderildi: {email}")
        return result
    except Exception as e:
        logger.error(f"Ekran durum değişikliği e-postası gönderilirken hata oluştu: {str(e)}")
        return False

def send_media_approval_notification(email, name, media_title, media_type=None, upload_date=None, preview_url=None, dashboard_url=None):
    """Medya onay bildirimi e-postası gönderir"""
    subject = f"BulutVizyon - Medya Onay Bildirimi: {media_title}"
    
    template = render_template(
        'emails/media_approved.html',
        name=name,
        media_title=media_title,
        media_type=media_type,
        upload_date=upload_date,
        preview_url=preview_url,
        dashboard_url=dashboard_url,
        company_name=current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        company_address=current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        now=datetime.now()
    )
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=email,
            subject=subject,
            content=template
        )
        logger.info(f"Medya onay bildirimi e-postası şu adrese gönderildi: {email}")
        return result
    except Exception as e:
        logger.error(f"Medya onay bildirimi e-postası gönderilirken hata oluştu: {str(e)}")
        return False

def send_media_rejection_notification(email, name, media_title, reason=None):
    """Medya red bildirimi e-postası gönderir"""
    subject = f"BulutVizyon - Medyanız Reddedildi: {media_title}"
    
    template = render_template(
        'emails/media_rejected.html',
        name=name,
        media_title=media_title,
        reason=reason,
        company_name=current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        company_address=current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        now=datetime.now()
    )
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=email,
            subject=subject,
            content=template
        )
        logger.info(f"Medya red bildirimi e-postası şu adrese gönderildi: {email}")
        return result
    except Exception as e:
        logger.error(f"Medya red bildirimi e-postası gönderilirken hata oluştu: {str(e)}")
        return False

def send_screen_status_change_notification(email, name, screen_name, screen_code, new_status, reason=None):
    """Ekran durum değişikliği bildirimi e-postası gönderir"""
    status_text = "aktifleştirildi" if new_status == "active" else "devre dışı bırakıldı"
    subject = f"BulutVizyon - Ekran Durumu Değişti: {screen_name}"
    
    template = render_template(
        'emails/screen_status_change.html',
        name=name,
        screen_name=screen_name,
        screen_code=screen_code,
        status=status_text,
        reason=reason,
        company_name=current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        company_address=current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        now=datetime.now()
    )
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=email,
            subject=subject,
            content=template
        )
        logger.info(f"Ekran durum değişikliği bildirimi e-postası şu adrese gönderildi: {email}")
        return result
    except Exception as e:
        logger.error(f"Ekran durum değişikliği bildirimi e-postası gönderilirken hata oluştu: {str(e)}")
        return False

def send_notification(email, subject, template_path, **kwargs):
    """Genel bildirim e-postası gönderir"""
    # Şablon için ortak değişkenler ekle
    kwargs.update({
        'company_name': current_app.config.get('COMPANY_NAME', 'BulutVizyon'),
        'company_address': current_app.config.get('COMPANY_ADDRESS', 'Ankara, Türkiye'),
        'now': datetime.now()
    })
    
    template = render_template(template_path, **kwargs)
    
    try:
        mailer = Mailer()
        result = mailer.sendHTML(
            to=email,
            subject=subject,
            content=template
        )
        logger.info(f"Bildirim e-postası şu adrese gönderildi: {email}")
        return result
    except Exception as e:
        logger.error(f"Bildirim e-postası gönderilirken hata oluştu: {str(e)}")
        return False 