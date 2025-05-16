#!/usr/bin/env python3
"""
Bu script tüm playlistlerin medya sayılarını günceller.
"""
from app import create_app
from app.models.playlist import Playlist
from app.models.playlist_media import PlaylistMedia
from app import mongo
from bson.objectid import ObjectId

app = create_app()

with app.app_context():
    print("TÜM PLAYLIST MEDYA SAYILARI GÜNCELLENİYOR...")
    
    try:
        # Tüm playlistleri getir
        playlists = list(Playlist.find_all())
        print(f"Toplam {len(playlists)} playlist bulundu")
        
        # Her playlist için gerçek medya sayısını kontrol et ve güncelle
        for playlist in playlists:
            playlist_id = playlist.id
            name = playlist.name
            old_count = playlist.media_count
            
            # Gerçek medya sayısını hesapla
            media_list = PlaylistMedia.find_by_playlist(playlist_id)
            real_count = len(media_list)
            
            print(f"Playlist: {name} (ID: {playlist_id})")
            print(f"  - Mevcut medya sayısı: {old_count}")
            print(f"  - Gerçek medya sayısı: {real_count}")
            
            # Eğer farklıysa veritabanını güncelle
            if old_count != real_count:
                print(f"  - Güncelleniyor...")
                
                # Hem nesneyi hem de veritabanını güncelle
                playlist.media_count = real_count
                
                # Doğrudan MongoDB'yi güncelle
                try:
                    result = mongo.db.playlists.update_one(
                        {"_id": ObjectId(playlist_id)},
                        {"$set": {"media_count": real_count}}
                    )
                    
                    if result.modified_count > 0:
                        print(f"  - Güncelleme başarılı!")
                    else:
                        print(f"  - Güncelleme başarısız. MongoDB cevabı: {result.raw_result}")
                        
                        # Alternatif ID formatı ile dene
                        try:
                            result2 = mongo.db.playlists.update_one(
                                {"_id": playlist_id},
                                {"$set": {"media_count": real_count}}
                            )
                            
                            if result2.modified_count > 0:
                                print(f"  - İkinci deneme başarılı!")
                            else:
                                print(f"  - İkinci deneme başarısız. MongoDB cevabı: {result2.raw_result}")
                        except Exception as e2:
                            print(f"  - İkinci deneme hatası: {str(e2)}")
                        
                except Exception as e:
                    print(f"  - MongoDB güncelleme hatası: {str(e)}")
            else:
                print(f"  - Medya sayısı doğru, güncelleme gerekmiyor")
                
            print("")  # Boş satır
        
        print("TÜM GÜNCELLEMELERİ BİTTİ")
        
    except Exception as e:
        import traceback
        print(f"Genel hata: {str(e)}")
        traceback.print_exc() 