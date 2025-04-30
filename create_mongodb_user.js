// MongoDB Admin Kullanıcısı oluşturma
db = db.getSiblingDB('admin');

// Önce admin kullanıcısını oluştur
db.createUser({
  user: "elektrobil_admin",
  pwd: "Eb@2254097*",
  roles: [
    { role: "userAdminAnyDatabase", db: "admin" },
    { role: "readWriteAnyDatabase", db: "admin" },
    { role: "dbAdminAnyDatabase", db: "admin" }
  ]
});

// Şimdi bulutvizyondb için de kullanıcı oluştur
db = db.getSiblingDB('bulutvizyondb');
db.createUser({
  user: "elektrobil_admin",
  pwd: "Eb@2254097*",
  roles: [
    { role: "readWrite", db: "bulutvizyondb" },
    { role: "dbAdmin", db: "bulutvizyondb" }
  ]
}); 