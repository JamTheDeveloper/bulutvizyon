#!/usr/bin/env python3
"""
Bu script tüm playlistlerin medya sayılarını veritabanında günceller.
"""
import sys
import pymongo
from bson.objectid import ObjectId
from datetime import datetime

# MongoDB bağlantı bilgileri
MONGO_URI = "mongodb://elektrobil_admin:Eb%402254097%2A@localhost:27017/bulutvizyondb?authSource=admin"

def update_playlist_media_counts():
    print("Playlist medya sayıları güncelleniyor...")
    
    try:
        # MongoDB bağlantısı
        client = pymongo.MongoClient(MONGO_URI)
        db = client.bulutvizyondb
        
        # Tüm playlistleri getir
        playlists = list(db.playlists.find())
        print(f"Toplam {len(playlists)} playlist bulundu")
        
        updated_count = 0
        for playlist in playlists:
            playlist_id = playlist['_id']
            name = playlist.get('name', 'İsimsiz')
            
            # Veritabanındaki medya sayısı
            db_count = playlist.get('media_count', 0)
            
            # Gerçek medya sayısı
            query = {"$or": [
                {"playlist_id": playlist_id},
                {"playlist_id": str(playlist_id)}
            ]}
            real_count = db.playlist_media.count_documents(query)
            
            print(f"Playlist: {name} (ID: {playlist_id})")
            print(f"  - DB medya sayısı: {db_count}")
            print(f"  - Gerçek medya sayısı: {real_count}")
            
            # Eğer sayılar farklıysa güncelle
            if db_count != real_count:
                print(f"  - !!! Fark tespit edildi, güncelleniyor...")
                
                # Playlist'i güncelle
                result = db.playlists.update_one(
                    {"_id": playlist_id},
                    {"$set": {
                        "media_count": real_count,
                        "updated_at": datetime.utcnow()
                    }}
                )
                
                # Güncelleme sonucunu kontrol et
                if result.modified_count > 0:
                    print(f"  - Güncelleme BAŞARILI")
                    updated_count += 1
                else:
                    print(f"  - Güncelleme BAŞARISIZ: {result.raw_result}")
            else:
                print(f"  - Sayı doğru, güncelleme gerekmiyor")
            
            print()  # Boş satır
        
        print(f"İşlem tamamlandı. {updated_count}/{len(playlists)} playlist güncellendi.")
        
    except Exception as e:
        import traceback
        print(f"HATA: {str(e)}")
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("PLAYLIST MEDYA SAYILARI DÜZELTME ARACI")
    print("======================================")
    
    success = update_playlist_media_counts()
    
    if success:
        print("İşlem başarıyla tamamlandı.")
        sys.exit(0)
    else:
        print("İşlem sırasında hatalar oluştu.")
        sys.exit(1) 