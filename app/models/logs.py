import datetime
from bson import ObjectId
from app import mongo

class Log:
    """Log model sınıfı"""
    
    # Log Tipleri
    TYPE_LOGIN = "login"
    TYPE_LOGOUT = "logout"
    TYPE_PASSWORD_RESET = "password_reset"
    TYPE_USER_CREATE = "user_create"
    TYPE_USER_UPDATE = "user_update"
    TYPE_USER_DELETE = "user_delete"
    TYPE_SCREEN_CREATE = "screen_create"
    TYPE_SCREEN_UPDATE = "screen_update"
    TYPE_SCREEN_DELETE = "screen_delete"
    TYPE_MEDIA_UPLOAD = "media_upload"
    TYPE_MEDIA_UPDATE = "media_update"
    TYPE_MEDIA_DELETE = "media_delete"
    TYPE_MEDIA_APPROVE = "media_approve"
    TYPE_MEDIA_REJECT = "media_reject"
    TYPE_SCREEN_CONNECT = "screen_connect"
    TYPE_ERROR = "error"
    
    # Content logs
    TYPE_CONTENT_ADD = "content_add"
    TYPE_CONTENT_REMOVE = "content_remove"
    TYPE_CONTENT_REORDER = "content_reorder"
    
    # Library actions
    TYPE_LIBRARY_USE = "library_use"
    
    # Özel log tipleri
    TYPE_MEDIA_MAKE_PUBLIC = 'media_make_public'
    TYPE_MEDIA_MAKE_PRIVATE = 'media_make_private'
    TYPE_MEDIA_ASSIGN_TO_USER = 'media_assign_to_user'
    TYPE_MEDIA_CREATE = 'media_create'
    
    def __init__(self, action, user_id=None, ip_address=None, details=None, timestamp=None):
        self.action = action
        self.user_id = user_id
        self.ip_address = ip_address
        self.details = details or {}
        self.timestamp = timestamp or datetime.datetime.utcnow()
        
    @staticmethod
    def get_collection():
        """MongoDB koleksiyonuna erişim sağlar"""
        return mongo.db.logs
    
    @classmethod
    def find_by_id(cls, log_id):
        """ID'ye göre log bulma"""
        log_data = cls.get_collection().find_one({"_id": ObjectId(log_id)})
        return cls.from_dict(log_data) if log_data else None
    
    @classmethod
    def find_by_user_id(cls, user_id, limit=100):
        """Kullanıcı ID'sine göre logları bulma"""
        logs = []
        for log_data in cls.get_collection().find({"user_id": user_id}).sort("timestamp", -1).limit(limit):
            logs.append(cls.from_dict(log_data))
        return logs
    
    @classmethod
    def find_by_action(cls, action, limit=100):
        """Aksiyon tipine göre logları bulma"""
        logs = []
        for log_data in cls.get_collection().find({"action": action}).sort("timestamp", -1).limit(limit):
            logs.append(cls.from_dict(log_data))
        return logs
    
    @classmethod
    def find_latest(cls, limit=100):
        """En son logları getir"""
        logs = []
        for log_data in cls.get_collection().find().sort("timestamp", -1).limit(limit):
            logs.append(cls.from_dict(log_data))
        return logs
    
    @classmethod
    def find_errors(cls, limit=100):
        """Hata loglarını getir"""
        logs = []
        for log_data in cls.get_collection().find({"action": cls.TYPE_ERROR}).sort("timestamp", -1).limit(limit):
            logs.append(cls.from_dict(log_data))
        return logs
    
    @classmethod
    def find_media_logs(cls, media_id, limit=100):
        """Medya ile ilgili logları getir"""
        logs = []
        for log_data in cls.get_collection().find({"details.media_id": media_id}).sort("timestamp", -1).limit(limit):
            logs.append(cls.from_dict(log_data))
        return logs
    
    @classmethod
    def find_screen_logs(cls, screen_id, limit=100):
        """Ekran ile ilgili logları getir"""
        logs = []
        for log_data in cls.get_collection().find({"details.screen_id": screen_id}).sort("timestamp", -1).limit(limit):
            logs.append(cls.from_dict(log_data))
        return logs
    
    @classmethod
    def from_dict(cls, log_dict):
        """Dictionary'den log nesnesi oluşturur"""
        if not log_dict:
            return None
            
        log = cls(
            action=log_dict.get('action'),
            user_id=log_dict.get('user_id'),
            ip_address=log_dict.get('ip_address'),
            details=log_dict.get('details', {}),
            timestamp=log_dict.get('timestamp')
        )
        log.id = str(log_dict.get('_id')) if '_id' in log_dict else None
        return log
    
    def to_dict(self):
        """Log nesnesini dictionary'ye dönüştürür"""
        # ObjectId'leri string'e dönüştür
        details_dict = {}
        if self.details:
            for key, value in self.details.items():
                if isinstance(value, ObjectId):
                    details_dict[key] = str(value)
                else:
                    details_dict[key] = value
                    
        log_dict = {
            "action": self.action,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "details": details_dict,
            "timestamp": self.timestamp
        }
        
        # None değerlerini filtreleme
        return {k: v for k, v in log_dict.items() if v is not None}
    
    def save(self):
        """Logu veritabanına kaydeder"""
        log_dict = self.to_dict()
        
        if hasattr(self, 'id') and self.id:
            # Güncelleme
            self.get_collection().update_one(
                {"_id": ObjectId(self.id)},
                {"$set": log_dict}
            )
            return self.id
        else:
            # Yeni log oluşturma
            result = self.get_collection().insert_one(log_dict)
            self.id = str(result.inserted_id)
            return self.id
            
    @classmethod
    def log_action(cls, action, user_id=None, ip_address=None, details=None):
        """Yeni bir log kaydı oluşturur ve kaydeder"""
        log = cls(
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            details=details
        )
        log.save()
        return log 