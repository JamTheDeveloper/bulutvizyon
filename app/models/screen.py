"""
Ekran Modeli: Dijital ekran bilgilerini ve ilişkilerini yönetir
"""
import random
import string
from datetime import datetime
from bson.objectid import ObjectId
from flask import current_app
from app import mongo
import uuid
import os
from pymongo import MongoClient
from urllib.parse import quote_plus

class Screen:
    """
    Ekran modeli
    
    Alanlar:
    - id: Benzersiz ID
    - name: Ekran adı
    - description: Açıklama
    - api_key: API anahtarı
    - orientation: Yönlendirme (horizontal, vertical)
    - resolution: Çözünürlük (örn. 1920x1080)
    - location: Konum
    - status: Durum (active, inactive)
    - user_id: Sahip kullanıcı ID
    - organization_id: Organizasyon ID (isteğe bağlı)
    - refresh_rate: Yenileme sıklığı (saniye)
    - show_clock: Saat gösterimi
    - last_active: Son aktivite zamanı
    - created_at: Oluşturulma zamanı
    - updated_at: Güncellenme zamanı
    - offline_periods: Offline kalma dönemleri
    - playlist_id: Playlist ID
    """
    
    # Status değerleri
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    
    ORIENTATION_HORIZONTAL = 'horizontal'
    ORIENTATION_VERTICAL = 'vertical'
    
    @classmethod
    def create(cls, data):
        """
        Yeni ekran oluştur
        """
        # API anahtarı oluştur
        api_key = cls.generate_api_key()
        
        # Ekran nesnesi
        screen = {
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'api_key': api_key,
            'orientation': data.get('orientation', cls.ORIENTATION_HORIZONTAL),
            'resolution': data.get('resolution', '1920x1080'),
            'location': data.get('location', ''),
            'status': data.get('status', cls.STATUS_ACTIVE),
            'user_id': data.get('user_id'),
            'organization_id': data.get('organization_id'),
            'refresh_rate': int(data.get('refresh_rate', 15)),
            'show_clock': bool(data.get('show_clock', True)),
            'last_active': None,
            'offline_periods': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Veritabanına ekle
        result = mongo.db.screens.insert_one(screen)
        screen['_id'] = result.inserted_id
        
        return screen
    
    @classmethod
    def find_by_id(cls, screen_id):
        """
        ID'ye göre ekran bul
        """
        if isinstance(screen_id, str):
            try:
                screen_id = ObjectId(screen_id)
            except:
                return None
        
        screen_data = mongo.db.screens.find_one({'_id': screen_id})
        
        if not screen_data:
            return None
        
        # MongoDB belgesini Screen nesnesine dönüştür
        return cls(**screen_data)
    
    @classmethod
    def find_by_api_key(cls, api_key):
        """
        API anahtarına göre ekran bul
        """
        screen_data = mongo.db.screens.find_one({'api_key': api_key})
        
        if not screen_data:
            return None
        
        # MongoDB belgesini Screen nesnesine dönüştür
        return cls(**screen_data)
    
    @classmethod
    def find_by_user(cls, user_id, limit=100, skip=0, status=None):
        """
        Kullanıcı ID'sine göre ekranları bul
        """
        try:
            # MongoDB bağlantısını doğrudan oluştur - Flask-PyMongo yerine
            try:
                # user_id'yi doğru şekilde dönüştür
                if isinstance(user_id, str):
                    try:
                        user_id_obj = ObjectId(user_id)
                    except Exception as e:
                        print(f"ObjectId dönüşüm hatası: {str(e)}")
                        user_id_obj = user_id
                else:
                    user_id_obj = user_id
                
                # İki şekilde de sorgula (String veya ObjectId)
                query = {'$or': [{'user_id': user_id}, {'user_id': user_id_obj}]}
                
                if status:
                    query['status'] = status
                
                screen_list = []
                for screen_data in mongo.db.screens.find(query).sort('created_at', -1).skip(skip).limit(limit):
                    screen_list.append(cls(**screen_data))
                
                print(f"Kullanıcıya ait {len(screen_list)} ekran bulundu - user_id: {user_id}")
                return screen_list
            except Exception as e:
                print(f"MongoDB işlemleri hatası: {str(e)}")
                return []
                
        except Exception as e:
            print(f"Ekranlar getirilirken hata: {str(e)}")
            return []
    
    @classmethod
    def find_all(cls, limit=100, skip=0, sort_by='created_at', sort_dir=-1):
        """
        Tüm ekranları getir
        """
        screen_list = []
        for screen_data in mongo.db.screens.find().sort(sort_by, sort_dir).skip(skip).limit(limit):
            screen_list.append(cls(**screen_data))
        
        return screen_list
    
    @classmethod
    def update(cls, screen_id, data):
        """
        Ekran güncelle
        """
        if isinstance(screen_id, str):
            try:
                screen_id = ObjectId(screen_id)
            except:
                return False
        
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        # Güncellenebilir alanlar
        for field in ['name', 'description', 'orientation', 'resolution', 
                     'location', 'status', 'refresh_rate', 'show_clock', 'last_active']:
            if field in data:
                update_data[field] = data[field]
        
        result = mongo.db.screens.update_one(
            {'_id': screen_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    @classmethod
    def delete(cls, screen_id):
        """
        Ekran sil
        """
        if isinstance(screen_id, str):
            try:
                obj_id = ObjectId(screen_id)
            except:
                return False
        else:
            obj_id = screen_id
        
        # İlişkili içerikleri sil
        from app.models.screen_content import ScreenContent
        ScreenContent.delete_by_screen(screen_id)
        
        # Ekranı sil
        result = mongo.db.screens.delete_one({'_id': obj_id})
        
        return result.deleted_count > 0
    
    @classmethod
    def count_by_user(cls, user_id, status=None):
        """
        Kullanıcının ekran sayısını döndür
        """
        try:
            # user_id'yi doğru şekilde dönüştür
            if isinstance(user_id, str):
                try:
                    user_id_obj = ObjectId(user_id)
                except Exception as e:
                    print(f"ObjectId dönüşüm hatası: {str(e)}")
                    user_id_obj = user_id
            else:
                user_id_obj = user_id
            
            # İki şekilde de sorgula (String veya ObjectId)
            query = {'$or': [{'user_id': user_id}, {'user_id': user_id_obj}]}
            
            if status:
                query['status'] = status
            
            count = mongo.db.screens.count_documents(query)
            print(f"Kullanıcıya ait ekran sayısı: {count} - user_id: {user_id}")
            return count
        except Exception as e:
            print(f"Ekran sayısı sayılırken hata: {str(e)}")
            return 0
    
    @staticmethod
    def generate_api_key(length=32):
        """
        Benzersiz API anahtarı oluştur
        """
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    def __init__(self, _id, user_id, name, orientation, resolution, api_key, 
                 status='active', location=None, description=None, refresh_rate=15, 
                 show_clock=True, preview_image=None, created_at=None, 
                 updated_at=None, last_active=None, offline_periods=None, playlist_id=None, **kwargs):
        """Yeni bir ekran örneği başlat"""
        self.id = str(_id)
        self.user_id = user_id
        self.name = name
        self.orientation = orientation
        self.resolution = resolution
        self.location = location
        self.description = description
        self.status = status
        self.refresh_rate = refresh_rate
        self.show_clock = show_clock
        self.api_key = api_key
        self.preview_image = preview_image
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_active = last_active
        self.offline_periods = offline_periods if offline_periods else []
        self.playlist_id = playlist_id
    
    def update(self, **kwargs):
        """Ekran bilgilerini güncelle"""
        updates = {"updated_at": datetime.now()}
        
        # Güncellenebilir alanlar
        updatable_fields = [
            'name', 'orientation', 'resolution', 'location', 
            'description', 'status', 'refresh_rate', 'show_clock'
        ]
        
        for field in updatable_fields:
            if field in kwargs:
                updates[field] = kwargs[field]
        
        # Özel alanlar
        if 'preview_image' in kwargs:
            updates['preview_image'] = kwargs['preview_image']
            
        if 'last_active' in kwargs:
            updates['last_active'] = kwargs['last_active']
        
        # Veritabanını güncelle
        mongo.db.screens.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": updates}
        )
        
        # Nesne bilgilerini güncelle
        for key, value in updates.items():
            setattr(self, key, value)
            
        return self
    
    def delete(self):
        """Ekranı ve ilişkili içerikleri sil"""
        # Önce ilişkili ekran içeriklerini sil
        from app.models.screen_content import ScreenContent
        ScreenContent.delete_by_screen(self.id)
        
        # Sonra ekranı sil
        mongo.db.screens.delete_one({"_id": ObjectId(self.id)})
        
        return True
    
    def get_contents(self):
        """Ekranın içeriklerini getir"""
        from app.models.screen_content import ScreenContent
        return ScreenContent.find_by_screen(self.id)
    
    def update_last_active(self):
        """Son aktif zamanını güncelle"""
        return self.update(last_active=datetime.now())
    
    def to_dict(self):
        """Ekran bilgilerini sözlük olarak döndür"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "orientation": self.orientation,
            "resolution": self.resolution,
            "location": self.location,
            "description": self.description,
            "status": self.status,
            "refresh_rate": self.refresh_rate,
            "show_clock": self.show_clock,
            "api_key": self.api_key,
            "preview_image": self.preview_image,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_active": self.last_active,
            "offline_periods": self.offline_periods,
            "playlist_id": self.playlist_id
        }
    
    def add_offline_period(self, offline_period):
        """
        Ekrana offline kalma dönemi ekle
        """
        if not hasattr(self, 'offline_periods') or self.offline_periods is None:
            self.offline_periods = []
            
        self.offline_periods.append(offline_period)
        
        # Veritabanını güncelle
        mongo.db.screens.update_one(
            {"_id": ObjectId(self.id)},
            {"$push": {"offline_periods": offline_period}}
        )
        
        return True 