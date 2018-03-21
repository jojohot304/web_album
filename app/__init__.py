#!/usr/bin/env python
# _*_ coding:utf-8 _*_
import os
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_login import LoginManager


bootstrap = Bootstrap()
login_manager = LoginManager()
login_manager.login_view = 'main.login'


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.urandom(24)
    bootstrap.init_app(app)
    login_manager.init_app(app)
    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app