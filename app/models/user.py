"""
Kullanıcı Modeli: Kullanıcı hesap bilgilerini ve yetkilerini yönetir
"""
import uuid
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from app import mongo
import os
from pymongo import MongoClient
from urllib.parse import quote_plus

class User(UserMixin):
    """Kullanıcı modeli sınıfı"""
    
    # Kullanıcı rolleri
    ROLE_ADMIN = 'admin'
    ROLE_SUPERVISOR = 'supervisor'
    ROLE_USER = 'user'
    
    # Kullanıcı durumları
    STATUS_ACTIVE = 'active'
    STATUS_INACTIVE = 'inactive'
    STATUS_PENDING = 'pending'
    
    # Paket tipleri
    PACKAGE_STANDARD = 'standard'
    PACKAGE_PRO = 'pro'
    PACKAGE_ENTERPRISE = 'enterprise'
    
    # Paketlerin izin verdiği ekran sayıları
    PACKAGE_LIMITS = {
        PACKAGE_STANDARD: 3,
        PACKAGE_PRO: 10,
        PACKAGE_ENTERPRISE: 999  # Pratik olarak sınırsız
    }
    
    @classmethod
    def create(cls, email, password, name, role=ROLE_USER, 
               package=PACKAGE_STANDARD, status=STATUS_ACTIVE,
               is_nobetmatik_pro=False, terminal_no=None, business_name=None):
        """Yeni kullanıcı oluştur"""
        user_data = {
            "email": email.lower(),
            "password_hash": generate_password_hash(password),
            "name": name,
            "role": role,
            "package": package,
            "status": status,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "last_login": None,
            "is_nobetmatik_pro": is_nobetmatik_pro,
            "terminal_no": terminal_no,
            "business_name": business_name
        }
        
        result = mongo.db.users.insert_one(user_data)
        user_data['_id'] = result.inserted_id
        
        return cls(**user_data)
    
    @classmethod
    def find_by_id(cls, user_id):
        """ID'ye göre kullanıcı bulma"""
        try:
            # Konfigürasyon değerlerini al
            mongo_user = os.environ.get('MONGODB_USERNAME', 'elektrobil_admin')
            mongo_pass = os.environ.get('MONGODB_PASSWORD', 'Eb@2254097*')
            mongo_host = os.environ.get('MONGODB_HOST', 'localhost')
            mongo_port = os.environ.get('MONGODB_PORT', '27017')
            mongo_db = os.environ.get('MONGO_DB', 'bulutvizyondb')
            
            encoded_password = quote_plus(mongo_pass)
            
            # MongoDB bağlantısı oluştur
            mongo_uri = f"mongodb://{mongo_user}:{encoded_password}@{mongo_host}:{mongo_port}/{mongo_db}?authSource=admin"
            client = MongoClient(mongo_uri)
            db = client[mongo_db]
            
            # Eğer string olarak geldiyse ObjectId'ye çevir
            if isinstance(user_id, str):
                try:
                    obj_id = ObjectId(user_id)
                except Exception as e:
                    print(f"ObjectId dönüşüm hatası: {str(e)}")
                    return None
            else:
                obj_id = user_id
            
            # Kullanıcıyı bul
            user_data = db.users.find_one({"_id": obj_id})
            
            if not user_data:
                print(f"Kullanıcı bulunamadı: {user_id}")
                return None
                
            return cls(**user_data)
        except Exception as e:
            print(f"Kullanıcı bulunamadı. Hata: {str(e)}, ID: {user_id}")
            return None
    
    @classmethod
    def find_by_email(cls, email):
        """Email adresine göre kullanıcı bulma"""
        user_data = mongo.db.users.find_one({"email": email})
        if user_data:
            return cls(**user_data)
        return None
    
    @classmethod
    def find_by_reset_token(cls, token):
        """Şifre sıfırlama token'ına göre kullanıcı bulma"""
        user_data = mongo.db.users.find_one({"reset_token": token})
        if user_data:
            return cls(**user_data)
        return None
    
    @classmethod
    def find_all(cls, role=None, status=None):
        """Tüm kullanıcıları veya belirli rol/duruma göre bul"""
        query = {}
        if role:
            query["role"] = role
        if status:
            query["status"] = status
            
        users = []
        for user_data in mongo.db.users.find(query):
            users.append(cls(**user_data))
        return users
    
    @classmethod
    def generate_reset_token(cls):
        """Şifre sıfırlama tokeni oluştur"""
        return str(uuid.uuid4())
    
    def __init__(self, _id, email, password_hash, name, role, 
               package=PACKAGE_STANDARD, status=STATUS_ACTIVE, 
               created_at=None, updated_at=None, last_login=None, 
               reset_token=None, reset_token_expires=None, supervisor_id=None,
               is_nobetmatik_pro=False, terminal_no=None, business_name=None, **kwargs):
        """Yeni bir kullanıcı nesnesi başlat"""
        self.id = str(_id)
        self.email = email
        self.password_hash = password_hash
        self.name = name
        self.role = role
        self.package = package
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_login = last_login
        self.reset_token = reset_token
        self.reset_token_expires = reset_token_expires
        self.supervisor_id = supervisor_id
        self.is_nobetmatik_pro = is_nobetmatik_pro
        self.terminal_no = terminal_no
        self.business_name = business_name
        
        # Ekstra özellikleri de ekle
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def update(self, **kwargs):
        """Kullanıcı bilgilerini güncelle"""
        updates = {"updated_at": datetime.now()}
        
        # Güncellenebilir alanlar
        updatable_fields = ['name', 'role', 'email', 'status', 'package', 'supervisor_id', 
                            'is_nobetmatik_pro', 'terminal_no', 'business_name']
        
        for field in updatable_fields:
            if field in kwargs:
                updates[field] = kwargs[field]
        
        # Şifre ayrı işlenir
        if 'password' in kwargs:
            updates['password_hash'] = generate_password_hash(kwargs['password'])
        
        result = mongo.db.users.update_one(
            {"_id": ObjectId(self.id)}, 
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    def delete(self):
        """Kullanıcıyı sil"""
        mongo.db.users.delete_one({"_id": ObjectId(self.id)})
        return True
    
    def verify_password(self, password):
        """Şifreyi doğrula"""
        return check_password_hash(self.password_hash, password)
    
    def set_password(self, password):
        """Şifreyi güncelle"""
        return self.update(password=password)
    
    def update_last_login(self):
        """Son giriş zamanını güncelle"""
        return self.update(last_login=datetime.now())
    
    def get_id(self):
        """UserMixin için gerekli ID döndürme fonksiyonu"""
        return self.id
    
    def is_admin(self):
        """Kullanıcının admin olup olmadığını kontrol et"""
        return self.role == self.ROLE_ADMIN
    
    def is_supervisor(self):
        """Kullanıcının denetmen olup olmadığını kontrol et"""
        return self.role == self.ROLE_SUPERVISOR
    
    def is_active(self):
        """UserMixin için gerekli, kullanıcının aktif olup olmadığını kontrol et"""
        return self.status == self.STATUS_ACTIVE
    
    def get_allowed_screen_count(self):
        """Kullanıcının paketine göre oluşturabileceği maksimum ekran sayısı"""
        return self.PACKAGE_LIMITS.get(self.package, 0)
    
    def set_reset_token(self, expires_in=3600):
        """Şifre sıfırlama tokeni oluştur ve kaydet"""
        from datetime import timedelta
        reset_token = self.generate_reset_token()
        reset_token_expires = datetime.now() + timedelta(seconds=expires_in)
        
        self.update(
            reset_token=reset_token,
            reset_token_expires=reset_token_expires
        )
        
        return reset_token
    
    def verify_reset_token(self, token):
        """Şifre sıfırlama tokenini doğrula"""
        if not self.reset_token or self.reset_token != token:
            return False
        
        if not self.reset_token_expires or datetime.now() > self.reset_token_expires:
            return False
            
        return True
    
    def to_dict(self):
        """Kullanıcı bilgilerini sözlük olarak döndür"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "role": self.role,
            "package": self.package,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login
        }
    
    def has_supervisor(self):
        """Kullanıcıya atanmış bir supervisor var mı kontrol et"""
        return self.supervisor_id is not None 