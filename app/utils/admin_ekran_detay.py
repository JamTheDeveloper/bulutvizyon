import os
import pymongo
from bson.objectid import ObjectId
import urllib.parse
from flask import current_app
from datetime import datetime
import json

class MongoJSONEncoder(json.JSONEncoder):
    """MongoDB ObjectId ve datetime nesnelerini JSON'a çevirmek için encoder"""
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

def get_mongo_connection():
    """MongoDB bağlantısı oluşturur"""
    # MongoDB bağlantı bilgilerini al
    mongo_user = current_app.config.get("MONGO_USER", os.getenv("MONGO_USER", "elektrobil_admin"))
    mongo_pass = current_app.config.get("MONGO_PASS", os.getenv("MONGO_PASS", "Eb@2254097*"))
    mongo_host = current_app.config.get("MONGO_HOST", os.getenv("MONGO_HOST", "localhost"))
    mongo_port = current_app.config.get("MONGO_PORT", os.getenv("MONGO_PORT", "27017"))
    mongo_db = current_app.config.get("MONGO_DB", os.getenv("MONGO_DB", "bulutvizyondb"))

    # Şifreyi URL için encode et
    encoded_password = urllib.parse.quote_plus(mongo_pass)

    # Bağlantı URL'ini oluştur
    mongo_uri = f"mongodb://{mongo_user}:{encoded_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"

    # MongoDB'ye bağlan
    client = pymongo.MongoClient(mongo_uri)
    db = client.get_database()
    
    return client, db

def get_user_screens_detail(user_id=None):
    """Kullanıcının ekranlarını ve ilişkili playlist ve medya detaylarını alır.
    
    Args:
        user_id: Kullanıcı ID'si, None ise tüm ekranlar getirilir
        
    Returns:
        Ekran, playlist ve medya detaylarını içeren liste
    """
    try:
        # MongoDB bağlantısı oluştur
        client, db = get_mongo_connection()
        
        # Admin sayfası için verileri topla
        screens_data = []
        
        # Kullanıcı filtresini uygula
        query = {}
        if user_id:
            query = {"user_id": user_id}
            
        # Ekranları sorgula
        screens = list(db.screens.find(query))
        
        for screen in screens:
            screen_data = {
                "ekran_id": screen["_id"],
                "ekran_adi": screen.get("name", "İsimsiz Ekran"),
                "ekran_durumu": screen.get("status", "Belirtilmemiş"),
                "user_id": screen.get("user_id", ""),
                "kullanici": None,
                "playlists": []
            }
            
            # Kullanıcı bilgilerini al
            if 'user_id' in screen:
                user = db.users.find_one({"_id": ObjectId(screen["user_id"])})
                if user:
                    screen_data["kullanici"] = {
                        "id": user["_id"],
                        "ad": user.get("name", ""),
                        "email": user.get("email", "")
                    }
            
            # Bu ekrana atanmış playlist'leri bul
            screen_playlists = db.screen_playlists.find({"screen_id": str(screen["_id"])})
            
            for sp in screen_playlists:
                playlist_id = sp.get("playlist_id")
                
                try:
                    # Playlist detaylarını al
                    if isinstance(playlist_id, str):
                        playlist = db.playlists.find_one({"_id": ObjectId(playlist_id)})
                    else:
                        playlist = db.playlists.find_one({"_id": playlist_id})
                    
                    if playlist:
                        playlist_data = {
                            "playlist_id": playlist["_id"],
                            "playlist_adi": playlist.get("name", "İsimsiz Playlist"),
                            "aciklama": playlist.get("description", ""),
                            "durum": playlist.get("status", ""),
                            "media_count": playlist.get("media_count", 0),
                            "media_listesi": []
                        }
                        
                        # Medya ilişkilerini sorgula - İki farklı biçimi kontrol et
                        query_media = []
                        
                        # 1. String ID ile kontrol
                        if isinstance(playlist["_id"], ObjectId):
                            playlist_id_str = str(playlist["_id"])
                            pm_items1 = list(db.playlist_media.find({"playlist_id": playlist_id_str}))
                            query_media.extend(pm_items1)
                        
                        # 2. ObjectId ile kontrol
                        pm_items2 = list(db.playlist_media.find({"playlist_id": playlist["_id"]}))
                        query_media.extend(pm_items2)
                        
                        # Medya bilgilerini ekle
                        for pm in query_media:
                            media_id = pm.get("media_id")
                            
                            try:
                                if isinstance(media_id, str):
                                    media = db.media.find_one({"_id": ObjectId(media_id)})
                                else:
                                    media = db.media.find_one({"_id": media_id})
                                    
                                if media:
                                    media_data = {
                                        "media_id": media["_id"],
                                        "media_adi": media.get("title", "İsimsiz Medya"),
                                        "dosya_adi": media.get("filename", ""),
                                        "dosya_turu": media.get("file_type", ""),
                                        "gosterim_suresi": pm.get("display_time", media.get("display_time", 10)),
                                        "sira": pm.get("order", 0)
                                    }
                                    playlist_data["media_listesi"].append(media_data)
                            except Exception as e:
                                current_app.logger.error(f"Medya hatası: {str(e)}")
                        
                        # Medya listesini sıralama numarasına göre sırala
                        playlist_data["media_listesi"] = sorted(playlist_data["media_listesi"], key=lambda x: x["sira"])
                        
                        screen_data["playlists"].append(playlist_data)
                except Exception as e:
                    current_app.logger.error(f"Playlist hatası: {str(e)}")
            
            screens_data.append(screen_data)
        
        return screens_data
    
    except Exception as e:
        current_app.logger.error(f"Ekran detayları getirilirken hata: {str(e)}")
        return []
    finally:
        # Bağlantıyı kapat
        if 'client' in locals():
            client.close()

