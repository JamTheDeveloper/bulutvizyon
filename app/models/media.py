"""
Medya Modeli: Görsel ve video içeriklerini yönetir
"""
import os
from datetime import datetime
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
from flask import current_app
from app import mongo
import uuid
from PIL import Image
import mimetypes
import urllib.parse

from app.models.logs import Log

class Media:
    """
    Medya dosyası modeli (resim, video)
    
    Alanlar:
    - id: Benzersiz ID
    - title: Medya başlığı
    - description: Açıklama
    - filename: Dosya adı
    - file_path: Dosya yolu
    - file_type: Dosya türü (image, video)
    - file_size: Dosya boyutu (byte)
    - width: Genişlik (piksel)
    - height: Yükseklik (piksel)
    - duration: Süre (video için, saniye)
    - display_time: Görüntülenme süresi (saniye)
    - category: Kategori
    - tags: Etiketler
    - orientation: Yönlendirme (horizontal, vertical)
    - status: Durum (active, inactive)
    - is_public: Kütüphanede paylaşımlı mı?
    - user_id: Yükleyen kullanıcı ID
    - created_at: Oluşturulma zamanı
    - updated_at: Güncellenme zamanı
    """
    
    # Medya tipleri
    TYPE_IMAGE = 'image'
    TYPE_VIDEO = 'video'
    TYPE_WEBPAGE = 'webpage'
    TYPE_CUSTOM = 'custom'
    
    # Medya durumları
    STATUS_ACTIVE = 'active'
    STATUS_PENDING = 'pending'
    STATUS_INACTIVE = 'inactive'
    STATUS_PROCESSING = 'processing'
    STATUS_DELETED = 'deleted'
    
    ORIENTATION_HORIZONTAL = 'horizontal'
    ORIENTATION_VERTICAL = 'vertical'
    
    # Log tipleri
    TYPE_MEDIA_CREATE = 'media_create'
    TYPE_MEDIA_UPDATE = 'media_update'
    TYPE_MEDIA_DELETE = 'media_delete'
    TYPE_MEDIA_APPROVE = 'media_approve'
    TYPE_MEDIA_REJECT = 'media_reject'
    
    @classmethod
    def create(cls, data, file=None):
        """
        Yeni medya oluştur
        """
        from bson import ObjectId
        
        # USER_ID doğru formatta olduğundan emin olalım
        user_id = data.get('user_id')
        if user_id:
            try:
                # String ise ObjectId'ye dönüştür
                if isinstance(user_id, str):
                    user_id = ObjectId(user_id)
                print(f"Media.create: user_id dönüştürüldü: {user_id}, tipi: {type(user_id)}")
            except Exception as e:
                print(f"Media.create: user_id dönüşüm hatası: {str(e)}")
        
        # Boş bir medya nesnesi oluştur
        media = {
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'category': data.get('category', ''),
            'tags': data.get('tags', []),
            'display_time': int(data.get('display_time', 10)),
            'status': data.get('status', cls.STATUS_ACTIVE),
            'is_public': bool(data.get('is_public', False)),
            'user_id': user_id,  # Dönüştürülmüş user_id kullan
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Dosya yüklendi mi?
        if file and file.filename:
            # Güvenli dosya adı oluştur
            original_filename = secure_filename(file.filename)
            file_ext = os.path.splitext(original_filename)[1].lower()
            
            # Benzersiz dosya adı
            new_filename = f"{uuid.uuid4().hex}{file_ext}"
            
            # Dosya türünü belirle
            mime_type = mimetypes.guess_type(original_filename)[0]
            if mime_type and mime_type.startswith('image/'):
                media['file_type'] = cls.TYPE_IMAGE
            elif mime_type and mime_type.startswith('video/'):
                media['file_type'] = cls.TYPE_VIDEO
            else:
                raise ValueError('Desteklenmeyen dosya türü')
            
            # Dosya yolunu belirle
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], new_filename)
            
            # Dosyayı kaydet
            file.save(file_path)
            
            # Dosya boyutunu kontrol et
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                # Dosya boyutu 0 ise dosyayı sil ve hata fırlat
                try:
                    os.remove(file_path)
                except:
                    pass
                raise ValueError('Dosya boyutu 0. Yükleme başarısız oldu.')
            
            # Dosya bilgilerini güncelle
            media['filename'] = new_filename
            media['file_path'] = file_path
            media['file_size'] = file_size
            
            # Resim ise boyutlarını al
            if media['file_type'] == cls.TYPE_IMAGE:
                try:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        media['width'] = width
                        media['height'] = height
                        
                        # Yönlendirmeyi belirle
                        if width > height:
                            media['orientation'] = cls.ORIENTATION_HORIZONTAL
                        else:
                            media['orientation'] = cls.ORIENTATION_VERTICAL
                except Exception as e:
                    # Resim işlenemezse dosyayı sil
                    os.remove(file_path)
                    raise ValueError(f"Resim işlenemedi: {str(e)}")
            
            # Video ise, daha sonra işlenecek (media_processor ile)
            elif media['file_type'] == cls.TYPE_VIDEO:
                # Varsayılan değerler
                media['width'] = 1920
                media['height'] = 1080
                media['duration'] = data.get('duration', 0)
                media['orientation'] = cls.ORIENTATION_HORIZONTAL
        
        # Veritabanına ekle
        result = mongo.db.media.insert_one(media)
        media['_id'] = result.inserted_id
        
        # Video işleme arka plan görevini başlat (ID'yi aldıktan sonra)
        if file and file.filename and media.get('file_type') == cls.TYPE_VIDEO:
            cls.process_video_async(media.get('file_path'), str(media['_id']))
        
        return media
    
    @classmethod
    def process_video_async(cls, file_path, media_id):
        """
        Video işleme fonksiyonu (async)
        """
        # Bu fonksiyon daha sonra geliştirilecek
        # Video boyutlarını, süresini ve yönlendirmesini alacak
        pass
    
    @classmethod
    def find_by_id(cls, media_id):
        """
        ID'ye göre medya bul
        """
        print(f"Media.find_by_id çağrıldı: {media_id}, tipi: {type(media_id)}")
        
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
                print(f"String'den ObjectId'ye dönüştürüldü: {media_id}")
            except Exception as e:
                print(f"ObjectId dönüşüm hatası: {str(e)}")
                return None
        
        result = mongo.db.media.find_one({'_id': media_id})
        print(f"Bulunan medya: {result}")
        return result
    
    @classmethod
    def find_by_user(cls, user_id, status=None, limit=20, skip=0, sort_by=None, sort_order=-1):
        """
        Kullanıcı ID'sine göre medya öğelerini bul.
        
        Bu fonksiyon üç tip medya döndürür:
        1. Kullanıcının yüklediği medya (user_id ile doğrudan eşleşme)
        2. Kullanıcı ile paylaşılan medya (media_shares koleksiyonu aracılığıyla)
        3. Herkese açık medya (is_public=True)
        
        Args:
            user_id: Kullanıcı ID'si
            status: Medya durumu (isteğe bağlı)
            limit: Döndürülecek maksimum kayıt sayısı
            skip: Atlanacak kayıt sayısı
            sort_by: Sıralama alanı
            sort_order: Sıralama düzeni (1: artan, -1: azalan)
        
        Returns:
            Medya öğelerinin listesi
        """
        from bson import ObjectId
        
        # user_id string ise ObjectId'ye dönüştür
        if isinstance(user_id, str):
            user_id = ObjectId(user_id)
        
        # Kullanıcının sahip olduğu medyayı bul
        query = {"user_id": user_id}
        
        # Duruma göre filtrele
        if status is not None:
            query["status"] = status
        
        # Kullanıcının kendi medyasını bul
        owned_media = list(mongo.db.media.find(query).skip(skip).limit(limit))
        
        # Kullanıcı ile paylaşılan medyayı bul (MediaShare tablosundan)
        shared_media_ids = [
            share["media_id"] for share in 
            mongo.db.media_shares.find({"user_id": user_id})
        ]
        
        # Paylaşılan medya ID'lerini ObjectId'ye dönüştür
        shared_media_object_ids = [
            ObjectId(media_id) if isinstance(media_id, str) else media_id 
            for media_id in shared_media_ids
        ]
        
        # Paylaşılan medyayı bul
        shared_media_query = {"_id": {"$in": shared_media_object_ids}}
        if status is not None:
            shared_media_query["status"] = status
            
        shared_media = list(mongo.db.media.find(shared_media_query))
        
        # Sonuçları birleştir (aynı medya hem sahip hem de paylaşılan olabilir)
        all_media = owned_media + shared_media
        
        # Aynı ID'ye sahip medya öğelerini kaldır
        seen_ids = set()
        unique_media = []
        
        for media in all_media:
            if str(media["_id"]) not in seen_ids:
                seen_ids.add(str(media["_id"]))
                unique_media.append(media)
        
        # Oluşturulma tarihine göre sırala
        unique_media.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)
        
        # Limit uygula
        return unique_media[skip:skip+limit]
    
    @classmethod
    def find_public(cls, limit=100, skip=0, category=None, search=None):
        """
        Herkese açık medyaları bul
        """
        query = {'is_public': True, 'status': cls.STATUS_ACTIVE}
        
        if category:
            query['category'] = category
        
        if search:
            query['$or'] = [
                {'title': {'$regex': search, '$options': 'i'}},
                {'description': {'$regex': search, '$options': 'i'}},
                {'tags': {'$in': [search]}}
            ]
        
        return list(mongo.db.media.find(query).sort('created_at', -1).skip(skip).limit(limit))
    
    @classmethod
    def find_all(cls, limit=100, skip=0, sort_by='created_at', sort_dir=-1):
        """
        Tüm medyaları getir
        """
        return list(mongo.db.media.find().sort(sort_by, sort_dir).skip(skip).limit(limit))
    
    @classmethod
    def find_pending(cls, limit=100, skip=0):
        """
        Onay bekleyen medyaları getir
        """
        query = {'status': cls.STATUS_PROCESSING}
        return list(mongo.db.media.find(query).sort('created_at', -1).skip(skip).limit(limit))
    
    @classmethod
    def update(cls, media_id, data=None, **kwargs):
        """
        Medya güncelle - hem sınıf metodu hem de nesne metodu olarak kullanılabilir
        
        Kullanım (nesne üzerinden): 
            media.update(status='active', title='Yeni başlık')
            
        Kullanım (sınıf üzerinden):
            Media.update(media_id, {'status': 'active', 'title': 'Yeni başlık'})
            
        veya
            Media.update(media_id, status='active', title='Yeni başlık')
        """
        # Eğer nesne üzerinden çağrıldıysa (self olarak)
        if not data and not kwargs and not isinstance(media_id, (str, ObjectId)):
            # self=media_id olarak gelmiş demektir, nesne metodu olarak kullanım
            return media_id._instance_update(**kwargs)
            
        # Sınıf metodu olarak kullanım
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
            except:
                return False
        
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        # data sözlük olarak geldi mi?
        if data and isinstance(data, dict):
            # Güncellenebilir alanları data'dan al
            updatable_fields = ['title', 'description', 'category', 'tags', 'display_time', 'status', 'is_public', 'approved_by', 'approved_at']
            for field in updatable_fields:
                if field in data:
                    update_data[field] = data[field]
        
        # kwargs doğrudan parametre olarak geldi mi?
        if kwargs:
            # Güncellenebilir alanları kwargs'tan al
            updatable_fields = ['title', 'description', 'category', 'tags', 'display_time', 'status', 'is_public', 'approved_by', 'approved_at']
            for field in updatable_fields:
                if field in kwargs:
                    update_data[field] = kwargs[field]
        
        result = mongo.db.media.update_one(
            {'_id': media_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    def _instance_update(self, **kwargs):
        """Nesne metodunun dahili implementasyonu"""
        updates = {"updated_at": datetime.now()}
        
        # Güncellenebilir alanlar
        updatable_fields = [
            'title', 'category', 'description', 'status', 
            'display_time', 'is_public', 'duration', 'approved_by', 'approved_at'
        ]
        
        for field in updatable_fields:
            if field in kwargs:
                updates[field] = kwargs[field]
        
        # Veritabanını güncelle
        mongo.db.media.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": updates}
        )
        
        # Nesne bilgilerini güncelle
        for key, value in updates.items():
            setattr(self, key, value)
            
        return self
    
    @classmethod
    def count_by_user(cls, user_id):
        """
        Kullanıcıya ait medya sayısını döndürür. 
        Bu metot, hem kullanıcının sahip olduğu hem de paylaşılan medyaları sayar.
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Medya sayısı
        """
        from bson import ObjectId
        
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
        except:
            return 0
            
        # Kullanıcının sahip olduğu medya sayısı
        owned_count = mongo.db.media.count_documents({"user_id": user_id})
        
        # Kullanıcı ile paylaşılan medya ID'leri
        shared_media_ids = [
            share["media_id"] for share in 
            mongo.db.media_shares.find({"user_id": user_id})
        ]
        
        # Eğer paylaşılan medya yoksa, sadece sahip olunan medya sayısını döndür
        if not shared_media_ids:
            return owned_count
            
        # Paylaşılan medya sayısı
        shared_count = mongo.db.media.count_documents({
            "_id": {"$in": shared_media_ids},
            "user_id": {"$ne": user_id}  # Zaten sahip olunan medyaları saymamak için
        })
        
        return owned_count + shared_count
    
    @classmethod
    def count_public(cls, category=None):
        """
        Kütüphanedeki medya sayısını döndür
        """
        query = {'is_public': True, 'status': cls.STATUS_ACTIVE}
        
        if category:
            query['category'] = category
            
        return mongo.db.media.count_documents(query)
    
    @classmethod
    def increment_views(cls, media_ids):
        """
        Birden çok medyanın görüntülenme sayısını artırır.
        Bu metot, bulk operasyon kullanarak veritabanında toplu güncelleme yapar.
        
        Args:
            media_ids: Medya ID'lerinin listesi (str veya ObjectId)
            
        Returns:
            Güncellenen medya sayısı
        """
        if not media_ids:
            return 0
            
        # String ID'leri ObjectId'ye dönüştür
        object_ids = []
        for media_id in media_ids:
            if isinstance(media_id, str):
                try:
                    object_ids.append(ObjectId(media_id))
                except:
                    pass  # Geçersiz ID'leri atla
            elif isinstance(media_id, ObjectId):
                object_ids.append(media_id)
        
        if not object_ids:
            return 0
            
        # Toplu güncelleme - $inc operatörü ile views alanını 1 artır
        result = mongo.db.media.update_many(
            {'_id': {'$in': object_ids}},
            {'$inc': {'views': 1}}
        )
        
        return result.modified_count
    
    def __init__(self, _id, user_id, title, filename, file_type, file_size, 
                 status='active', category=None, description=None, duration=None, 
                 display_time=10, is_public=False, views=0,
                 created_at=None, updated_at=None, **kwargs):
        """Yeni bir medya örneği başlat"""
        self.id = str(_id)
        self.user_id = user_id
        self.title = title
        self.filename = filename
        self.file_type = file_type
        self.file_size = file_size
        self.category = category
        self.description = description
        self.status = status
        self.duration = duration
        self.display_time = display_time
        self.is_public = is_public
        self.views = views
        self.created_at = created_at
        self.updated_at = updated_at
    
    def increment_view(self):
        """Görüntülenme sayısını artır"""
        mongo.db.media.update_one(
            {"_id": ObjectId(self.id)}, 
            {"$inc": {"views": 1}}
        )
        self.views += 1
        return self.views
    
    def get_file_url(self):
        """Medya dosyasının URL'ini oluştur"""
        return f"/uploads/{self.filename}"
    
    def is_image(self):
        """Medyanın resim olup olmadığını kontrol et"""
        return self.file_type == self.TYPE_IMAGE
    
    def is_video(self):
        """Medyanın video olup olmadığını kontrol et"""
        return self.file_type == self.TYPE_VIDEO
    
    def to_dict(self):
        """Medya bilgilerini sözlük olarak döndür"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "category": self.category,
            "description": self.description,
            "status": self.status,
            "duration": self.duration,
            "display_time": self.display_time,
            "is_public": self.is_public,
            "views": self.views,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "file_url": self.get_file_url()
        }

    @classmethod
    def delete(cls, media_id):
        """
        Medya sil (sınıf metodu)
        
        Args:
            media_id: Silinecek medyanın ID'si
            
        Returns:
            Başarılıysa True, değilse False
        """
        print(f"DEBUG: Media.delete çağrıldı. media_id: {media_id}, tipi: {type(media_id)}")
        
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
                print(f"DEBUG: media_id ObjectId'ye dönüştürüldü: {media_id}")
            except Exception as e:
                print(f"DEBUG: ObjectId dönüşüm hatası: {str(e)}")
                return False
        
        # Medya bilgilerini al
        media = cls.find_by_id(media_id)
        if not media:
            print(f"DEBUG: Silinecek medya bulunamadı: {media_id}")
            return False
        
        print(f"DEBUG: Silinecek medya bulundu: {media.get('_id')}, durum: {media.get('status')}")
        
        # MediaShare koleksiyonundan paylaşımları temizle
        try:
            MediaShare.delete_medias_from_shares(media_id)
            print(f"DEBUG: MediaShare kayıtları temizlendi")
        except Exception as e:
            print(f"DEBUG: MediaShare temizleme hatası: {str(e)}")
        
        # Dosyayı diskten sil
        try:
            filename = media.get('filename')
            if filename:
                # Tüm olası dosya yollarını kontrol edelim
                possible_paths = [
                    os.path.join(current_app.config.get('UPLOAD_FOLDER', ''), filename),
                    os.path.join('app', 'static', 'uploads', filename),
                    os.path.join('static', 'uploads', filename),
                    os.path.join('/root/bulutvizyonServer/app/static/uploads', filename),
                    media.get('file_path')  # Doğrudan veritabanında saklanan tam yol
                ]
                
                file_deleted = False
                for file_path in possible_paths:
                    if file_path and os.path.exists(file_path):
                        print(f"DEBUG: Dosya bulundu ve siliniyor: {file_path}")
                        os.remove(file_path)
                        print(f"DEBUG: Dosya diskten silindi: {file_path}")
                        file_deleted = True
                        break
                
                if not file_deleted:
                    print(f"DEBUG: Hiçbir konumda dosya bulunamadı. Denenen yollar: {possible_paths}")
            else:
                print(f"DEBUG: Dosya adı bulunamadı")
        except Exception as e:
            print(f"DEBUG: Dosya silme hatası: {str(e)}")
        
        # Veritabanından sil
        try:
            result = mongo.db.media.delete_one({'_id': media_id})
            deleted_count = result.deleted_count
            print(f"DEBUG: Veritabanından silme sonucu: {deleted_count} kayıt silindi")
            return deleted_count > 0
        except Exception as e:
            print(f"DEBUG: Veritabanı silme hatası: {str(e)}")
            return False

# Medya paylaşımları için yeni bir koleksiyon oluşturalım
class MediaShare:
    """
    Medya paylaşımlarını takip eden sınıf. 
    Bu sınıf, hangi medya öğesinin hangi kullanıcıya atandığını izler.
    """
    
    @classmethod
    def create(cls, media_id, user_id, assigned_by=None):
        """
        Medya paylaşımı oluştur.
        
        Args:
            media_id: Medya ID'si
            user_id: Kullanıcı ID'si
            assigned_by: Paylaşımı yapan kullanıcı ID'si (isteğe bağlı)
            
        Returns:
            Oluşturulan paylaşım belgesi veya None
        """
        from bson import ObjectId
        from datetime import datetime
        
        # ID'leri kontrol et
        try:
            if isinstance(media_id, str):
                media_id = ObjectId(media_id)
            
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
                
            if assigned_by and isinstance(assigned_by, str):
                assigned_by = ObjectId(assigned_by)
        except:
            return None
        
        # Medya ve kullanıcının varlığını kontrol et
        media = mongo.db.media.find_one({"_id": media_id})
        user = mongo.db.users.find_one({"_id": user_id})
        
        if not media or not user:
            return None
        
        # Mevcut paylaşımı kontrol et
        existing = mongo.db.media_shares.find_one({
            "media_id": media_id,
            "user_id": user_id
        })
        
        # Mevcut bir paylaşım varsa güncelle
        if existing:
            return mongo.db.media_shares.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "updated_at": datetime.utcnow(),
                    "assigned_by": assigned_by if assigned_by else existing.get("assigned_by")
                }}
            )
        
        # Yeni paylaşım oluştur
        share_data = {
            "media_id": media_id,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if assigned_by:
            share_data["assigned_by"] = assigned_by
            
        result = mongo.db.media_shares.insert_one(share_data)
        if result.inserted_id:
            return mongo.db.media_shares.find_one({"_id": result.inserted_id})
        return None
    
    @classmethod
    def remove(cls, media_id, user_id):
        """
        Medya paylaşımını kaldır.
        
        Args:
            media_id: Medya ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Başarılı ise True, değilse False
        """
        from bson import ObjectId
        
        try:
            if isinstance(media_id, str):
                media_id = ObjectId(media_id)
            
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
        except:
            return False
        
        result = mongo.db.media_shares.delete_one({
            "media_id": media_id,
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    @classmethod
    def find_by_media(cls, media_id):
        """
        Medya ID'sine göre paylaşımları bul.
        
        Args:
            media_id: Medya ID'si
            
        Returns:
            Bu medya ile ilişkili kullanıcıların listesi
        """
        from bson import ObjectId
        
        try:
            if isinstance(media_id, str):
                media_id = ObjectId(media_id)
        except:
            return []
        
        # Medya ID'sine göre paylaşımları bul
        shares = mongo.db.media_shares.find({"media_id": media_id})
        
        # Kullanıcı ID'lerini al
        user_ids = [share["user_id"] for share in shares]
        
        # Kullanıcıları bul
        users = []
        for user_id in user_ids:
            user = mongo.db.users.find_one({"_id": user_id})
            if user:
                users.append(user)
                
        return users
    
    @classmethod
    def find_by_user(cls, user_id):
        """
        Kullanıcı ID'sine göre paylaşımları bul.
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            Bu kullanıcı ile paylaşılan medya öğelerinin listesi
        """
        from bson import ObjectId
        
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
        except:
            return []
        
        # Kullanıcı ID'sine göre paylaşımları bul
        shares = mongo.db.media_shares.find({"user_id": user_id})
        
        # Medya ID'lerini al
        media_ids = [share["media_id"] for share in shares]
        
        # Medya öğelerini bul
        media_list = []
        for media_id in media_ids:
            media = mongo.db.media.find_one({"_id": media_id})
            if media:
                media_list.append(media)
                
        return media_list
    
    @classmethod
    def media_is_shared_with_user(cls, media_id, user_id):
        """
        Bir medya öğesinin belirli bir kullanıcı ile paylaşılıp paylaşılmadığını kontrol et.
        
        Args:
            media_id: Medya ID'si
            user_id: Kullanıcı ID'si
            
        Returns:
            Paylaşılmışsa True, değilse False
        """
        from bson import ObjectId
        
        try:
            if isinstance(media_id, str):
                media_id = ObjectId(media_id)
            
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
        except:
            return False
        
        share = mongo.db.media_shares.find_one({
            "media_id": media_id,
            "user_id": user_id
        })
        
        return share is not None

    @classmethod
    def delete_medias_from_shares(cls, media_id):
        """
        MediaShare koleksiyonundan medya paylaşımlarını kaldır
        """
        from bson import ObjectId
        
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
            except:
                return False
        
        # MediaShare kayıtlarını sil
        result = mongo.db.media_shares.delete_many({"media_id": media_id})
        return result.deleted_count > 0 