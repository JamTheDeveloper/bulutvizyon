#!/usr/bin/env python3
import os
import pymongo
from dotenv import load_dotenv

# .env dosyasından çevre değişkenlerini yükle
load_dotenv()

# MongoDB bağlantı bilgilerini al
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/bulutvizyonDB")

try:
    # MongoDB'ye bağlan
    client = pymongo.MongoClient(mongo_uri)
    db = client.get_database()
    
    # Tüm koleksiyonları listele
    print("Mevcut koleksiyonlar:")
    collections = db.list_collection_names()
    for collection in collections:
        print(f"- {collection}")
        
        # Her koleksiyondaki belge sayısını yazdır
        count = db[collection].count_documents({})
        print(f"  Belge sayısı: {count}")
        
        # İlk belgeyi göster (eğer varsa)
        if count > 0:
            print(f"  İlk belge örneği:")
            first_doc = db[collection].find_one()
            for key, value in first_doc.items():
                print(f"    {key}: {value}")
            
            # playlist_id alanını kontrol et
            if "playlist_id" in first_doc:
                print(f"  playlist_id değeri mevcut: {first_doc['playlist_id']}")
            else:
                print(f"  playlist_id alanı bu belgede bulunamadı")
    
    print("\nBağlantı başarılı!")
    
except Exception as e:
    print(f"Hata: {e}")
finally:
    # Bağlantıyı kapat
    if 'client' in locals():
        client.close() 