"""
E-posta gönderme işlemleri için yardımcı fonksiyonlar
"""
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from flask import current_app
import logging
import base64
from email import charset


def send_email(subject, recipients, content, html_content=None):
    """
    E-posta gönderimi için genel fonksiyon
    
    Args:
        subject (str): E-posta konusu
        recipients (list): Alıcı e-posta adresleri listesi
        content (str): Düz metin içerik
        html_content (str, optional): HTML formatında içerik
    
    Returns:
        bool: Gönderim başarılı olduysa True, aksi takdirde False
    """
    try:
        # E-posta ayarlarını al - önce current_app.config'den dene
        smtp_server = current_app.config.get('MAIL_SERVER')
        smtp_port = current_app.config.get('MAIL_PORT')
        smtp_username = current_app.config.get('MAIL_USERNAME')
        smtp_password = current_app.config.get('MAIL_PASSWORD')
        sender_email = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        # Eğer config'de yoksa direkt çevre değişkenlerinden al
        if not smtp_server:
            smtp_server = os.environ.get('MAIL_SERVER')
        if not smtp_port:
            smtp_port = os.environ.get('MAIL_PORT')
        if not smtp_username:
            smtp_username = os.environ.get('MAIL_USERNAME')
        if not smtp_password:
            smtp_password = os.environ.get('MAIL_PASSWORD')
        if not sender_email:
            sender_email = os.environ.get('MAIL_DEFAULT_SENDER')
        
        # Port değerini int'e çevir
        if smtp_port and isinstance(smtp_port, str):
            try:
                smtp_port = int(smtp_port)
            except ValueError:
                smtp_port = 587  # Varsayılan port
        
        # Alınan değerleri log'a yaz (şifre hariç)
        logging.info(f"SMTP ayarları: SERVER={smtp_server}, PORT={smtp_port}, USER={smtp_username}, SENDER={sender_email}")
        
        if not all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
            logging.error("E-posta ayarları eksik. Lütfen yapılandırma dosyasını kontrol edin.")
            logging.error(f"Eksik değerler: server={bool(smtp_server)}, port={bool(smtp_port)}, username={bool(smtp_username)}, password={bool(smtp_password)}, sender={bool(sender_email)}")
            return False
        
        # E-posta mesajını oluştur
        msg = MIMEMultipart('alternative')
        
        # Türkçe karakterler için UTF-8 kodlaması
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = sender_email
        msg['To'] = ', '.join(recipients)
        
        # Düz metin içerik - UTF-8 kodlaması kullan
        part1 = MIMEText(content, 'plain', 'utf-8')
        msg.attach(part1)
        
        # HTML içerik (varsa) - UTF-8 kodlaması kullan
        if html_content:
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part2)
        
        # SMTP bağlantısı kur ve e-postayı gönder
        logging.info(f"SMTP bağlantısı kuruluyor: {smtp_server}:{smtp_port}")
        
        # Debug modu etkinleştir
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.set_debuglevel(1)  # Debug bilgilerini göster
        
        # Bağlantı bilgilerini log'a yazdır
        logging.info("EHLO komutu gönderiliyor...")
        server.ehlo()
        
        # TLS bağlantısını başlat
        logging.info("TLS bağlantısı başlatılıyor...")
        server.starttls()
        server.ehlo()  # TLS sonrası yeniden EHLO
        
        # Giriş yap
        logging.info(f"Giriş yapılıyor: {smtp_username}")
        server.login(smtp_username, smtp_password)
        
        # E-posta gönder
        logging.info(f"E-posta gönderiliyor: {subject} -> {recipients}")
        server.sendmail(sender_email, recipients, msg.as_string())
        
        # Bağlantıyı kapat
        logging.info("SMTP bağlantısı kapatılıyor")
        server.quit()
        
        logging.info(f"E-posta başarıyla gönderildi: {subject} - Alıcılar: {recipients}")
        return True
    
    except Exception as e:
        logging.error(f"E-posta gönderiminde hata: {str(e)}")
        # Hata türüne göre daha detaylı mesaj
        if isinstance(e, smtplib.SMTPAuthenticationError):
            logging.error("Kimlik doğrulama hatası. Kullanıcı adı ve şifrenizi kontrol edin.")
            logging.error("Gmail kullanıyorsanız, 'Daha az güvenli uygulamalara izin ver' ayarını etkinleştirin veya uygulama şifresi kullanın.")
        elif isinstance(e, smtplib.SMTPConnectError):
            logging.error(f"SMTP sunucusuna bağlanırken hata: {smtp_server}:{smtp_port}")
        elif isinstance(e, smtplib.SMTPServerDisconnected):
            logging.error("SMTP sunucusu bağlantıyı beklenmedik şekilde kapattı.")
        elif isinstance(e, UnicodeEncodeError):
            logging.error("Unicode kodlama hatası. Türkçe karakterleri göndermede sorun oluştu.")
            
        return False

