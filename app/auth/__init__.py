from flask import Blueprint
import os

auth = Blueprint('auth', __name__,static_folder = os.environ['static_folder'] ,
                static_url_path = os.environ['static_url_path'] )

from . import views