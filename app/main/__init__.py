from flask import Blueprint
import os

main = Blueprint('main', __name__,static_folder = os.environ['static_folder'] ,
                static_url_path = os.environ['static_url_path'])

from . import views, errors
from ..models import Permission


@main.app_context_processor
def inject_permissions():
    return dict(Permission=Permission)