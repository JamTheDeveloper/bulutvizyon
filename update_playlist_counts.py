#!/usr/bin/env python3

from app import mongo, create_app
from app.models.playlist import Playlist
from bson.objectid import ObjectId
import traceback

app = create_app()

def update_playlist_counts():
    """Tüm playlistlerin medya sayılarını günceller"""
    print("Tüm playlistlerin medya sayıları güncelleniyor...")
    updated_count = 0
    total_media = 0
    
    try:
        # Tüm playlistleri getir
        all_playlists = list(mongo.db.playlists.find())
        print(f"Toplam {len(all_playlists)} playlist bulundu")
        
        # Her bir playlist için medya sayısını güncelle
        for playlist in all_playlists:
            playlist_id = playlist['_id']
            playlist_name = playlist.get('name', 'Bilinmeyen')
            
            # Medya sayısını al
            # Her iki formatı da arayalım
            query = {"$or": [{"playlist_id": playlist_id}, {"playlist_id": str(playlist_id)}]}
            new_count = mongo.db.playlist_media.count_documents(query)
            old_count = playlist.get('media_count', 0)
            
            # Medya sayısını güncelle
            if old_count != new_count:
                mongo.db.playlists.update_one(
                    {"_id": playlist_id},
                    {"$set": {"media_count": new_count}}
                )
                updated_count += 1
                print(f"Playlist {playlist_name} ({playlist_id}): {old_count} -> {new_count}")
            
            total_media += new_count
        
        print(f"Toplam {updated_count} playlist güncellendi. Toplam {total_media} medya içeriği.")
    
    except Exception as e:
        print(f"Playlist medya sayıları güncellenirken hata: {str(e)}")
        print(traceback.format_exc())
    
    return {
        'updated_playlist_count': updated_count,
        'total_media_count': total_media
    }

if __name__ == "__main__":
    with app.app_context():
        update_playlist_counts() 