def notify_admin_for_new_led_screen(user, screen):
    """
    LED ekran oluşturulduğunda admin kullanıcılarını bilgilendir
    
    Args:
        user (User): Ekranı oluşturan kullanıcı 
        screen (dict): Oluşturulan ekran bilgileri
    
    Returns:
        bool: Bildirim gönderildi ise True, aksi halde False
    """
    try:
        from app.models.user import User
        
        # Karakter kodlama ayarlarını değiştir - UTF-8 için
        # Bu, en temel seviyede karakter kodlama sorunlarını çözer
        charset.add_charset('utf-8', charset.SHORTEST, charset.QP, 'utf-8')
        
        # Admin kullanıcılarını bul
        admin_users = User.find_by_role('admin')
        if not admin_users:
            logging.warning("Bildirim gönderilebilecek admin kullanıcısı bulunamadı.")
            return False
        
        admin_emails = [admin.email for admin in admin_users if admin.email]
        if not admin_emails:
            logging.warning("Admin kullanıcıların e-posta adresleri bulunamadı.")
            return False
        
        # E-posta konusu - Header olarak kodla
        subject = Header("BulutVizyon: Yeni LED Ekran Oluşturuldu", 'utf-8')
        
        # Düz metin içerik
        content = f"""
Yeni bir LED ekran oluşturuldu.

Kullanıcı Bilgileri:
-------------------
Kullanıcı ID: {user.id}
Ad Soyad: {user.name}
E-posta: {user.email}
Telefon: {getattr(user, 'phone', 'Belirtilmemiş')}

Ekran Bilgileri:
-------------------
Ekran ID: {screen.get('_id')}
Ekran Adı: {screen.get('name')}
Konum: {screen.get('location') or 'Belirtilmemiş'}
Çözünürlük: {screen.get('resolution')}
Yön: {screen.get('orientation')}
API Anahtarı: {screen.get('api_key')}
Oluşturulma Tarihi: {screen.get('created_at')}

Bu bildirim otomatik olarak gönderilmiştir.
        """
        
        # HTML içerik
        html_content = f"""
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        h2 {{ color: #2c3e50; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .section {{ margin-bottom: 20px; }}
        .label {{ font-weight: bold; color: #7f8c8d; }}
        .value {{ margin-left: 10px; }}
        .api-key {{ font-family: monospace; background-color: #f8f9fa; padding: 5px; border: 1px solid #ddd; }}
        .footer {{ font-size: 12px; color: #95a5a6; margin-top: 30px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Yeni LED Ekran Oluşturuldu</h2>
        
        <div class="section">
            <h3>Kullanıcı Bilgileri</h3>
            <p><span class="label">Kullanıcı ID:</span> <span class="value">{user.id}</span></p>
            <p><span class="label">Ad Soyad:</span> <span class="value">{user.name}</span></p>
            <p><span class="label">E-posta:</span> <span class="value">{user.email}</span></p>
            <p><span class="label">Telefon:</span> <span class="value">{getattr(user, 'phone', 'Belirtilmemiş')}</span></p>
        </div>
        
        <div class="section">
            <h3>Ekran Bilgileri</h3>
            <p><span class="label">Ekran ID:</span> <span class="value">{screen.get('_id')}</span></p>
            <p><span class="label">Ekran Adı:</span> <span class="value">{screen.get('name')}</span></p>
            <p><span class="label">Konum:</span> <span class="value">{screen.get('location') or 'Belirtilmemiş'}</span></p>
            <p><span class="label">Çözünürlük:</span> <span class="value">{screen.get('resolution')}</span></p>
            <p><span class="label">Yön:</span> <span class="value">{screen.get('orientation')}</span></p>
            <p><span class="label">API Anahtarı:</span> <span class="value api-key">{screen.get('api_key')}</span></p>
            <p><span class="label">Oluşturulma Tarihi:</span> <span class="value">{screen.get('created_at')}</span></p>
        </div>
        
        <div class="footer">
            Bu bildirim otomatik olarak gönderilmiştir.
        </div>
    </div>
</body>
</html>
        """
        
        # E-posta ayarlarını al
        smtp_server = os.environ.get('MAIL_SERVER')
        smtp_port = int(os.environ.get('MAIL_PORT', 587))
        smtp_username = os.environ.get('MAIL_USERNAME')
        smtp_password = os.environ.get('MAIL_PASSWORD')
        sender_email = os.environ.get('MAIL_DEFAULT_SENDER')
        
        if not all([smtp_server, smtp_port, smtp_username, smtp_password, sender_email]):
            logging.error("E-posta ayarları eksik, admin bildirimi gönderilemedi.")
            return False
            
        logging.info(f"LED ekran bildirimi için e-posta hazırlanıyor: {subject}")
        
        # E-posta hazırla - tamamen UTF-8 destekli
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = ", ".join(admin_emails)
        
        # Düz metin içerik - UTF-8 ile kodla
        part1 = MIMEText(content.encode('utf-8'), 'plain', _charset='utf-8')
        msg.attach(part1)
        
        # HTML içerik - UTF-8 ile kodla
        part2 = MIMEText(html_content.encode('utf-8'), 'html', _charset='utf-8')
        msg.attach(part2)
        
        # E-posta gönder - BCC ekleyerek kopya al
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()  # EHLO ile başla
            server.starttls()
            server.ehlo()  # TLS sonrası yeniden EHLO
            server.login(smtp_username, smtp_password)
            
            # Mesajı kodla ve gönder
            server.sendmail(sender_email, admin_emails, msg.as_string())
            server.quit()
            
            logging.info(f"LED ekran bildirimi başarıyla gönderildi. Alıcılar: {admin_emails}")
            return True
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"LED ekran bildirimi gönderirken SMTP hatası: {error_msg}")
            
            # Alternatif yöntem dene - başlık kodlamasını değiştir
            if "codec can't encode" in error_msg:
                logging.info("Alternatif gönderim yöntemi deneniyor...")
                try:
                    # Base64 kodlamaya geç
                    charset.add_charset('utf-8', charset.SHORTEST, charset.BASE64, 'utf-8')
                    
                    # Yeni mesaj hazırla
                    new_msg = MIMEMultipart('alternative')
                    new_msg['Subject'] = Header(str(subject), 'utf-8').encode()
                    new_msg['From'] = sender_email
                    new_msg['To'] = ", ".join(admin_emails)
                    
                    # ASCII sürümünü hazırla - Türkçe karakterler kaldırılmış
                    ascii_content = content.encode('ascii', 'ignore').decode('ascii')
                    part1 = MIMEText(ascii_content, 'plain', 'ascii')
                    new_msg.attach(part1)
                    
                    # Base64 kodlanmış HTML içerik
                    encoded_html = base64.b64encode(html_content.encode('utf-8')).decode('ascii')
                    part2 = MIMEText(encoded_html, 'base64')
                    part2.add_header('Content-Type', 'text/html; charset=utf-8')
                    new_msg.attach(part2)
                    
                    # Yeniden gönder
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    server.starttls()
                    server.login(smtp_username, smtp_password)
                    server.sendmail(sender_email, admin_emails, new_msg.as_string())
                    server.quit()
                    
                    logging.info("Alternatif gönderim metodu başarılı!")
                    return True
                except Exception as e2:
                    logging.error(f"Alternatif gönderim metodunda da hata: {str(e2)}")
            
            return False
        
    except Exception as e:
        logging.error(f"Admin bildirim e-postası gönderilemedi: {str(e)}")
        return False 