def get_screen_detail(screen_id):
    """Belirli bir ekranın detaylarını ve ilişkili playlist ve medya bilgilerini alır
    
    Args:
        screen_id: Ekran ID'si
        
    Returns:
        Ekran, playlist ve medya detaylarını içeren sözlük
    """
    try:
        # MongoDB bağlantısı oluştur
        client, db = get_mongo_connection()
        
        # Ekranı bul
        screen = db.screens.find_one({"_id": ObjectId(screen_id)})
        
        if not screen:
            return None
            
        screen_data = {
            "ekran_id": screen["_id"],
            "ekran_adi": screen.get("name", "İsimsiz Ekran"),
            "ekran_durumu": screen.get("status", "Belirtilmemiş"),
            "user_id": screen.get("user_id", ""),
            "kullanici": None,
            "playlists": []
        }
        
        # Kullanıcı bilgilerini al
        if 'user_id' in screen:
            user = db.users.find_one({"_id": ObjectId(screen["user_id"])})
            if user:
                screen_data["kullanici"] = {
                    "id": user["_id"],
                    "ad": user.get("name", ""),
                    "email": user.get("email", "")
                }
        
        # Bu ekrana atanmış playlist'leri bul
        screen_playlists = db.screen_playlists.find({"screen_id": str(screen["_id"])})
        
        for sp in screen_playlists:
            playlist_id = sp.get("playlist_id")
            
            try:
                # Playlist detaylarını al
                if isinstance(playlist_id, str):
                    playlist = db.playlists.find_one({"_id": ObjectId(playlist_id)})
                else:
                    playlist = db.playlists.find_one({"_id": playlist_id})
                
                if playlist:
                    playlist_data = {
                        "playlist_id": playlist["_id"],
                        "playlist_adi": playlist.get("name", "İsimsiz Playlist"),
                        "aciklama": playlist.get("description", ""),
                        "durum": playlist.get("status", ""),
                        "media_count": playlist.get("media_count", 0),
                        "media_listesi": []
                    }
                    
                    # Medya ilişkilerini sorgula - İki farklı biçimi kontrol et
                    query_media = []
                    
                    # 1. String ID ile kontrol
                    if isinstance(playlist["_id"], ObjectId):
                        playlist_id_str = str(playlist["_id"])
                        pm_items1 = list(db.playlist_media.find({"playlist_id": playlist_id_str}))
                        query_media.extend(pm_items1)
                    
                    # 2. ObjectId ile kontrol
                    pm_items2 = list(db.playlist_media.find({"playlist_id": playlist["_id"]}))
                    query_media.extend(pm_items2)
                    
                    # Medya bilgilerini ekle
                    for pm in query_media:
                        media_id = pm.get("media_id")
                        
                        try:
                            if isinstance(media_id, str):
                                media = db.media.find_one({"_id": ObjectId(media_id)})
                            else:
                                media = db.media.find_one({"_id": media_id})
                                
                            if media:
                                media_data = {
                                    "media_id": media["_id"],
                                    "media_adi": media.get("title", "İsimsiz Medya"),
                                    "dosya_adi": media.get("filename", ""),
                                    "dosya_turu": media.get("file_type", ""),
                                    "gosterim_suresi": pm.get("display_time", media.get("display_time", 10)),
                                    "sira": pm.get("order", 0),
                                    "url": f"/static/uploads/{media.get('filename', '')}" if media.get('filename') else ''
                                }
                                playlist_data["media_listesi"].append(media_data)
                        except Exception as e:
                            current_app.logger.error(f"Medya hatası: {str(e)}")
                    
                    # Medya listesini sıralama numarasına göre sırala
                    playlist_data["media_listesi"] = sorted(playlist_data["media_listesi"], key=lambda x: x["sira"])
                    
                    screen_data["playlists"].append(playlist_data)
            except Exception as e:
                current_app.logger.error(f"Playlist hatası: {str(e)}")
        
        return screen_data
        
    except Exception as e:
        current_app.logger.error(f"Ekran detayı getirilirken hata: {str(e)}")
        return None
    finally:
        # Bağlantıyı kapat
        if 'client' in locals():
            client.close() 