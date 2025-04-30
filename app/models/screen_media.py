"""
Ekran-Medya ilişkisi modeli: Ekranlara atanmış medyaların ilişkilerini yönetir
"""
from datetime import datetime
from bson.objectid import ObjectId
from app import mongo

class ScreenMedia:
    """
    Ekran-Medya ilişkisini yöneten model sınıfı
    """
    
    # Statü değerleri
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    
    @classmethod
    def create(cls, screen_id, media_id, order=0, display_time=None, status=STATUS_ACTIVE):
        """Yeni bir ekran-medya ilişkisi oluştur"""
        screen_media_data = {
            "screen_id": screen_id,
            "media_id": media_id,
            "order": order,  # Sıralama için kullanılır
            "display_time": display_time,  # Medyanın bu ekranda gösterilme süresi (None ise varsayılan değer kullanılır)
            "status": status,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        # Aynı ekran ve medya ilişkisi varsa güncelle
        existing = mongo.db.screen_media.find_one({
            "screen_id": screen_id,
            "media_id": media_id
        })
        
        if existing:
            screen_media_data["_id"] = existing["_id"]
            mongo.db.screen_media.replace_one({"_id": existing["_id"]}, screen_media_data)
            return cls(**screen_media_data)
            
        # Yoksa yeni oluştur
        result = mongo.db.screen_media.insert_one(screen_media_data)
        screen_media_data['_id'] = result.inserted_id
        return cls(**screen_media_data)
    
    @classmethod
    def find_by_id(cls, screen_media_id):
        """ID'ye göre ekran-medya ilişkisi bul"""
        screen_media_data = mongo.db.screen_media.find_one({"_id": ObjectId(screen_media_id)})
        return cls(**screen_media_data) if screen_media_data else None
    
    @classmethod
    def find_by_screen(cls, screen_id):
        """Belirli bir ekrandaki tüm medyaları bul"""
        screen_media_list = []
        for screen_media_data in mongo.db.screen_media.find({"screen_id": screen_id}):
            screen_media_list.append(cls(**screen_media_data))
        return screen_media_list
    
    @classmethod
    def find_by_media(cls, media_id):
        """Belirli bir medyanın atandığı tüm ekranları bul"""
        screen_media_list = []
        for screen_media_data in mongo.db.screen_media.find({"media_id": media_id}):
            screen_media_list.append(cls(**screen_media_data))
        return screen_media_list
    
    @classmethod
    def find_by_screen_and_media(cls, screen_id, media_id):
        """Belirli bir ekran ve medya ilişkisini bul"""
        screen_media_data = mongo.db.screen_media.find_one({
            "screen_id": screen_id,
            "media_id": media_id
        })
        return cls(**screen_media_data) if screen_media_data else None
    
    @classmethod
    def remove_from_screen(cls, screen_id, media_id):
        """Belirli bir ekrandan medyayı kaldır"""
        mongo.db.screen_media.delete_one({
            "screen_id": screen_id,
            "media_id": media_id
        })
        return True
    
    @classmethod
    def clear_screen(cls, screen_id):
        """Bir ekrandaki tüm medyaları temizle"""
        mongo.db.screen_media.delete_many({"screen_id": screen_id})
        return True
    
    @classmethod
    def reorder_screen_media(cls, screen_id, media_order):
        """
        Ekrandaki medyaları yeniden sırala
        
        media_order: [{"media_id": "...", "order": 1}, ...]
        """
        for item in media_order:
            mongo.db.screen_media.update_one(
                {"screen_id": screen_id, "media_id": item["media_id"]},
                {"$set": {"order": item["order"], "updated_at": datetime.now()}}
            )
        return True
    
    def __init__(self, _id, screen_id, media_id, order=0, display_time=None, 
                 status=STATUS_ACTIVE, created_at=None, updated_at=None):
        """Yeni bir ekran-medya ilişkisi örneği başlat"""
        self.id = str(_id)
        self.screen_id = screen_id
        self.media_id = media_id
        self.order = order
        self.display_time = display_time
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
    
    def update(self, **kwargs):
        """Ekran-medya ilişkisini güncelle"""
        updates = {"updated_at": datetime.now()}
        
        # Güncellenebilir alanlar
        updatable_fields = ['order', 'display_time', 'status']
        
        for field in updatable_fields:
            if field in kwargs:
                updates[field] = kwargs[field]
        
        # Veritabanını güncelle
        mongo.db.screen_media.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": updates}
        )
        
        # Nesne bilgilerini güncelle
        for key, value in updates.items():
            setattr(self, key, value)
            
        return self
    
    def delete(self):
        """Ekran-medya ilişkisini sil"""
        mongo.db.screen_media.delete_one({"_id": ObjectId(self.id)})
        return True
    
    def to_dict(self):
        """Ekran-medya ilişkisini sözlük olarak döndür"""
        return {
            "id": self.id,
            "screen_id": self.screen_id,
            "media_id": self.media_id,
            "order": self.order,
            "display_time": self.display_time,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        } 