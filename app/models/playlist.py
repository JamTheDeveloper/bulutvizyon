"""
Playlist Modeli: Kullanıcıların ekranlara atamak için hazırladığı medya oynatma listelerini yönetir
"""
from datetime import datetime
from bson.objectid import ObjectId
from app import mongo

class Playlist:
    """
    Playlist modeli
    
    Alanlar:
    - id: Benzersiz ID
    - name: Playlist adı
    - description: Açıklama
    - user_id: Sahip kullanıcı ID
    - is_public: Kütüphanede paylaşılıp paylaşılmadığı
    - status: Durum (active, inactive)
    - created_at: Oluşturulma zamanı
    - updated_at: Güncellenme zamanı
    - media_count: Playlist içindeki medya sayısı (otomatik hesaplanır)
    """
    
    # Statü değerleri
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    
    @classmethod
    def create(cls, data):
        """
        Yeni playlist oluştur
        """
        playlist = {
            'name': data.get('name', ''),
            'description': data.get('description', ''),
            'user_id': data.get('user_id'),
            'is_public': bool(data.get('is_public', False)),
            'status': data.get('status', cls.STATUS_ACTIVE),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'media_count': 0
        }
        
        # Veritabanına ekle
        result = mongo.db.playlists.insert_one(playlist)
        playlist['_id'] = result.inserted_id
        
        return playlist
    
    @classmethod
    def find_by_id(cls, playlist_id):
        """
        ID'ye göre playlist bul
        """
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return None
                
        playlist_data = mongo.db.playlists.find_one({'_id': playlist_id})
        
        if not playlist_data:
            return None
            
        return cls(**playlist_data)
    
    @classmethod
    def find_by_user(cls, user_id, status=None, limit=100, skip=0):
        """
        Kullanıcı ID'sine göre playlistleri bul
        """
        query = {'user_id': user_id}
        
        if status:
            query['status'] = status
            
        playlist_list = []
        for playlist_data in mongo.db.playlists.find(query).sort('created_at', -1).skip(skip).limit(limit):
            playlist_list.append(cls(**playlist_data))
            
        return playlist_list
    
    @classmethod
    def find_public(cls, limit=100, skip=0):
        """
        Herkese açık playlistleri bul
        """
        query = {'is_public': True, 'status': cls.STATUS_ACTIVE}
        
        playlist_list = []
        for playlist_data in mongo.db.playlists.find(query).sort('created_at', -1).skip(skip).limit(limit):
            playlist_list.append(cls(**playlist_data))
            
        return playlist_list
    
    @classmethod
    def find_all(cls, limit=100, skip=0):
        """
        Tüm playlistleri bul
        """
        playlist_list = []
        for playlist_data in mongo.db.playlists.find().sort('created_at', -1).skip(skip).limit(limit):
            playlist_list.append(cls(**playlist_data))
            
        return playlist_list
    
    @classmethod
    def update(cls, playlist_id, data):
        """
        Playlist güncelle
        """
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return False
                
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        # Güncellenebilir alanlar
        for field in ['name', 'description', 'is_public', 'status']:
            if field in data:
                update_data[field] = data[field]
                
        result = mongo.db.playlists.update_one(
            {'_id': playlist_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    @classmethod
    def delete(cls, playlist_id):
        """
        Playlist sil
        """
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return False
                
        # İlişkili playlist medya öğelerini sil
        mongo.db.playlist_media.delete_many({'playlist_id': playlist_id})
        
        # Playlist'i sil
        result = mongo.db.playlists.delete_one({'_id': playlist_id})
        
        return result.deleted_count > 0
    
    @classmethod
    def count_by_user(cls, user_id, status=None):
        """
        Kullanıcının playlist sayısını döndür
        """
        query = {'user_id': user_id}
        
        if status:
            query['status'] = status
            
        return mongo.db.playlists.count_documents(query)
    
    @classmethod
    def update_media_count(cls, playlist_id):
        """
        Playlist içindeki medya sayısını güncelle ve güncel sayıyı döndür
        """
        import traceback
        from datetime import datetime
        print(f"DEBUG - update_media_count başladı: playlist_id={playlist_id}")
        
        try:
            # ID'yi doğru formata dönüştür
            if isinstance(playlist_id, str):
                try:
                    obj_id = ObjectId(playlist_id)
                except:
                    obj_id = playlist_id
            else:
                obj_id = playlist_id
            
            # Playlist medyalarını say (hem string hem ObjectId formatını kontrol et)
            # Tek sorguda ve daha basit bir $or operatörü ile gerçekleştir
            count = mongo.db.playlist_media.count_documents({
                "$or": [
                    {"playlist_id": obj_id},
                    {"playlist_id": str(obj_id)}
                ]
            })
            
            print(f"DEBUG - Bulunan playlist medya sayısı: {count}")
            
            # Playlist'i güncelle - ObjectId dönüşüm hataları için try-except içinde
            try:
                update_id = obj_id if obj_id else playlist_id
                result = mongo.db.playlists.update_one(
                    {"_id": update_id},
                    {"$set": {"media_count": count, "updated_at": datetime.utcnow()}}
                )
                modified = result.modified_count
            except Exception as e:
                # ID formatı problemi olabilir, string olarak dene
                try:
                    result = mongo.db.playlists.update_one(
                        {"_id": ObjectId(str(update_id))},
                        {"$set": {"media_count": count, "updated_at": datetime.utcnow()}}
                    )
                    modified = result.modified_count
                except:
                    modified = 0
            
            print(f"DEBUG - Güncelleme sonucu: {modified} belge etkilendi.")
            return count
        except Exception as e:
            print(f"DEBUG - media_count güncelleme hatası: {str(e)}")
            print(traceback.format_exc())
            return 0
    
    @classmethod
    def update_all_media_counts(cls):
        """
        Tüm playlistlerin medya sayılarını günceller
        
        Returns:
            dict: Güncellenen playlist sayısı ve toplam medya sayısı
        """
        import traceback
        
        print("Tüm playlistlerin medya sayıları güncelleniyor...")
        updated_count = 0
        total_media = 0
        
        try:
            # Tüm playlistleri getir
            all_playlists = list(mongo.db.playlists.find())
            print(f"Toplam {len(all_playlists)} playlist bulundu")
            
            # Her bir playlist için medya sayısını güncelle
            for playlist in all_playlists:
                playlist_id = playlist['_id']
                
                # Medya sayısını hesapla
                old_count = playlist.get('media_count', 0)
                new_count = cls.update_media_count(playlist_id)
                
                if old_count != new_count:
                    updated_count += 1
                    print(f"Playlist {playlist.get('name')} ({playlist_id}): {old_count} -> {new_count}")
                
                total_media += new_count
        
        except Exception as e:
            print(f"Playlist medya sayıları güncellenirken hata: {str(e)}")
            print(traceback.format_exc())
        
        print(f"Toplam {updated_count} playlist güncellendi. Toplam {total_media} medya içeriği.")
        return {
            'updated_playlist_count': updated_count,
            'total_media_count': total_media
        }
    
    def __init__(self, _id, name, user_id, description=None, is_public=False, 
                 status=STATUS_ACTIVE, created_at=None, updated_at=None, media_count=0, **kwargs):
        """Yeni bir playlist örneği başlat"""
        self.id = str(_id)
        self.name = name
        self.description = description
        self.user_id = user_id
        self.is_public = is_public
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.media_count = media_count
    
    def update(self, **kwargs):
        """Playlist bilgilerini güncelle"""
        updates = {"updated_at": datetime.utcnow()}
        
        # Güncellenebilir alanlar
        updatable_fields = ['name', 'description', 'is_public', 'status']
        
        for field in updatable_fields:
            if field in kwargs:
                updates[field] = kwargs[field]
                
        # Veritabanını güncelle
        mongo.db.playlists.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": updates}
        )
        
        # Nesne bilgilerini güncelle
        for key, value in updates.items():
            setattr(self, key, value)
            
        return self
    
    def add_media(self, media_id, order=None, display_time=None):
        """Playlist'e medya ekle"""
        from app.models.playlist_media import PlaylistMedia
        
        if order is None:
            # Mevcut son sıraya ekle
            existing_count = PlaylistMedia.count_by_playlist(self.id)
            order = existing_count
            
        return PlaylistMedia.create({
            'playlist_id': self.id,
            'media_id': media_id,
            'order': order,
            'display_time': display_time
        })
    
    def remove_media(self, media_id):
        """Playlist'ten medya kaldır"""
        from app.models.playlist_media import PlaylistMedia
        
        return PlaylistMedia.remove_from_playlist(self.id, media_id)
    
    def get_media(self):
        """Playlist'teki medyaları getir"""
        from app.models.playlist_media import PlaylistMedia
        
        return PlaylistMedia.find_by_playlist(self.id)
    
    def update_media_count(self):
        """Medya sayısını güncelle"""
        from app.models.playlist_media import PlaylistMedia
        
        count = PlaylistMedia.count_by_playlist(self.id)
        
        mongo.db.playlists.update_one(
            {"_id": ObjectId(self.id)},
            {"$set": {"media_count": count}}
        )
        
        self.media_count = count
        return count
    
    def to_dict(self):
        """Playlist bilgilerini sözlük olarak döndür"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "is_public": self.is_public,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "media_count": self.media_count
        } 