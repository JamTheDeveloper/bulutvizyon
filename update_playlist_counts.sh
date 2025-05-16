#!/bin/bash
# Playlist medya sayılarını güncelleyen script

echo "BulutVizyon Playlist Medya Sayıları Güncelleme Aracı"
echo "==================================================="
echo

# MongoDB kimlik bilgileri
DB_USER="elektrobil_admin"
DB_PASS="Eb@2254097*"
DB_HOST="localhost"
DB_PORT="27017"
DB_NAME="bulutvizyondb"
AUTH_DB="admin"

echo "MongoDB'ye bağlanılıyor..."

# Tüm playlist'leri çekme sorgusu
mongo_result=$(mongo --quiet --username "$DB_USER" --password "$DB_PASS" --host "$DB_HOST" --port "$DB_PORT" --authenticationDatabase "$AUTH_DB" "$DB_NAME" --eval '
// Playlist ve PlaylistMedia koleksiyonları üzerinde işlem yapacağız
var playlists = db.playlists.find().toArray();
print("Toplam " + playlists.length + " playlist bulundu");

var updated_count = 0;

for (var i = 0; i < playlists.length; i++) {
    var playlist = playlists[i];
    var playlist_id = playlist._id;
    var name = playlist.name || "İsimsiz";
    var db_count = playlist.media_count || 0;
    
    // Her iki ID formatı için sorgu yap (String ve ObjectId)
    var query = {
        "$or": [
            {"playlist_id": playlist_id},
            {"playlist_id": playlist_id.toString()}
        ]
    };
    
    var real_count = db.playlist_media.count(query);
    
    print("Playlist: " + name + " (ID: " + playlist_id + ")");
    print("  - DB medya sayısı: " + db_count);
    print("  - Gerçek medya sayısı: " + real_count);
    
    // Sayılar farklı mı?
    if (db_count !== real_count) {
        print("  - !!! Fark tespit edildi, güncelleniyor...");
        
        // Playlist güncellemesi
        var result = db.playlists.updateOne(
            {"_id": playlist_id},
            {"$set": {
                "media_count": real_count,
                "updated_at": new Date()
            }}
        );
        
        if (result.modifiedCount > 0) {
            print("  - Güncelleme BAŞARILI");
            updated_count++;
        } else {
            print("  - Güncelleme BAŞARISIZ");
        }
    } else {
        print("  - Sayı doğru, güncelleme gerekmiyor");
    }
    
    print("");
}

print("İşlem tamamlandı. " + updated_count + "/" + playlists.length + " playlist güncellendi");
')

# MongoDB sorgusu sonucunu yazdır
echo "$mongo_result"

echo
echo "İşlem tamamlandı." 