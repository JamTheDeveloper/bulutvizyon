/**
 * BulutVizyon Ana JavaScript Dosyası
 */

// DOM hazır olduğunda çalışacak kodlar
document.addEventListener('DOMContentLoaded', function() {
    // Flash mesajları için otomatik kapanma
    const flashMessages = document.querySelectorAll('.alert');
    flashMessages.forEach(function(flash) {
        setTimeout(function() {
            flash.classList.add('fade');
            setTimeout(function() {
                flash.remove();
            }, 500);
        }, 5000);
    });
    
    // Dosya yükleme alanları için drag & drop desteği
    setupFileUploads();
    
    // Bootstrap tooltip'lerini etkinleştir
    enableTooltips();
    
    // Medya önizleme işlevselliği
    setupMediaPreviews();

    // Tooltips etkinleştirme
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Popovers etkinleştirme
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Dinamik tarih seçiciyi etkinleştir
    const dateInputs = document.querySelectorAll('input[type="date"]');
    if (dateInputs.length > 0) {
        dateInputs.forEach(input => {
            if (!input.value) {
                const today = new Date().toISOString().split('T')[0];
                if (input.id === 'end_date') {
                    // End date için varsayılan olarak 1 ay sonrası
                    const nextMonth = new Date();
                    nextMonth.setMonth(nextMonth.getMonth() + 1);
                    const nextMonthFormatted = nextMonth.toISOString().split('T')[0];
                    input.min = today;
                }
                if (input.id === 'start_date') {
                    input.min = today;
                }
            }
        });
    }

    // Tablo satırlarına tıklamada yönlendirme
    const clickableRows = document.querySelectorAll('tr[data-href]');
    clickableRows.forEach(row => {
        row.style.cursor = 'pointer';
        row.addEventListener('click', () => {
            window.location.href = row.dataset.href;
        });
    });

    // Ekran önizleme için
    const screenPreview = document.getElementById('screen-preview');
    if (screenPreview) {
        initScreenPreview(screenPreview);
    }

    // Responsive tablo
    setupResponsiveTables();
});

/**
 * Bootstrap tooltip'lerini etkinleştirir
 */
function enableTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Dosya yükleme alanları için sürükle-bırak işlevselliği
 */
function setupFileUploads() {
    const dropAreas = document.querySelectorAll('.upload-area');
    
    if (dropAreas.length === 0) return;
    
    dropAreas.forEach(function(dropArea) {
        const fileInput = dropArea.querySelector('input[type="file"]');
        const previewContainer = document.getElementById(dropArea.dataset.preview);
        
        if (!fileInput) return;
        
        // Sürükle bırak olayları
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropArea.classList.add('highlight');
        }
        
        function unhighlight() {
            dropArea.classList.remove('highlight');
        }
        
        // Dosya bırakma olayı
        dropArea.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (fileInput && files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change'));
            }
        }
        
        // Dosya seçme olayı
        fileInput.addEventListener('change', function() {
            if (previewContainer) {
                previewFiles(this.files, previewContainer);
            }
            
            // Form submit butonunu etkinleştir
            const submitBtn = dropArea.closest('form').querySelector('button[type="submit"]');
            if (submitBtn && this.files.length > 0) {
                submitBtn.disabled = false;
            }
        });
        
        // Dosyaları önizle
        function previewFiles(files, container) {
            container.innerHTML = '';
            
            if (files.length === 0) return;
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const fileType = file.type.split('/')[0];
                
                if (fileType === 'image') {
                    previewImage(file, container);
                } else if (fileType === 'video') {
                    previewVideo(file, container);
                } else {
                    previewOther(file, container);
                }
            }
        }
        
        function previewImage(file, container) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const img = document.createElement('img');
                img.src = e.target.result;
                img.classList.add('img-preview');
                container.appendChild(img);
                
                // Dosya bilgileri
                appendFileInfo(file, container);
            }
            reader.readAsDataURL(file);
        }
        
        function previewVideo(file, container) {
            const reader = new FileReader();
            reader.onload = function(e) {
                const video = document.createElement('video');
                video.src = e.target.result;
                video.classList.add('video-preview');
                video.controls = true;
                container.appendChild(video);
                
                // Dosya bilgileri
                appendFileInfo(file, container);
            }
            reader.readAsDataURL(file);
        }
        
        function previewOther(file, container) {
            const fileInfo = document.createElement('div');
            fileInfo.classList.add('file-info');
            fileInfo.innerHTML = `
                <i class="fas fa-file fa-3x"></i>
                <p>${file.name}</p>
                <p>${formatFileSize(file.size)}</p>
            `;
            container.appendChild(fileInfo);
        }
        
        function appendFileInfo(file, container) {
            const fileInfo = document.createElement('div');
            fileInfo.classList.add('file-info', 'mt-2');
            fileInfo.innerHTML = `
                <p class="mb-0"><strong>${file.name}</strong></p>
                <p class="text-muted">${formatFileSize(file.size)}</p>
            `;
            container.appendChild(fileInfo);
        }
        
        function formatFileSize(bytes) {
            if (bytes === 0) return '0 Bytes';
            const k = 1024;
            const sizes = ['Bytes', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }
    });
}

/**
 * Medya önizleme işlevselliği
 */
function setupMediaPreviews() {
    const mediaItems = document.querySelectorAll('.media-item');
    
    if (mediaItems.length === 0) return;
    
    mediaItems.forEach(function(item) {
        item.addEventListener('click', function() {
            const mediaId = this.dataset.id;
            const mediaType = this.dataset.type;
            const mediaUrl = this.dataset.url;
            const mediaTitle = this.dataset.title;
            
            const modal = document.getElementById('mediaPreviewModal');
            if (!modal) return;
            
            const modalTitle = modal.querySelector('.modal-title');
            const modalBody = modal.querySelector('.modal-body');
            
            modalTitle.textContent = mediaTitle;
            modalBody.innerHTML = '';
            
            if (mediaType === 'image') {
                const img = document.createElement('img');
                img.src = mediaUrl;
                img.classList.add('img-fluid');
                modalBody.appendChild(img);
            } else if (mediaType === 'video') {
                const video = document.createElement('video');
                video.src = mediaUrl;
                video.classList.add('img-fluid');
                video.controls = true;
                video.autoplay = true;
                modalBody.appendChild(video);
            }
            
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        });
    });
}

// Ekran önizlemesi için 
function initScreenPreview(element) {
    const apiKey = element.dataset.apiKey;
    if (!apiKey) return;
    
    // Burada gerçek API'den veri çekme kodu olacak
    console.log('Ekran önizleme başlatıldı: ' + apiKey);
    
    // Örnek: 5 saniyede bir yenile
    setInterval(() => {
        console.log('Ekran önizleme yenileniyor: ' + apiKey);
        // API isteği burada yapılacak
    }, 5000);
}

// Responsive tablolar için
function setupResponsiveTables() {
    const tables = document.querySelectorAll('.table-responsive-header');
    
    tables.forEach(table => {
        if (window.innerWidth < 768) {
            const headerCells = table.querySelectorAll('thead th');
            const headerTexts = Array.from(headerCells).map(cell => cell.textContent.trim());
            
            const bodyRows = table.querySelectorAll('tbody tr');
            bodyRows.forEach(row => {
                const cells = row.querySelectorAll('td');
                cells.forEach((cell, index) => {
                    if (headerTexts[index]) {
                        cell.setAttribute('data-label', headerTexts[index]);
                    }
                });
            });
        }
    });
} 