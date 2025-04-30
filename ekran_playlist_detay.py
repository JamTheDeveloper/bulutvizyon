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
    
    print("==== EKRAN VE PLAYLIST İLİŞKİLERİ ====\n")
    
    # Tüm ekranları al
    screens = db.screens.find({})
    
    # Ekran sayısını kontrol et
    screen_count = db.screens.count_documents({})
    if screen_count == 0:
        print("Veritabanında ekran bulunmamaktadır.")
    
    for screen in screens:
        print(f"EKRAN: {screen.get('name', 'İsimsiz')} (ID: {screen['_id']})")
        print(f"  Durum: {screen.get('status', 'Belirtilmemiş')}")
        
        # Bu ekrana atanmış playlist'leri bul
        screen_playlists = db.screen_playlists.find({"screen_id": str(screen["_id"])})
        
        playlist_count = db.screen_playlists.count_documents({"screen_id": str(screen["_id"])})
        if playlist_count == 0:
            print("  Bu ekrana henüz playlist atanmamış.")
        else:
            for sp in screen_playlists:
                playlist_id = sp.get("playlist_id")
                
                # Playlist detaylarını al
                try:
                    playlist = db.playlists.find_one({"_id": ObjectId(playlist_id)})
                except:
                    print(f"  Hatalı playlist ID: {playlist_id}")
                    continue
                
                if playlist:
                    print(f"\n  PLAYLIST: {playlist.get('name', 'İsimsiz')} (ID: {playlist['_id']})")
                    print(f"    Açıklama: {playlist.get('description', 'Açıklama yok')}")
                    print(f"    Durum: {playlist.get('status', 'Belirtilmemiş')}")
                    print(f"    Medya Sayısı: {playlist.get('media_count', 0)}")
                    
                    # Playlist ID stringini kullanarak medya verilerini sorgula (diğer koleksiyondan farklı olabilir)
                    playlist_id_str = str(playlist["_id"])
                    
                    # Önce bu formatta deneyelim
                    playlist_media_items = list(db.playlist_media.find({"playlist_id": playlist_id_str}))
                    
                    # İlk format sonuç vermediyse diğer formatı deneyelim
                    if not playlist_media_items:
                        print(f"    Medya ilişkisi bulunamadı. Alternatif ID formatları deneniyor...")
                        # Doğrudan ObjectId ile deneyelim
                        playlist_media_items = list(db.playlist_media.find({"playlist_id": playlist_id}))
                    
                    media_count = len(playlist_media_items)
                    if media_count == 0:
                        print("    Bu playlist'te henüz medya dosyası bulunamadı.")
                        # Medya dosyalarını doğrudan listeyelim
                        print("\n    Sistemdeki MEDYA DOSYALARI (playlist'e atanmamış):")
                        media_items = db.media.find().limit(5)
                        for media in media_items:
                            print(f"      - {media.get('title', 'İsimsiz Dosya')} (ID: {media['_id']})")
                            print(f"        Tür: {media.get('file_type', 'Belirtilmemiş')}")
                            print(f"        Dosya: {media.get('filename', 'Belirtilmemiş')}")
                            print(f"        Gösterim Süresi: {media.get('display_time', 'Belirtilmemiş')} saniye")
                    else:
                        print(f"\n    MEDYA DOSYALARI ({media_count} adet):")
                        for item in playlist_media_items:
                            media_id = item.get("media_id")
                            
                            try:
                                # Medya detaylarını al
                                media = db.media.find_one({"_id": ObjectId(media_id)})
                            except:
                                print(f"      - Hatalı medya ID: {media_id}")
                                continue
                            
                            if media:
                                print(f"      - {media.get('title', 'İsimsiz Dosya')} (ID: {media['_id']})")
                                print(f"        Tür: {media.get('file_type', 'Belirtilmemiş')}")
                                print(f"        Dosya: {media.get('filename', 'Belirtilmemiş')}")
                                print(f"        Gösterim Süresi: {item.get('display_time', media.get('display_time', 'Belirtilmemiş'))} saniye")
                                print(f"        Sıra: {item.get('order', 0)}")
                else:
                    print(f"\n  Playlist bulunamadı (ID: {playlist_id})")
                    
        print("\n" + "-"*50 + "\n")
    
    # Playlist'ler ve medya ilişkileri hakkında genel bilgiler
    print("\n==== ÖZET BİLGİLER ====")
    print(f"Toplam Ekran Sayısı: {db.screens.count_documents({})}")
    print(f"Toplam Playlist Sayısı: {db.playlists.count_documents({})}")
    print(f"Toplam Medya Sayısı: {db.media.count_documents({})}")
    print(f"Ekran-Playlist İlişki Sayısı: {db.screen_playlists.count_documents({})}")
    print(f"Playlist-Medya İlişki Sayısı: {db.playlist_media.count_documents({})}")
    
except Exception as e:
    print(f"Hata: {e}")
finally:
    # Bağlantıyı kapat
    if 'client' in locals():
        client.close() 