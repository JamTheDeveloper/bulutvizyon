#!/usr/bin/env python3
import os
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
import urllib.parse
import json
from datetime import datetime

# MongoDB ObjectId'leri JSON formatına çevirmek için encoder
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

# .env dosyasından çevre değişkenlerini yükle
load_dotenv()

# MongoDB bağlantı bilgilerini al
MONGO_USER = os.getenv("MONGO_USER", "elektrobil_admin")
MONGO_PASS = os.getenv("MONGO_PASS", "Eb@2254097*")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB = os.getenv("MONGO_DB", "bulutvizyondb")

# Şifreyi URL için encode et
encoded_password = urllib.parse.quote_plus(MONGO_PASS)

# Bağlantı URL'ini oluştur
mongo_uri = f"mongodb://{MONGO_USER}:{encoded_password}@{MONGO_HOST}:{MONGO_PORT}/{MONGO_DB}?authSource=admin"

try:
    # MongoDB'ye bağlan
    client = pymongo.MongoClient(mongo_uri)
    db = client.get_database()
    
    # Admin sayfası için verileri topla
    admin_data = []
    
    # Tüm ekranları al
    screens = list(db.screens.find())
    
    for screen in screens:
        screen_data = {
            "ekran_id": screen["_id"],
            "ekran_adi": screen.get("name", "İsimsiz Ekran"),
            "ekran_durumu": screen.get("status", "Belirtilmemiş"),
            "playlists": []
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
                    
                    # Medya ilişkilerini sorgula
                    query_media = []
                    
                    # İki farklı biçimi kontrol et - Önce string ID
                    if isinstance(playlist["_id"], ObjectId):
                        playlist_id_str = str(playlist["_id"])
                        pm_items1 = list(db.playlist_media.find({"playlist_id": playlist_id_str}))
                        query_media.extend(pm_items1)
                    
                    # Sonra ObjectId
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
                            print(f"Medya hatası: {str(e)}")
                    
                    # Medya listesini sıralama numarasına göre sırala
                    playlist_data["media_listesi"] = sorted(playlist_data["media_listesi"], key=lambda x: x["sira"])
                    
                    screen_data["playlists"].append(playlist_data)
            except Exception as e:
                print(f"Playlist hatası: {str(e)}")
        
        admin_data.append(screen_data)
    
    # Sonuçları JSON formatında yazdır
    print(json.dumps(admin_data, cls=MongoJSONEncoder, indent=2, ensure_ascii=False))
    
    # Ayrıca bir dosyaya kaydet
    with open("admin_ekran_detay.json", "w", encoding="utf-8") as f:
        json.dump(admin_data, f, cls=MongoJSONEncoder, indent=2, ensure_ascii=False)
    
    print("\nVeriler admin_ekran_detay.json dosyasına kaydedildi.")
    
except Exception as e:
    print(f"Hata: {e}")
finally:
    # Bağlantıyı kapat
    if 'client' in locals():
        client.close() 