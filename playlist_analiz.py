#!/usr/bin/env python3
import os
import pymongo
from bson.objectid import ObjectId
from dotenv import load_dotenv
import urllib.parse

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
    
    print("==== PLAYLIST VE MEDYA ANALİZİ ====\n")
    
    # Tüm playlist'leri al
    playlists = list(db.playlists.find({}))
    print(f"Veritabanında {len(playlists)} playlist bulundu.\n")
    
    for playlist in playlists:
        playlist_id = playlist["_id"]
        playlist_id_str = str(playlist_id)
        
        print(f"PLAYLIST: {playlist.get('name', 'İsimsiz')} (ID: {playlist_id})")
        print(f"  Tanım: {playlist.get('description', 'Açıklama yok')}")
        print(f"  Durum: {playlist.get('status', 'Belirtilmemiş')}")
        print(f"  Metadatada gösterilen medya sayısı: {playlist.get('media_count', 0)}")
        
        # Farklı formatları test et
        media_count1 = db.playlist_media.count_documents({"playlist_id": playlist_id_str})
        media_count2 = db.playlist_media.count_documents({"playlist_id": playlist_id})
        
        print(f"  Medya ilişkileri (string ID kullanarak): {media_count1}")
        print(f"  Medya ilişkileri (ObjectId kullanarak): {media_count2}")
        
        # Playlist_mediaları getir
        playlist_media = list(db.playlist_media.find({"playlist_id": playlist_id_str}))
        if not playlist_media:
            playlist_media = list(db.playlist_media.find({"playlist_id": playlist_id}))
        
        if playlist_media:
            print(f"\n  Bu playlist'e ait {len(playlist_media)} medya dosyası bulundu:")
            for i, pm in enumerate(playlist_media, 1):
                media_id = pm.get("media_id")
                try:
                    media = db.media.find_one({"_id": ObjectId(media_id)})
                    if media:
                        print(f"    {i}. {media.get('title', 'İsimsiz')} (ID: {media['_id']})")
                    else:
                        print(f"    {i}. Medya bulunamadı (ID: {media_id})")
                except Exception as e:
                    print(f"    {i}. Hata: {str(e)} (ID: {media_id})")
        else:
            print("\n  Bu playlist için medya ilişkisi bulunamadı.")
            
            # Alternatif sorgu denemeleri
            print("\n  Alternatif ID Sorguları Deneniyor:")
            
            # MongoDB'de kullanılan diğer playlist ID formatlarını kontrol et
            pm_sample = db.playlist_media.find_one()
            if pm_sample:
                print(f"  playlist_media koleksiyonundan örnek playlist_id: {pm_sample.get('playlist_id')}")
                print(f"  playlist_id veri tipi: {type(pm_sample.get('playlist_id'))}")
                
                # Farklı ID formatlarını dene
                playlist_id_hex = playlist_id.hex()
                media_count_hex = db.playlist_media.count_documents({"playlist_id": playlist_id_hex})
                print(f"  Medya ilişkileri (hex ID kullanarak): {media_count_hex}")
                
        # Bu playlist'in ekranlarda görüntülenme durumu
        screen_playlists = list(db.screen_playlists.find({"playlist_id": playlist_id_str}))
        if not screen_playlists:
            screen_playlists = list(db.screen_playlists.find({"playlist_id": playlist_id}))
        
        if screen_playlists:
            print(f"\n  Bu playlist {len(screen_playlists)} ekranda görüntüleniyor:")
            for sp in screen_playlists:
                screen_id = sp.get("screen_id")
                try:
                    screen = db.screens.find_one({"_id": ObjectId(screen_id)})
                    if screen:
                        print(f"    - {screen.get('name', 'İsimsiz Ekran')} (ID: {screen['_id']})")
                    else:
                        print(f"    - Ekran bulunamadı (ID: {screen_id})")
                except Exception as e:
                    print(f"    - Hata: {str(e)} (ID: {screen_id})")
        else:
            print("\n  Bu playlist hiçbir ekranda görüntülenmiyor.")
        
        print("\n" + "-"*50 + "\n")
    
    # playlist_media koleksiyonunun içeriğini analiz et
    print("\n==== PLAYLIST_MEDIA ANALİZİ ====")
    
    playlist_media_items = list(db.playlist_media.find().limit(10))
    print(f"Toplam playlist_media ilişki sayısı: {db.playlist_media.count_documents({})}")
    
    if playlist_media_items:
        print("\nİlk 10 playlist_media örneği:")
        playlist_ids = set()
        
        for i, pm in enumerate(playlist_media_items, 1):
            playlist_id = pm.get("playlist_id")
            media_id = pm.get("media_id")
            playlist_ids.add(playlist_id)
            
            print(f"{i}. playlist_id: {playlist_id} (tip: {type(playlist_id)})")
            print(f"   media_id: {media_id}")
            print(f"   display_time: {pm.get('display_time')}")
            print(f"   order: {pm.get('order')}")
            print()
        
        print(f"Kullanılan benzersiz playlist_id sayısı: {len(playlist_ids)}")
        print("Kullanılan playlist_id'ler:")
        
        for pid in playlist_ids:
            # Bu ID'ye karşılık gelen playlist var mı kontrol et
            try:
                playlist = db.playlists.find_one({"_id": ObjectId(pid)})
                if playlist:
                    print(f"  - {pid} -> Playlist: {playlist.get('name', 'İsimsiz')}")
                else:
                    print(f"  - {pid} -> Playlist bulunamadı!")
            except:
                print(f"  - {pid} -> ObjectId çevirme hatası!")
    
except Exception as e:
    print(f"Hata: {e}")
finally:
    # Bağlantıyı kapat
    if 'client' in locals():
        client.close() 