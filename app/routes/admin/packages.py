from flask import render_template, request, redirect, url_for, flash, session
from app.models.package import Package
from app.models.logs import Log
from app.models.user import User
from app.utils.decorators import admin_required
from app.routes.admin import bp

@bp.route('/packages')
@admin_required
def packages():
    """Paket listesi sayfası"""
    packages = Package.find_all()
    
    # Her paketin kullanım sayısını hesapla
    for package in packages:
        user_count = 0
        # MongoDB sorgusu ile direkt sayma
        from app import mongo
        user_count = mongo.db.users.count_documents({"package": package.name})
        package.user_count = user_count
    
    return render_template('admin/packages.html', packages=packages)

@bp.route('/packages/create', methods=['GET', 'POST'])
@admin_required
def create_package():
    """Paket oluşturma sayfası"""
    if request.method == 'POST':
        # Form verilerini al
        name = request.form.get('name', '').strip().lower()
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '')
        screen_limit = request.form.get('screen_limit', '3')
        price = request.form.get('price', '0')
        
        # Zorunlu alanları kontrol et
        if not name or not display_name:
            flash('Paket adı ve görünür adı alanları zorunludur.', 'danger')
            return render_template('admin/create_package.html')
        
        # Aynı isimde paket var mı kontrol et
        existing_package = Package.find_by_name(name)
        if existing_package:
            flash('Bu isimde bir paket zaten mevcut.', 'danger')
            return render_template('admin/create_package.html')
        
        # Sayısal alanları dönüştür
        try:
            screen_limit = int(screen_limit)
            price = float(price)
        except ValueError:
            flash('Ekran limiti ve fiyat alanları sayısal olmalıdır.', 'danger')
            return render_template('admin/create_package.html')
        
        # Özellikleri al (dinamik alan)
        features = {}
        for key, value in request.form.items():
            if key.startswith('feature_key_') and value:
                index = key.split('_')[-1]
                feature_key = value
                feature_value = request.form.get(f'feature_value_{index}', '')
                features[feature_key] = feature_value
        
        # Paketi oluştur
        package = Package.create(
            name=name,
            display_name=display_name,
            description=description,
            screen_limit=screen_limit,
            price=price,
            features=features
        )
        
        # Log kaydı
        Log.log_action(
            action="package_create",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={
                "package_id": package.id,
                "name": name,
                "display_name": display_name
            }
        )
        
        flash('Paket başarıyla oluşturuldu.', 'success')
        return redirect(url_for('admin.packages'))
    
    return render_template('admin/create_package.html')

@bp.route('/packages/edit/<package_id>', methods=['GET', 'POST'])
@admin_required
def edit_package(package_id):
    """Paket düzenleme sayfası"""
    package = Package.find_by_id(package_id)
    if not package:
        flash('Paket bulunamadı.', 'danger')
        return redirect(url_for('admin.packages'))
    
    if request.method == 'POST':
        # Form verilerini al
        display_name = request.form.get('display_name', '').strip()
        description = request.form.get('description', '')
        screen_limit = request.form.get('screen_limit', '3')
        price = request.form.get('price', '0')
        is_active = 'is_active' in request.form
        
        # Zorunlu alanları kontrol et
        if not display_name:
            flash('Görünür adı alanı zorunludur.', 'danger')
            return render_template('admin/edit_package.html', package=package)
        
        # Sayısal alanları dönüştür
        try:
            screen_limit = int(screen_limit)
            price = float(price)
        except ValueError:
            flash('Ekran limiti ve fiyat alanları sayısal olmalıdır.', 'danger')
            return render_template('admin/edit_package.html', package=package)
        
        # Özellikleri al (dinamik alan)
        features = {}
        for key, value in request.form.items():
            if key.startswith('feature_key_') and value:
                index = key.split('_')[-1]
                feature_key = value
                feature_value = request.form.get(f'feature_value_{index}', '')
                features[feature_key] = feature_value
        
        # Paketi güncelle
        package.update(
            display_name=display_name,
            description=description,
            screen_limit=screen_limit,
            price=price,
            features=features,
            is_active=is_active
        )
        
        # Log kaydı
        Log.log_action(
            action="package_update",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={
                "package_id": package.id,
                "name": package.name,
                "display_name": display_name
            }
        )
        
        flash('Paket başarıyla güncellendi.', 'success')
        return redirect(url_for('admin.packages'))
    
    # Kullanıcı sayısını hesapla
    from app import mongo
    user_count = mongo.db.users.count_documents({"package": package.name})
    
    return render_template('admin/edit_package.html', package=package, user_count=user_count)

@bp.route('/packages/delete/<package_id>', methods=['POST'])
@admin_required
def delete_package(package_id):
    """Paket silme"""
    package = Package.find_by_id(package_id)
    if not package:
        flash('Paket bulunamadı.', 'danger')
        return redirect(url_for('admin.packages'))
    
    # Bu paketi kullanan kullanıcı sayısını kontrol et
    from app import mongo
    user_count = mongo.db.users.count_documents({"package": package.name})
    
    if user_count > 0:
        flash(f'Bu paket {user_count} kullanıcı tarafından kullanılıyor ve silinemiyor.', 'danger')
        return redirect(url_for('admin.packages'))
    
    # Paketi sil
    if package.delete():
        # Log kaydı
        Log.log_action(
            action="package_delete",
            user_id=session['user_id'],
            ip_address=request.remote_addr,
            details={
                "package_id": package.id,
                "name": package.name
            }
        )
        
        flash('Paket başarıyla silindi.', 'success')
    else:
        flash('Paket silinirken bir hata oluştu.', 'danger')
    
    return redirect(url_for('admin.packages'))

@bp.route('/packages/toggle/<package_id>', methods=['POST'])
@admin_required
def toggle_package(package_id):
    """Paket durumunu değiştir (aktif/pasif)"""
    package = Package.find_by_id(package_id)
    if not package:
        flash('Paket bulunamadı.', 'danger')
        return redirect(url_for('admin.packages'))
    
    # Durumu değiştir
    new_status = not package.is_active
    package.update(is_active=new_status)
    
    # Log kaydı
    Log.log_action(
        action="package_toggle",
        user_id=session['user_id'],
        ip_address=request.remote_addr,
        details={
            "package_id": package.id,
            "name": package.name,
            "is_active": new_status
        }
    )
    
    status_text = "aktifleştirildi" if new_status else "devre dışı bırakıldı"
    flash(f'Paket başarıyla {status_text}.', 'success')
    
    return redirect(url_for('admin.packages')) 