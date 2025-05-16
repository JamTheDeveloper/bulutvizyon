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
    def create(cls, playlist_id=None, media_id=None, display_time=None, order=None, **kwargs):
        """Yeni playlist medya ilişkisi oluşturur"""
        
        import traceback
        print(f"PlaylistMedia.create called with: playlist_id={playlist_id}, media_id={media_id}, display_time={display_time}")
        
        # ID kontrolleri
        try:
            # playlist_id'yi ObjectId'ye dönüştür
            if isinstance(playlist_id, str):
                try:
                    playlist_id = ObjectId(playlist_id)
                    print(f"Playlist ID converted to ObjectId: {playlist_id}")
                except Exception as e:
                    print(f"Error converting playlist_id to ObjectId: {e}")
                    raise ValueError(f"Geçersiz playlist ID formatı: {playlist_id}")
                
            # media_id'yi ObjectId'ye dönüştür
            if isinstance(media_id, str):
                try:
                    media_id = ObjectId(media_id)
                    print(f"Media ID converted to ObjectId: {media_id}")
                except Exception as e:
                    print(f"Error converting media_id to ObjectId: {e}")
                    raise ValueError(f"Geçersiz media ID formatı: {media_id}")
                
            # Null kontrolleri
            if not playlist_id:
                raise ValueError("Playlist ID gereklidir")
            if not media_id:
                raise ValueError("Media ID gereklidir")
            
            # Son ID kontrolü
            try:
                # Playlist'in var olduğunu kontrol et
                from app.models.playlist import Playlist
                playlist = Playlist.find_by_id(playlist_id)
                if not playlist:
                    print(f"Playlist not found: {playlist_id}")
                    raise ValueError(f"Playlist bulunamadı: {playlist_id}")
                
                # Media'nın var olduğunu kontrol et
                from app.models.media import Media
                media = Media.find_by_id(media_id)
                if not media:
                    print(f"Media not found: {media_id}")
                    raise ValueError(f"Media bulunamadı: {media_id}")
            except Exception as check_error:
                print(f"Error checking playlist/media existence: {check_error}")
            
            # Sıra numarasını belirle - verilmemişse en sona ekle
            if order is None:
                order = cls.get_max_order(playlist_id) + 1
            
            # Yeni playlist media dökümanı
            playlist_media = {
                'playlist_id': playlist_id,
                'media_id': media_id,
                'display_time': 10 if display_time is None else display_time,
                'order': order,
                'created_at': datetime.utcnow()
            }
            
            # Ek parametreler
            for key, value in kwargs.items():
                playlist_media[key] = value
            
            # MongoDB'ye ekle
            result = mongo.db.playlist_media.insert_one(playlist_media)
            
            # ID'yi ayarla ve döndür
            playlist_media['_id'] = result.inserted_id
            print(f"Playlist media created successfully: {result.inserted_id}")
            
            # Playlist medya sayısını güncelle
            try:
                from app.models.playlist import Playlist
                Playlist.update_media_count(playlist_id)
            except Exception as e:
                print(f"Error updating playlist media count: {e}")
            
            return playlist_media
        except Exception as e:
            print(f"Error in PlaylistMedia.create: {e}")
            print(traceback.format_exc())
            raise
    
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
        import traceback
        print(f"PlaylistMedia.find_by_playlist çağrıldı: playlist_id={playlist_id}, tip={type(playlist_id)}")
        
        try:
            # ObjectId dönüşümü
            if isinstance(playlist_id, str):
                try:
                    obj_id = ObjectId(playlist_id)
                    print(f"Playlist ID ObjectId'ye dönüştürüldü: {obj_id}")
                except Exception as e:
                    print(f"ObjectId dönüşüm hatası: {str(e)}")
                    obj_id = None
            else:
                obj_id = playlist_id
            
            # Her iki ID formatı için sorgu
            query = {"$or": []}
            
            if obj_id:
                query["$or"].append({"playlist_id": obj_id})
            
            if isinstance(playlist_id, str):
                query["$or"].append({"playlist_id": playlist_id})
            elif obj_id:
                query["$or"].append({"playlist_id": str(obj_id)})
            
            print(f"Sorgu: {query}")
            
            # Bu playlist'teki tüm medyaları al ve sırala
            playlist_media = list(mongo.db.playlist_media.find(query).sort("order", 1))
            print(f"Bulunan playlist media sayısı: {len(playlist_media)}")
            
            # Medya detaylarını ekle
            from app.models.media import Media
            
            result_with_media = []
            for pm in playlist_media:
                print(f"Playlist media işleniyor: {pm.get('_id')}, media_id: {pm.get('media_id')}")
                
                # Her medyanın detaylarını al
                media_id = pm.get('media_id')
                media = None
                
                if media_id:
                    # Doğrudan string ID'yi ObjectId'ye dönüştürmeyi deneyelim
                    if isinstance(media_id, str):
                        try:
                            media_id_obj = ObjectId(media_id)
                            media = Media.find_by_id(media_id_obj)
                            print(f"String media_id ile bulma başarılı: {media_id}")
                        except Exception as e:
                            print(f"String ID dönüşüm hatası: {e}")
                            # Dönüşüm başarısız olursa orijinal ID ile devam et
                    
                    # ObjectId ile bulunamadıysa orijinal ID ile tekrar dene
                    if not media:
                        media = Media.find_by_id(media_id)
                        print(f"Orijinal media_id ile sorgu: {media_id}, tip: {type(media_id)}")
                    
                    # Hala bulunamadıysa string ile dene
                    if not media and isinstance(media_id, ObjectId):
                        media = Media.find_by_id(str(media_id))
                        print(f"String'e dönüştürülmüş media_id ile sorgu: {str(media_id)}")
                    
                    print(f"Medya bulundu mu: {bool(media)}")
                    
                    # Medya bulunamazsa atlama, önemli medya bilgilerini ekle
                    if media:
                        # Medya bilgilerini ekle
                        pm['media'] = media
                        
                        # Görüntülenme süresini kontrol et ve varsayılan değer ata
                        if pm.get('display_time') is None:
                            # Medya nesnesinden süreyi al, o da yoksa varsayılan değer kullan
                            if isinstance(media, dict) and media.get('display_time'):
                                pm['display_time'] = media.get('display_time')
                            elif hasattr(media, 'display_time') and media.display_time:
                                pm['display_time'] = media.display_time
                            else:
                                pm['display_time'] = 10
                    else:
                        print(f"Medya bulunamadı, ID: {media_id}")
                        
                        # MongoDB'den doğrudan sorgu yapalım
                        try:
                            direct_media = mongo.db.media.find_one({'_id': media_id})
                            if not direct_media and isinstance(media_id, ObjectId):
                                direct_media = mongo.db.media.find_one({'_id': str(media_id)})
                            if not direct_media and isinstance(media_id, str):
                                try:
                                    direct_media = mongo.db.media.find_one({'_id': ObjectId(media_id)})
                                except:
                                    pass
                                    
                            # Alternatif koleksiyon adını dene
                            if not direct_media:
                                direct_media = mongo.db.medias.find_one({'_id': media_id})
                                if not direct_media and isinstance(media_id, ObjectId):
                                    direct_media = mongo.db.medias.find_one({'_id': str(media_id)})
                                if not direct_media and isinstance(media_id, str):
                                    try:
                                        direct_media = mongo.db.medias.find_one({'_id': ObjectId(media_id)})
                                    except:
                                        pass
                            
                            if direct_media:
                                print(f"Doğrudan MongoDB sorgusu ile medya bulundu: {direct_media.get('_id')}")
                                pm['media'] = direct_media
                                
                                # Görüntülenme süresini ayarla
                                if pm.get('display_time') is None:
                                    pm['display_time'] = direct_media.get('display_time', 10)
                            else:
                                # Boş bir medya nesnesi ekle
                                pm['media'] = {
                                    '_id': media_id,
                                    'title': 'Medya bulunamadı',
                                    'file_type': 'unknown',
                                    'filename': ''
                                }
                        except Exception as mongo_error:
                            print(f"Doğrudan MongoDB sorgusu hatası: {mongo_error}")
                            # Boş bir medya nesnesi ekle
                            pm['media'] = {
                                '_id': media_id,
                                'title': 'Medya bulunamadı',
                                'file_type': 'unknown',
                                'filename': ''
                            }
                
                result_with_media.append(pm)
            
            print(f"Medya bilgileriyle birlikte döndürülen item sayısı: {len(result_with_media)}")
            return result_with_media
        except Exception as e:
            print(f"find_by_playlist hatası: {str(e)}")
            print(traceback.format_exc())
            return []
    
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
                return 0
                
        # Son sıradaki öğeyi bul
        result = mongo.db.playlist_media.find_one(
            {"playlist_id": playlist_id}, 
            sort=[("order", -1)]
        )
        
        if result:
            return result.get("order", 0)
        return 0
    
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