"""
Ekran-Playlist İlişkisi Modeli: Ekranlar ve playlistler arasındaki ilişkiyi yönetir
"""
from datetime import datetime
from bson import ObjectId
from app import mongo

class ScreenPlaylist:
    """
    Ekran-Playlist ilişki modeli
    
    Alanlar:
    - id: Benzersiz ID
    - screen_id: Ekran ID
    - playlist_id: Playlist ID
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
        Yeni ekran-playlist ilişkisi oluştur
        """
        screen_playlist = {
            'screen_id': data.get('screen_id'),
            'playlist_id': data.get('playlist_id'),
            'status': data.get('status', cls.STATUS_ACTIVE),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Önceden aynı ekran için playlist atanmışsa güncelle
        existing = cls.find_by_screen_id(data.get('screen_id'))
        if existing:
            screen_playlist['_id'] = existing['_id']
            mongo.db.screen_playlists.replace_one(
                {'_id': existing['_id']},
                screen_playlist
            )
            return screen_playlist
        
        # Yeni kayıt
        result = mongo.db.screen_playlists.insert_one(screen_playlist)
        screen_playlist['_id'] = result.inserted_id
        
        return screen_playlist
    
    @classmethod
    def find_by_id(cls, relation_id):
        """
        ID'ye göre ekran-playlist ilişkisini bul
        """
        if isinstance(relation_id, str):
            try:
                relation_id = ObjectId(relation_id)
            except:
                return None
        
        return mongo.db.screen_playlists.find_one({'_id': relation_id})
    
    @classmethod
    def find_by_screen_id(cls, screen_id):
        """
        Ekran ID'sine göre playlist ilişkisini bul
        """
        print(f"DEBUG - ScreenPlaylist.find_by_screen_id çağrıldı: {screen_id}")
        
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
        
        print(f"DEBUG - screen_playlists sorgusu: {query}")
        
        # İlişkiyi getir (en yakın tarihe göre)
        result = mongo.db.screen_playlists.find_one(query, sort=[('created_at', -1)])
        print(f"DEBUG - Bulunan ilişki: {result}")
        
        return result
    
    @classmethod
    def find_by_playlist_id(cls, playlist_id):
        """
        Playlist ID'sine göre ilişkileri bul
        """
        print(f"DEBUG - ScreenPlaylist.find_by_playlist_id çağrıldı: {playlist_id}")
        
        # Farklı format olasılıklarını göz önünde bulunduralım
        query_conditions = []
        
        # String ID durumu
        if isinstance(playlist_id, str):
            query_conditions.append({'playlist_id': playlist_id})
            
            # ObjectId dönüşümü yapabilirsek bu formatı da ekleyelim
            try:
                obj_id = ObjectId(playlist_id)
                query_conditions.append({'playlist_id': obj_id})
            except:
                pass
        
        # Halihazırda ObjectId ise 
        elif isinstance(playlist_id, ObjectId):
            query_conditions.append({'playlist_id': playlist_id})
            query_conditions.append({'playlist_id': str(playlist_id)})
        
        # Diğer durumlar için orijinal ID'yi kullan
        else:
            query_conditions.append({'playlist_id': playlist_id})
        
        # Her durum için OR sorgusu oluştur
        query = {
            '$or': query_conditions,
            'status': cls.STATUS_ACTIVE
        }
        
        print(f"DEBUG - screen_playlists sorgusu: {query}")
        
        # İlişkileri getir
        result = list(mongo.db.screen_playlists.find(query))
        print(f"DEBUG - Bulunan ilişki sayısı: {len(result)}")
        
        return result
    
    @classmethod
    def update(cls, relation_id, data):
        """
        İlişkiyi güncelle
        """
        if isinstance(relation_id, str):
            try:
                relation_id = ObjectId(relation_id)
            except:
                return False
        
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        # Güncellenebilir alanlar
        for field in ['status']:
            if field in data:
                update_data[field] = data[field]
        
        result = mongo.db.screen_playlists.update_one(
            {'_id': relation_id},
            {'$set': update_data}
        )
        
        return result.modified_count > 0
    
    @classmethod
    def delete(cls, relation_id):
        """
        İlişkiyi sil
        """
        if isinstance(relation_id, str):
            try:
                relation_id = ObjectId(relation_id)
            except:
                return False
        
        result = mongo.db.screen_playlists.delete_one({'_id': relation_id})
        
        return result.deleted_count > 0
    
    @classmethod
    def delete_by_screen(cls, screen_id):
        """
        Ekrana ait tüm ilişkileri sil
        """
        print(f"DEBUG - ScreenPlaylist.delete_by_screen çağrıldı: screen_id={screen_id}")
        
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
        
        print(f"DEBUG - Silinecek kayıtlar için sorgu: {query}")
        
        # Silinecek kayıtları göster
        matching_records = list(mongo.db.screen_playlists.find(query))
        print(f"DEBUG - Eşleşen kayıt sayısı: {len(matching_records)}")
        for record in matching_records:
            print(f"DEBUG - Silinecek kayıt: {record}")
        
        # Silme işlemi
        result = mongo.db.screen_playlists.delete_many(query)
        deleted_count = result.deleted_count
        print(f"DEBUG - Silinen kayıt sayısı: {deleted_count}")
        
        return deleted_count
    
    @classmethod
    def delete_by_playlist(cls, playlist_id):
        """
        Playlist'e ait tüm ilişkileri sil
        """
        if isinstance(playlist_id, str):
            try:
                playlist_id = ObjectId(playlist_id)
            except:
                return 0
        
        result = mongo.db.screen_playlists.delete_many({'playlist_id': playlist_id})
        
        return result.deleted_count 