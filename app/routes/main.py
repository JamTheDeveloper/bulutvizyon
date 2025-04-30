from flask import Blueprint, render_template, redirect, url_for, current_app, send_from_directory
from app.models.screen import Screen
import os

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """
    Ana sayfa
    """
    return redirect(url_for('auth.login'))

@main_bp.route('/media/<filename>')
def media_file(filename):
    """
    Medya dosyalarını sunar
    """
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main_bp.route('/viewer/<api_key>')
def viewer(api_key):
    """
    Ekran görüntüleyici
    """
    screen = Screen.find_by_api_key(api_key)
    if not screen:
        return render_template('errors/404.html'), 404
        
    return render_template('viewer.html', screen=screen) 