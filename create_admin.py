from flask import Flask
from app import create_app
from app.models.user import User
import sys

def create_admin_user(email, password, name):
    """Admin kullanıcısı oluşturur"""
    # Uygulama bağlamını oluştur
    app = create_app()
    
    with app.app_context():
        # E-posta zaten kullanılıyor mu kontrol et
        existing_user = User.find_by_email(email)
        if existing_user:
            print(f"Hata: {email} adresi zaten kullanımda.")
            return False
        
        # Admin kullanıcısı oluştur
        user = User.create(
            email=email,
            password=password,
            name=name,
            role=User.ROLE_ADMIN,
            status=User.STATUS_ACTIVE,
            package=User.PACKAGE_ENTERPRISE
        )
        
        if user:
            print(f"Admin kullanıcısı başarıyla oluşturuldu: {email}")
            return True
        else:
            print("Kullanıcı oluşturulurken bir hata oluştu.")
            return False

if __name__ == "__main__":
    # Komut satırı argümanlarını kontrol et
    if len(sys.argv) != 4:
        print("Kullanım: python create_admin.py <email> <şifre> <ad>")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    name = sys.argv[3]
    
    # Admin kullanıcısı oluştur
    success = create_admin_user(email, password, name)
    sys.exit(0 if success else 1) 