from flask import Blueprint, request, jsonify, current_app, session
from app.models.screen import Screen
from app.models.screen_content import ScreenContent
from app.models.media import Media
from app.models.playlist import Playlist
from app.models.logs import Log
import datetime
import json
import traceback

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/screen/<api_key>', methods=['GET'])
def get_screen_content(api_key):
    """
    Ekran içeriklerini API ile getir
    """
    try:
        print(f"DEBUG - API isteği başladı: /screen/{api_key}")
        
        screen = Screen.find_by_api_key(api_key)
        
        if not screen:
            print(f"DEBUG - Geçersiz API anahtarı: {api_key}")
            return jsonify({'error': 'Geçersiz API anahtarı'}), 401
        
        print(f"DEBUG - Ekran bulundu: {screen.id}")
        
        # Ekran durumunu kontrol et
        if screen.status != Screen.STATUS_ACTIVE:
            print(f"DEBUG - Ekran aktif değil: {screen.status}")
            return jsonify({'error': 'Bu ekran aktif değil'}), 403
        
        # Ekranın son etkinlik zamanını güncelle
        screen.update_last_active()
        
        # Ekrana ait içerikleri getir
        content_list = ScreenContent.find_by_screen_id(screen.id)
        print(f"DEBUG - Ekran içerik sayısı: {len(content_list)}")
        
        # İçerik listesini oluştur
        items = []
        for index, content in enumerate(content_list):
            try:
                print(f"DEBUG - İçerik işleniyor: {index}, ID: {content.get('_id')}, Media ID: {content.get('media_id')}")
                
                media = Media.find_by_id(content.get('media_id'))
                
                if not media:
                    print(f"DEBUG - Media bulunamadı: {content.get('media_id')}")
                    continue
                    
                if media.get('status') != Media.STATUS_ACTIVE:
                    print(f"DEBUG - Media aktif değil: {media.get('status')}")
                    continue
                
                display_time = content.get('display_time') or media.get('display_time', 10)
                
                # İçerik bilgileri
                item = {
                    'id': str(content.get('_id')),
                    'media': {
                        'id': str(media.get('_id')),
                        'title': media.get('title', ''),
                        'description': media.get('description', ''),
                        'file_type': media.get('file_type', ''),
                        'width': media.get('width', 0),
                        'height': media.get('height', 0),
                        'duration': media.get('duration', 0),
                        'file_url': f"/uploads/{media.get('filename', '')}"
                    },
                    'display_time': display_time,
                    'order': content.get('order', index)
                }
                
                items.append(item)
                print(f"DEBUG - Eklenen içerik: ID: {item['id']}, Media: {item['media']['title']}, Dosya tipi: {item['media']['file_type']}, URL: {item['media']['file_url']}, Sıra: {item['order']}")
            except Exception as e:
                print(f"DEBUG - İçerik işleme hatası: {str(e)}")
                print(traceback.format_exc())
        
        # İçerikler sıraya göre sıralanıyor
        items.sort(key=lambda x: x['order'])
        
        # Medya görüntülenme sayılarını artır (async olarak)
        if items:
            media_ids = [content.get('media_id') for content in content_list]
            Media.increment_views(media_ids)
        
        # Ekran bilgileri ve içerik listesi
        response = {
            'success': True,
            'screen': {
                'id': screen.id,
                'name': screen.name,
                'orientation': screen.orientation,
                'resolution': screen.resolution,
                'refresh_rate': screen.refresh_rate,
                'show_clock': screen.show_clock
            },
            'content': items,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        
        print(f"DEBUG - API yanıtı: İçerik sayısı: {len(items)}")
        
        return jsonify(response)
    except Exception as e:
        print(f"DEBUG - API genel hatası: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/screen/<api_key>/status', methods=['POST'])
def update_screen_status(api_key):
    """
    Ekran durumunu güncellemek için kullanılır (Raspberry Pi'dan)
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz veri'}), 400
        
        screen = Screen.find_by_api_key(api_key)
        if not screen:
            return jsonify({'success': False, 'message': 'Ekran bulunamadı'}), 404
        
        # Ekran son aktivite zamanını ve varsa diğer durum bilgilerini güncelle
        update_data = {
            'last_active': datetime.datetime.utcnow()
        }
        
        # Ekran sıcaklığı, bellek durumu vb. bilgiler varsa ekle
        if 'temperature' in data:
            update_data['temperature'] = data['temperature']
        
        if 'memory_usage' in data:
            update_data['memory_usage'] = data['memory_usage']
        
        if 'cpu_usage' in data:
            update_data['cpu_usage'] = data['cpu_usage']
        
        if 'current_media' in data:
            update_data['current_media'] = data['current_media']
        
        # Ekranı güncelle
        Screen.update(screen['_id'], update_data)
        
        return jsonify({
            'success': True,
            'message': 'Ekran durumu güncellendi'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/screen/preview/<api_key>', methods=['GET'])
def screen_preview(api_key):
    """
    Ekran önizleme için HTML içeriği döndürür
    """
    try:
        screen = Screen.find_by_api_key(api_key)
        if not screen:
            return "Ekran bulunamadı", 404
        
        # Ekran içeriklerini al
        content_list = ScreenContent.find_by_screen_id(screen['_id'])
        
        # Her içerik için medya detaylarını ekle
        content_with_media = []
        for content in content_list:
            media = Media.find_by_id(content['media_id'])
            if media and media.get('status') == 'active':
                content_data = {
                    'id': str(content['_id']),
                    'display_time': content.get('display_time', media.get('display_time', 10)),
                    'order': content.get('order', 0),
                    'media': {
                        'id': str(media['_id']),
                        'title': media.get('title', ''),
                        'file_type': media.get('file_type', ''),
                        'file_url': f"/uploads/{media.get('filename', '')}",
                        'display_time': media.get('display_time', 10)
                    }
                }
                content_with_media.append(content_data)
        
        # İçerikleri sıraya göre sırala
        content_with_media.sort(key=lambda x: x['order'])
        
        # Ekran ve içerik bilgilerini HTML template'e gönder
        screen_data = {
            'id': str(screen['_id']),
            'name': screen.get('name', ''),
            'orientation': screen.get('orientation', 'horizontal'),
            'resolution': screen.get('resolution', '1920x1080'),
            'refresh_rate': screen.get('refresh_rate', 15),
            'show_clock': screen.get('show_clock', True),
            'api_key': api_key
        }
        
        # JSON formatında içerik bilgilerini döndür
        return jsonify({
            'screen': screen_data,
            'content': content_with_media
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/health', methods=['GET'])
def health_check():
    """API sağlık kontrolü"""
    return jsonify({"status": "healthy", "time": datetime.datetime.utcnow().isoformat()})

@bp.route('/media/<media_id>/info', methods=['GET'])
def media_info(media_id):
    """Medya bilgisi API'si"""
    media = Media.find_by_id(media_id)
    
    if not media:
        return jsonify({"error": "Medya bulunamadı."}), 404
        
    if media.get('status') != Media.STATUS_ACTIVE:
        return jsonify({"error": "Medya aktif değil."}), 403
    
    media_info = {
        "id": str(media['_id']),
        "title": media.get('title', ''),
        "description": media.get('description', ''),
        "file_type": media.get('file_type', ''),
        "width": media.get('width', 0),
        "height": media.get('height', 0),
        "duration": media.get('duration', 0),
        "display_time": media.get('display_time', 10),
        "file_url": f"/uploads/{media.get('filename', '')}",
        "orientation": media.get('orientation', 'horizontal'),
        "category": media.get('category', ''),
        "public": media.get('is_public', False),
        "created_at": media.get('created_at', '').isoformat() if media.get('created_at') else None
    }
    
    return jsonify(media_info)

@bp.route('/player/health', methods=['GET'])
def player_health():
    """Player sistemi sağlık kontrolü API'si"""
    return jsonify({
        "status": "ok", 
        "version": "1.0",
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

@bp.route('/player/<api_key>/healthcheck', methods=['GET', 'POST'])
def player_healthcheck(api_key):
    """
    Player sağlık kontrolü
    """
    screen = Screen.find_by_api_key(api_key)
    
    if not screen:
        return jsonify({'error': 'Geçersiz API anahtarı'}), 401
    
    # Ekran durumunu güncelle
    screen.update_last_active()
    
    # İstek gövdesinden bilgileri al (eğer POST ise)
    player_info = {}
    if request.method == 'POST':
        data = request.get_json()
        if data:
            player_info = {
                'ip': data.get('ip', request.remote_addr),
                'version': data.get('version', 'unknown'),
                'device_id': data.get('device_id', 'unknown'),
                'storage': data.get('storage', {}),
                'memory': data.get('memory', {}),
                'cpu': data.get('cpu', {})
            }
    
    # Yanıt
    response = {
        'status': 'ok',
        'screen_id': screen.id,
        'screen_name': screen.name,
        'timestamp': datetime.datetime.now().isoformat()
    }
    
    return jsonify(response)

@bp.route('/player/content/<api_key>', methods=['GET'])
def get_player_content(api_key):
    """
    Player için içerik getir
    """
    screen = Screen.find_by_api_key(api_key)
    
    if not screen:
        return jsonify({'error': 'Geçersiz API anahtarı'}), 401
    
    # Ekran durumunu kontrol et
    if screen.status != Screen.STATUS_ACTIVE:
        return jsonify({'error': 'Bu ekran aktif değil'}), 403
    
    # Ekranın son etkinlik zamanını güncelle
    screen.update_last_active()
    
    # Ekrana ait içerikleri getir
    content_list = ScreenContent.find_by_screen_id(screen.id)
    
    # İçerik listesini oluştur
    items = []
    for content in content_list:
        media = Media.find_by_id(content.get('media_id'))
        
        if not media or media.get('status') != Media.STATUS_ACTIVE:
            continue
        
        display_time = content.get('display_time') or media.get('display_time', 10)
        
        # İçerik bilgileri
        item = {
            'id': str(content.get('_id')),
            'title': media.get('title', ''),
            'description': media.get('description', ''),
            'file_type': media.get('file_type', ''),
            'width': media.get('width', 0),
            'height': media.get('height', 0),
            'duration': media.get('duration', 0),
            'display_time': display_time,
            'file_url': f"/uploads/{media.get('filename', '')}",
            'orientation': media.get('orientation', 'horizontal'),
            'category': media.get('category', ''),
            'public': media.get('public', False),
            'created_at': media.get('created_at')
        }
        
        items.append(item)
    
    # Medya görüntülenme sayılarını artır (async olarak)
    if items:
        media_ids = [content.get('media_id') for content in content_list]
        Media.increment_views(media_ids)
    
    # Ekran bilgileri ve içerik listesi
    response = {
        'screen': {
            'id': screen.id,
            'name': screen.name,
            'orientation': screen.orientation,
            'resolution': screen.resolution,
            'refresh_rate': screen.refresh_rate,
            'show_clock': screen.show_clock
        },
        'items': items
    }
    
    return jsonify(response)

@bp.route('/screen/report_offline', methods=['POST'])
def report_offline_period():
    """
    Ekranın offline kalma süresini raporlamak için kullanılır
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Geçersiz veri'}), 400
        
        api_key = data.get('api_key')
        if not api_key:
            return jsonify({'success': False, 'message': 'API anahtarı gerekli'}), 400
            
        offline_period = data.get('offline_period')
        if not offline_period:
            return jsonify({'success': False, 'message': 'Offline dönem bilgisi gerekli'}), 400
        
        # API anahtarı ile ekranı bul
        screen = Screen.find_by_api_key(api_key)
        if not screen:
            return jsonify({'success': False, 'message': 'Ekran bulunamadı'}), 404
        
        # Offline dönemi ekle
        result = screen.add_offline_period(offline_period)
        
        if result:
            # Log ekle
            Log.create({
                'action': 'offline_period_reported',
                'user_id': None,
                'screen_id': screen.id,
                'details': {
                    'offline_period': offline_period
                }
            })
            
            return jsonify({
                'success': True,
                'message': 'Offline süre başarıyla kaydedildi'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Offline süre kaydedilemedi'
            }), 500
    except Exception as e:
        print(f"Offline süre raporlama hatası: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500

@bp.route('/user/playlists', methods=['GET'])
def get_user_playlists():
    """
    Giriş yapmış kullanıcının playlistlerini getirir
    """
    try:
        # Kullanıcı giriş yapmış mı kontrol et
        if 'user_id' not in session:
            print(f"DEBUG - Playlist API: Oturum bulunamadı")
            return jsonify({'success': False, 'message': 'Oturum açmanız gerekiyor.'}), 401
            
        user_id = session['user_id']
        print(f"DEBUG - Playlist API: Kullanıcı ID: {user_id}")
        
        # Kullanıcının playlistlerini getir
        playlists = Playlist.find_by_user(user_id, status=Playlist.STATUS_ACTIVE)
        
        print(f"DEBUG - Playlist API: Bulunan playlist sayısı: {len(playlists)}")
        
        # API yanıtı için playlist verilerini formatla
        formatted_playlists = []
        for playlist in playlists:
            print(f"DEBUG - Playlist veri tipi: {type(playlist)}")
            try:
                playlist_data = {
                    'id': playlist.id if hasattr(playlist, 'id') else str(playlist.get('_id', '')),
                    'name': playlist.name if hasattr(playlist, 'name') else playlist.get('name', ''),
                    'description': playlist.description if hasattr(playlist, 'description') else playlist.get('description', ''),
                    'is_public': playlist.is_public if hasattr(playlist, 'is_public') else playlist.get('is_public', False),
                    'media_count': playlist.media_count if hasattr(playlist, 'media_count') else playlist.get('media_count', 0),
                }
                
                if hasattr(playlist, 'created_at') and playlist.created_at:
                    playlist_data['created_at'] = playlist.created_at.isoformat() if hasattr(playlist.created_at, 'isoformat') else playlist.created_at
                else:
                    created_at = playlist.get('created_at', '')
                    playlist_data['created_at'] = created_at.isoformat() if hasattr(created_at, 'isoformat') else created_at
                
                formatted_playlists.append(playlist_data)
                print(f"DEBUG - Eklenen playlist: {playlist_data['id']} - {playlist_data['name']}")
            except Exception as e:
                print(f"DEBUG - Playlist formatlarken hata: {str(e)}")
        
        print(f"DEBUG - Formatlanan playlist sayısı: {len(formatted_playlists)}")
        
        return jsonify({
            'success': True,
            'playlists': formatted_playlists
        })
    except Exception as e:
        print(f"DEBUG - Playlistleri getirme hatası: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)}), 500 