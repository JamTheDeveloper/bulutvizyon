import os
import time
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import datetime
from flask import current_app
from app.models.user import User
from app.models.screen import Screen
from app.models.media import Media

def allowed_file(filename, allowed_extensions):
    """
    Dosya uzantısının izin verilen uzantılarda olup olmadığını kontrol eder
    
    Args:
        filename: Dosya adı
        allowed_extensions: İzin verilen uzantılar listesi
        
    Returns:
        bool: Dosya uzantısı uygunsa True, değilse False
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_file(file, upload_folder, subfolder=None):
    """
    Dosyayı kaydeder ve benzersiz dosya adını döndürür
    
    Args:
        file: Dosya nesnesi
        upload_folder: Yükleme klasörü
        subfolder: Alt klasör (varsa)
        
    Returns:
        tuple: (Benzersiz dosya adı, Dosya yolu)
    """
    filename = secure_filename(file.filename)
    basename, ext = os.path.splitext(filename)
    unique_filename = f"{basename}_{uuid.uuid4().hex}{ext}"
    
    save_path = upload_folder
    if subfolder:
        save_path = os.path.join(save_path, subfolder)
        os.makedirs(save_path, exist_ok=True)
    
    file_path = os.path.join(save_path, unique_filename)
    file.save(file_path)
    
    return unique_filename, file_path

def get_image_dimensions(file_path):
    """
    Resim boyutlarını alır
    
    Args:
        file_path: Resim dosya yolu
        
    Returns:
        tuple: (genişlik, yükseklik) veya hata durumunda None
    """
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception as e:
        current_app.logger.error(f"Resim boyutları alınırken hata: {str(e)}")
        return None

def format_datetime(dt, format="%d.%m.%Y %H:%M"):
    """
    Datetime nesnesini belirli bir formatta string'e dönüştürür
    
    Args:
        dt: Datetime nesnesi
        format: Çıktı formatı
        
    Returns:
        str: Formatlanmış datetime string'i
    """
    if dt:
        return dt.strftime(format)
    return ""

def format_file_size(size_bytes):
    """
    Bayt cinsinden dosya boyutunu okunabilir formata dönüştürür
    
    Args:
        size_bytes: Bayt cinsinden dosya boyutu
        
    Returns:
        str: Okunabilir dosya boyutu
    """
    if size_bytes == 0:
        return "0B"
    
    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
        
    return f"{size_bytes:.2f} {size_names[i]}"

def get_screen_summary(screen_id):
    """
    Ekran özeti bilgilerini getirir
    
    Args:
        screen_id: Ekran ID'si
        
    Returns:
        dict: Ekran özet bilgileri
    """
    screen = Screen.find_by_id(screen_id)
    if not screen:
        return None
    
    # TODO: Ekrana atanmış medya sayısını getir
    media_count = 0
    
    # Ekranın son aktif zamanından bu yana geçen süre
    last_active_ago = None
    if screen.last_active:
        delta = datetime.datetime.utcnow() - screen.last_active
        if delta.days > 0:
            last_active_ago = f"{delta.days} gün önce"
        elif delta.seconds > 3600:
            last_active_ago = f"{delta.seconds // 3600} saat önce"
        elif delta.seconds > 60:
            last_active_ago = f"{delta.seconds // 60} dakika önce"
        else:
            last_active_ago = f"{delta.seconds} saniye önce"
    
    return {
        "id": screen.id,
        "name": screen.name,
        "status": screen.status,
        "orientation": screen.orientation,
        "resolution": f"{screen.width}x{screen.height}",
        "media_count": media_count,
        "last_active_ago": last_active_ago,
        "is_active": screen.is_active()
    }

def get_media_summary(media_id):
    """
    Medya özeti bilgilerini getirir
    
    Args:
        media_id: Medya ID'si
        
    Returns:
        dict: Medya özet bilgileri
    """
    media = Media.find_by_id(media_id)
    if not media:
        return None
    
    user = User.find_by_id(media.user_id)
    username = user.username if user else "Bilinmeyen Kullanıcı"
    
    # TODO: Bu medyanın atandığı ekran sayısını getir
    assigned_screen_count = 0
    
    return {
        "id": media.id,
        "title": media.title,
        "type": media.file_type,
        "orientation": media.orientation,
        "resolution": f"{media.width}x{media.height}" if media.width and media.height else "Bilinmiyor",
        "status": media.status,
        "username": username,
        "file_size": format_file_size(media.file_size) if media.file_size else "Bilinmiyor",
        "created_at": format_datetime(media.created_at),
        "assigned_screen_count": assigned_screen_count,
        "is_active": media.is_active(),
        "is_pending": media.is_pending(),
        "category": media.category or "Kategori Yok",
        "public": "Evet" if media.public else "Hayır"
    } 