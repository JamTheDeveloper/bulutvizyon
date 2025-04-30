"""
MongoDB veritabanı ve koleksiyonlarını oluşturur
"""

from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from datetime import datetime
import sys
import os

def setup_database():
    # MongoDB bağlantısı
    client = MongoClient('mongodb://localhost:27017/')
    
    # Veritabanı oluştur
    db = client['bulutvizyondb']
    
    # Koleksiyonları oluştur
    collections = ['users', 'screens', 'media', 'screen_contents', 'logs']
    for collection in collections:
        if collection not in db.list_collection_names():
            print(f"'{collection}' koleksiyonu oluşturuluyor...")
            db.create_collection(collection)
    
    print("Veritabanı ve koleksiyonlar oluşturuldu.")
    return db

def create_admin(db, email, password, name):
    # Admin kullanıcısı var mı kontrol et
    users = db['users']
    existing_user = users.find_one({"email": email.lower()})
    
    if existing_user:
        print(f"Hata: {email} adresi zaten kullanımda.")
        return False
    
    # Admin kullanıcısı oluştur
    admin_user = {
        "email": email.lower(),
        "password_hash": generate_password_hash(password),
        "name": name,
        "role": "admin",
        "package": "enterprise",
        "status": "active",
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "last_login": None
    }
    
    result = users.insert_one(admin_user)
    
    if result.inserted_id:
        print(f"Admin kullanıcısı başarıyla oluşturuldu: {email}")
        return True
    else:
        print("Kullanıcı oluşturulurken bir hata oluştu.")
        return False

if __name__ == "__main__":
    # MongoDB veritabanı ve koleksiyonlarını oluştur
    db = setup_database()
    
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) != 4:
        print("Kullanım: python configure_db.py <email> <şifre> <ad>")
        print("Örnek: python configure_db.py admin@example.com 123456 'Admin Kullanıcı'")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3]
    
    # Admin kullanıcısı oluştur
    success = create_admin(db, email, password, name)
    sys.exit(0 if success else 1) 