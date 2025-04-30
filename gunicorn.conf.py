bind = "0.0.0.0:5006"
workers = 2
wsgi_app = "app:app"
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"
capture_output = True 
forwarded_allow_ips = "*"  # Tüm IP'lere izin ver
secure_scheme_headers = {
    'X-Forwarded-Proto': 'https',
    'X-Forwarded-Ssl': 'on',
    'X-Forwarded-For': 'remote_addr'
}
access_log_format = '%({X-Real-IP}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

logconfig_dict = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'errorlog': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': 'logs/error.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'accesslog': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': 'logs/access.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        }
    },
    'loggers': {
        'gunicorn.error': {
            'handlers': ['errorlog', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gunicorn.access': {
            'handlers': ['accesslog', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    }
} 