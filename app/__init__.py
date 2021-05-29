from flask import Flask
# from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_pagedown import PageDown
from config import config
import os

# bootstrap = Bootstrap()
mail = Mail()
moment = Moment()
db = SQLAlchemy(session_options={"autoflush": False})
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
pagedown = PageDown()


def create_app(config_name):
    app = Flask(__name__,template_folder = os.path.join(os.path.dirname(__file__),"templates"),
                static_folder = os.path.join(os.path.dirname(__file__),"assets"),
                static_url_path = '/assets')
    os.environ['static_folder'] = app.static_folder
    os.environ['static_url_path'] = app.static_url_path
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    # bootstrap.init_app(app)
    mail.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    pagedown.init_app(app)
    
    if app.config['SSL_REDIRECT']:
        from flask_sslify import SSLify
        sslify = SSLify(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    
    return app

