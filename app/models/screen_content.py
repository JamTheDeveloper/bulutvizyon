"""
Ekran İçerik Modeli: Ekranlarda gösterilen medya içeriklerini yönetir
"""
from datetime import datetime
from bson import ObjectId
from app import mongo

class ScreenContent:
    """
    Ekran içeriği modeli
    
    Alanlar:
    - id: Benzersiz ID
    - screen_id: Ekran ID
    - media_id: Medya ID
    - display_time: Görüntülenme süresi (saniye)
    - order: Sıralama
    - status: Durum (active, inactive)
    - created_at: Oluşturulma zamanı
    - updated_at: Güncellenme zamanı
    """
    
    # Sabitler
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    
    @classmethod
    def create(cls, data):
        """
        Yeni ekran içeriği oluştur
        """
        # İçerik nesnesi
        content = {
            'screen_id': data.get('screen_id'),
            'media_id': data.get('media_id'),
            'display_time': int(data.get('display_time', 10)),
            'order': int(data.get('order', 0)),
            'status': data.get('status', cls.STATUS_ACTIVE),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Veritabanına ekle
        result = mongo.db.screen_contents.insert_one(content)
        content['_id'] = result.inserted_id
        
        return content
    
    @classmethod
    def find_by_id(cls, content_id):
        """
        ID'ye göre içerik bul
        """
        if isinstance(content_id, str):
            try:
                content_id = ObjectId(content_id)
            except:
                return None
        
        return mongo.db.screen_contents.find_one({'_id': content_id})
    
    @classmethod
    def find_by_screen_id(cls, screen_id):
        """
        Ekran ID'sine göre içerikleri bul
        """
        print(f"DEBUG - find_by_screen_id metodu çağrıldı: {screen_id}, tip: {type(screen_id)}")
        
        # Farklı format olasılıklarını göz önünde bulunduralım
        query_conditions = []
        
        # String ID durumu
        if isinstance(screen_id, str):
            query_conditions.append({'screen_id': screen_id})
            
            # ObjectId dönüşümü yapabilirsek bu formatı da ekleyelim
            try:
                obj_id = ObjectId(screen_id)
                query_conditions.append({'screen_id': obj_id})
            except:
                pass
        
        # Halihazırda ObjectId ise 
        elif isinstance(screen_id, ObjectId):
            query_conditions.append({'screen_id': screen_id})
            query_conditions.append({'screen_id': str(screen_id)})
        
        # Diğer durumlar için orijinal ID'yi kullan
        else:
            query_conditions.append({'screen_id': screen_id})
        
        # Her durum için OR sorgusu oluştur
        query = {
            '$or': query_conditions,
            'status': cls.STATUS_ACTIVE
        }
        
        print(f"DEBUG - screen_contents sorgusu: {query}")
        
        # Tüm olası eşleşmeleri getir
        result = list(mongo.db.screen_contents.find(query).sort('order', 1))
        print(f"DEBUG - Bulunan içerikler: {len(result)}")
        
        return result
    
    @classmethod
    def update(cls, content_id, data):
        """
        İçerik güncelle
        """
        if isinstance(content_id, str):
            try:
                content_id = ObjectId(content_id)
            except:
                return False
        
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        # Güncellenebilir alanlar
        for field in ['display_time', 'order', 'status']:
            if field in data:
                update_data[field] = data[field]
        
        result = mongo.db.screen_contents.update_one(
            {'_id': content_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    @classmethod
    def delete(cls, content_id):
        """
        İçerik sil
        """
        if isinstance(content_id, str):
            try:
                content_id = ObjectId(content_id)
            except:
                return False
        
        result = mongo.db.screen_contents.delete_one({'_id': content_id})
        
        return result.deleted_count > 0
    
    @classmethod
    def delete_by_screen(cls, screen_id):
        """
        Ekrana ait tüm içerikleri sil
        """
        print(f"DEBUG - ScreenContent.delete_by_screen çağrıldı: screen_id={screen_id}, tip={type(screen_id)}")
        
        # ObjectId formatına çevirme
        if isinstance(screen_id, str):
            try:
                obj_id = ObjectId(screen_id)
            except:
                obj_id = None
                print(f"DEBUG - screen_id ObjectId'ye çevrilemedi: {screen_id}")
        else:
            obj_id = screen_id
        
        # Her iki format için de sorgu yap 
        query = {
            '$or': [
                {'screen_id': screen_id},  # String format
                {'screen_id': obj_id}  # ObjectId format (eğer çevrilebildiyse)
            ]
        }
        
        print(f"DEBUG - Silinecek içerikler için sorgu: {query}")
        
        # Silinecek kayıtları göster
        matching_records = list(mongo.db.screen_contents.find(query))
        print(f"DEBUG - Eşleşen içerik sayısı: {len(matching_records)}")
        for record in matching_records:
            print(f"DEBUG - Silinecek içerik: {record.get('_id')}, media_id: {record.get('media_id')}")
        
        # Silme işlemi
        result = mongo.db.screen_contents.delete_many(query)
        deleted_count = result.deleted_count
        print(f"DEBUG - Silinen içerik sayısı: {deleted_count}")
        
        return deleted_count
    
    @classmethod
    def count_by_screen(cls, screen_id):
        """
        Ekrana ait içerik sayısını döndür
        """
        if isinstance(screen_id, str):
            try:
                screen_id = ObjectId(screen_id)
            except:
                return 0
        
        return mongo.db.screen_contents.count_documents({'screen_id': screen_id})
    
    @classmethod
    def count_by_media_id(cls, media_id):
        """
        Belirli bir medyanın kaç ekranda kullanıldığını sayar
        
        Args:
            media_id: Medya ID
            
        Returns:
            Medyanın kullanıldığı ekran içeriği sayısı
        """
        # String ID'leri ObjectId'ye çevirme girişimi
        media_id_str = media_id
        if isinstance(media_id, str):
            try:
                media_id_obj = ObjectId(media_id)
            except:
                media_id_obj = None
        else:
            media_id_obj = media_id
            media_id_str = str(media_id)
            
        # Her iki format için sorgu oluştur
        query = {
            '$or': [
                {'media_id': media_id_str},  # String format
                {'media_id': media_id_obj}   # ObjectId format
            ],
            'status': cls.STATUS_ACTIVE
        }
        
        # Sadece aktif içerikleri say
        return mongo.db.screen_contents.count_documents(query)
    
    def __init__(self, _id, screen_id, media_id, order=1, display_time=None, 
                 created_at=None, updated_at=None, **kwargs):
        """Yeni bir içerik örneği başlat"""
        self.id = str(_id)
        self.screen_id = screen_id
        self.media_id = media_id
        self.order = order
        self.display_time = display_time
        self.created_at = created_at
        self.updated_at = updated_at
        self.media = None  # Medya nesnesi sonradan yüklenebilir
    
    def update(self, **kwargs):
        """İçerik bilgilerini güncelle"""
        updates = {"updated_at": datetime.now()}
        
        # Güncellenebilir alanlar
        updatable_fields = ['display_time', 'order']
        
        for field in updatable_fields:
            if field in kwargs:
                updates[field] = kwargs[field]
        
        # Veritabanını güncelle
        mongo.db.screen_contents.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": updates}
        )
        
        # Nesne bilgilerini güncelle
        for key, value in updates.items():
            setattr(self, key, value)
            
        return self
    
    def delete(self):
        """İçeriği sil"""
        result = mongo.db.screen_contents.delete_one({"_id": ObjectId(self.id)})
        return result.deleted_count > 0
    
    def get_media(self):
        """İçeriğe ait medya bilgilerini getir"""
        if not self.media:
            self.media = mongo.db.media.find_one({"_id": ObjectId(self.media_id)})
        return self.media
    
    def to_dict(self):
        """İçerik bilgilerini sözlük olarak döndür"""
        return {
            "id": self.id,
            "screen_id": self.screen_id,
            "media_id": self.media_id,
            "order": self.order,
            "display_time": self.display_time,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "media": self.media
        } 