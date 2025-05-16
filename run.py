#!/usr/bin/env python3
"""
BulutVizyon Server
-----------------
Dijital Reklam Ekran Yönetim Sistemi
"""

from app import create_app, configure_logging

app = create_app()
configure_logging(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006, debug=True) 