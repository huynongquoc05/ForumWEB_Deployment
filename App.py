import os

import redis
from flask import Flask
from flask_wtf import CSRFProtect
from fix_pas import update_all_passwords

def create_app():
    # update_all_passwords()
    app = Flask(__name__)
    from models import cache
    app.cache = cache

    # Cấu hình ứng dụng
    app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your_secret_key_here')
    app.config['DEBUG'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = True
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

    # Kích hoạt CSRF protection
    csrf = CSRFProtect(app)

    # Import và đăng ký các route từ các blueprint
    from auth_routes import auth
    app.register_blueprint(auth)

    return app
