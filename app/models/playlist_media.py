"""
Playlist-Medya ilişkisi modeli: Playlistlere atanmış medyaların ilişkilerini yönetir
"""
from datetime import datetime
from bson.objectid import ObjectId
from app import mongo

class PlaylistMedia:
    """
    Playlist-Medya ilişkisini yöneten model sınıfı
    """
    
    # Statü değerleri
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    
    @classmethod
    def create(cls, data):
        """Yeni bir playlist-medya ilişkisi oluştur"""
        import traceback
        
        try:
            print(f"DEBUG - PlaylistMedia.create - Gelen veriler: {data}")
            
            # playlist_id ve media_id'yi ObjectId'ye dönüştür
            playlist_id = data.get('playlist_id')
            media_id = data.get('media_id')
            
            print(f"DEBUG - Ham playlist_id: {playlist_id}, media_id: {media_id}")
            
            if isinstance(playlist_id, str):
                try:
                    playlist_id = ObjectId(playlist_id)
                    print(f"DEBUG - playlist_id ObjectId'ye dönüştürüldü: {playlist_id}")
                except Exception as e:
                    print(f"DEBUG - playlist_id ObjectId dönüşüm hatası: {str(e)}")
                    return None
            
            if isinstance(media_id, str):
                try:
                    media_id = ObjectId(media_id)
                    print(f"DEBUG - media_id ObjectId'ye dönüştürüldü: {media_id}")
                except Exception as e:
                    print(f"DEBUG - media_id ObjectId dönüşüm hatası: {str(e)}")
                    return None
            
            playlist_media_data = {
                "playlist_id": playlist_id,
                "media_id": media_id,
                "order": data.get('order', 0),  # Sıralama için kullanılır
                "display_time": data.get('display_time'),  # Medyanın gösterilme süresi (None ise varsayılan değer kullanılır)
                "status": data.get('status', cls.STATUS_ACTIVE),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            print(f"DEBUG - Oluşturulan playlist_media_data: {playlist_media_data}")
            
            # Aynı playlist ve medya ilişkisi varsa güncelle
            existing = mongo.db.playlist_media.find_one({
                "playlist_id": playlist_id,
                "media_id": media_id
            })
            
            print(f"DEBUG - Mevcut playlist_media kontrolü: {existing}")
            
            if existing:
                playlist_media_data["_id"] = existing["_id"]
                print(f"DEBUG - Var olan playlist_media güncelleniyor: {existing['_id']}")
                
                mongo.db.playlist_media.replace_one({"_id": existing["_id"]}, playlist_media_data)
                
                # Playlist medya sayısını güncelle
                from app.models.playlist import Playlist
                print(f"DEBUG - Playlist.find_by_id çağrılıyor: {playlist_id}")
                
                playlist = Playlist.find_by_id(playlist_id)
                if playlist:
                    print(f"DEBUG - Playlist bulundu, medya sayısı güncelleniyor")
                    playlist.update_media_count()
                else:
                    print(f"DEBUG - Playlist bulunamadı: {playlist_id}")
                    
                return existing
                
            # Yoksa yeni oluştur
            print(f"DEBUG - Yeni playlist_media oluşturuluyor")
            
            result = mongo.db.playlist_media.insert_one(playlist_media_data)
            playlist_media_data['_id'] = result.inserted_id
            
            print(f"DEBUG - Yeni oluşturulan playlist_media ID: {result.inserted_id}")
            
            # Playlist medya sayısını güncelle
            from app.models.playlist import Playlist
            print(f"DEBUG - Playlist.find_by_id çağrılıyor (yeni): {playlist_id}")
            
            playlist = Playlist.find_by_id(playlist_id)
            if playlist:
                print(f"DEBUG - Playlist bulundu (yeni), medya sayısı güncelleniyor")
                playlist.update_media_count()
            else:
                print(f"DEBUG - Playlist bulunamadı (yeni): {playlist_id}")
                
            return playlist_media_data
        except Exception as e:
            print(f"DEBUG - PlaylistMedia.create genel hatası: {str(e)}")
            print(traceback.format_exc())
            return None
    
    @classmethod
    def find_by_id(cls, playlist_media_id):
        """ID'ye göre playlist-medya ilişkisi bul"""
        if isinstance(playlist_media_id, str):
            try:
                playlist_media_id = ObjectId(playlist_media_id)
            except:
                return None
                
        return mongo.db.playlist_media.find_one({"_id": playlist_media_id})
    
    @classmethod
    def find_by_playlist(cls, playlist_id):
        """Belirli bir playlist'teki tüm medyaları bul"""
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return []
        
        # Playlist-media ilişkisini bul ve sırala
        relations = list(mongo.db.playlist_media.find({"playlist_id": playlist_id}).sort("order", 1))
        
        # Medya detaylarını ekle
        from app.models.media import Media
        
        for relation in relations:
            media = Media.find_by_id(relation['media_id'])
            if media:
                relation['media'] = media
                
        return relations
    
    @classmethod
    def find_by_media(cls, media_id):
        """Belirli bir medyanın atandığı tüm playlist'leri bul"""
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
            except:
                return []
                
        return list(mongo.db.playlist_media.find({"media_id": media_id}))
    
    @classmethod
    def find_by_playlist_and_media(cls, playlist_id, media_id):
        """Belirli bir playlist ve medya ilişkisini bul"""
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return None
                
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
            except:
                return None
                
        return mongo.db.playlist_media.find_one({
            "playlist_id": playlist_id,
            "media_id": media_id
        })
    
    @classmethod
    def remove_from_playlist(cls, playlist_id, media_id):
        """Belirli bir playlist'ten medyayı kaldır"""
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return False
                
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
            except:
                return False
                
        result = mongo.db.playlist_media.delete_one({
            "playlist_id": playlist_id,
            "media_id": media_id
        })
        
        # Playlist medya sayısını güncelle
        from app.models.playlist import Playlist
        playlist = Playlist.find_by_id(playlist_id)
        if playlist:
            playlist.update_media_count()
            
        return result.deleted_count > 0
    
    @classmethod
    def clear_playlist(cls, playlist_id):
        """Bir playlist'teki tüm medyaları temizle"""
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return False
                
        result = mongo.db.playlist_media.delete_many({"playlist_id": playlist_id})
        
        # Playlist medya sayısını güncelle
        from app.models.playlist import Playlist
        playlist = Playlist.find_by_id(playlist_id)
        if playlist:
            playlist.update_media_count()
            
        return result.deleted_count
    
    @classmethod
    def reorder_playlist_media(cls, playlist_id, media_order):
        """
        Playlist'teki medyaları yeniden sırala
        
        media_order: [{"media_id": "...", "order": 1}, ...]
        """
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return False
                
        for item in media_order:
            media_id = item["media_id"]
            if isinstance(media_id, str):
                try:
                    media_id = ObjectId(media_id)
                except:
                    continue
                    
            mongo.db.playlist_media.update_one(
                {"playlist_id": playlist_id, "media_id": media_id},
                {"$set": {"order": item["order"], "updated_at": datetime.utcnow()}}
            )
            
        return True
    
    @classmethod
    def count_by_playlist(cls, playlist_id):
        """
        Belirli bir playlist'e ait medya sayısını döndür
        """
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return 0
                
        return mongo.db.playlist_media.count_documents({'playlist_id': playlist_id})
        
    @classmethod
    def get_max_order(cls, playlist_id):
        """
        Belirli bir playlist'teki en yüksek sıra numarasını döndürür
        """
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return None
                
        # Son sıradaki öğeyi bul
        result = mongo.db.playlist_media.find_one(
            {"playlist_id": playlist_id}, 
            sort=[("order", -1)]
        )
        
        if result:
            return result.get("order", 0)
        return None
    
    @classmethod
    def find_one(cls, query):
        """
        Belirtilen sorguya uyan bir playlist-medya ilişkisini döndürür
        """
        # ObjectId dönüşümlerini kontrol et
        if 'playlist_id' in query and isinstance(query['playlist_id'], str):
            try:
                query['playlist_id'] = ObjectId(query['playlist_id'])
            except:
                return None
        
        if 'media_id' in query and isinstance(query['media_id'], str):
            try:
                query['media_id'] = ObjectId(query['media_id'])
            except:
                return None
                
        return mongo.db.playlist_media.find_one(query)
    
    @classmethod
    def remove_media_from_all_playlists(cls, media_id):
        """
        Belirli bir medyayı tüm playlistlerden kaldır
        
        Args:
            media_id: Kaldırılacak medya ID'si
            
        Returns:
            Silinen kayıt sayısı
        """
        # String ID'yi ObjectId'ye çevirme girişimi
        if isinstance(media_id, str):
            try:
                media_id_obj = ObjectId(media_id)
            except:
                media_id_obj = None
                
            # Her iki format için sorgu
            result1 = mongo.db.playlist_media.delete_many({'media_id': media_id})
            
            if media_id_obj:
                result2 = mongo.db.playlist_media.delete_many({'media_id': media_id_obj})
                return result1.deleted_count + result2.deleted_count
            return result1.deleted_count
        else:
            # ObjectId olarak verilmişse
            result1 = mongo.db.playlist_media.delete_many({'media_id': media_id})
            result2 = mongo.db.playlist_media.delete_many({'media_id': str(media_id)})
            return result1.deleted_count + result2.deleted_count
    
    @classmethod
    def count_by_media(cls, media_id):
        """Medyanın atandığı playlist sayısını döndür"""
        if isinstance(media_id, str):
            try:
                media_id = ObjectId(media_id)
            except:
                return 0
                
        return mongo.db.playlist_media.count_documents({"media_id": media_id})
    
    @classmethod
    def update(cls, playlist_media_id, data):
        """Playlist-medya ilişkisini güncelle"""
        if isinstance(playlist_media_id, str):
            try:
                playlist_media_id = ObjectId(playlist_media_id)
            except:
                return False
                
        update_data = {
            "updated_at": datetime.utcnow()
        }
        
        # Güncellenebilir alanlar
        for field in ["order", "display_time", "status"]:
            if field in data:
                update_data[field] = data[field]
                
        result = mongo.db.playlist_media.update_one(
            {"_id": playlist_media_id},
            {"$set": update_data}
        )
        
        return result.modified_count > 0
    
    @classmethod
    def delete(cls, playlist_media_id):
        """Playlist-medya ilişkisini sil"""
        if isinstance(playlist_media_id, str):
            try:
                playlist_media_id = ObjectId(playlist_media_id)
            except:
                return False
                
        # İlişki bilgilerini al
        relation = mongo.db.playlist_media.find_one({"_id": playlist_media_id})
        
        if not relation:
            return False
            
        result = mongo.db.playlist_media.delete_one({"_id": playlist_media_id})
        
        # Playlist medya sayısını güncelle
        if result.deleted_count > 0 and relation.get('playlist_id'):
            from app.models.playlist import Playlist
            playlist = Playlist.find_by_id(relation['playlist_id'])
            if playlist:
                playlist.update_media_count()
                
        return result.deleted_count > 0 