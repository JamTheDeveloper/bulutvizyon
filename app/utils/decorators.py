from functools import wraps
from flask import session, redirect, url_for, flash, request
from app.models.user import User

def login_required(f):
    """Kullanıcı giriş kontrolü yapan decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Admin yetki kontrolü yapan decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
            
        user = User.find_by_id(session['user_id'])
        if not user or not user.is_admin():
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

def supervisor_required(f):
    """Supervisor yetki kontrolü yapan decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
            
        user = User.find_by_id(session['user_id'])
        if not user or not (user.is_supervisor() or user.is_admin()):
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    """Normal kullanıcı yetki kontrolü yapan decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
            
        user = User.find_by_id(session['user_id'])
        if not user:
            flash('Bu sayfaya erişim yetkiniz yok.', 'danger')
            return redirect(url_for('auth.login'))
            
        return f(*args, **kwargs)
    return decorated_function

def api_required(f):
    """API erişimi için yetki kontrolü yapan decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return {"error": "API anahtarı gerekli"}, 401
            
        user = User.find_by_api_key(api_key)
        if not user:
            return {"error": "Geçersiz API anahtarı"}, 401
            
        return f(*args, **kwargs)
    return decorated_function 