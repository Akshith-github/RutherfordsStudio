from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from markdown import markdown
import bleach
from flask import current_app, request , url_for
from datetime import datetime
import hashlib
from flask_login import UserMixin, AnonymousUserMixin
from app.exceptions import ValidationError
from . import db, login_manager


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [
                Permission.FOLLOW, Permission.COMMENT, Permission.WRITE,
                Permission.MODERATE
            ],
            'Administrator': [
                Permission.FOLLOW, Permission.COMMENT, Permission.WRITE,
                Permission.MODERATE, Permission.ADMIN
            ],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name

class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'),
                            primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['FLASKY_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
            if self.email is not None and self.avatar_hash is None:
                self.avatar_hash = self.gravatar_hash()
        self.follow(self)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id}).decode('utf-8')

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id}).decode('utf-8')

    @staticmethod
    def reset_password(token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        user = User.query.get(data.get('reset'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({
            'change_email': self.id,
            'new_email': new_email
        }).decode('utf-8')

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'))
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        # hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user.id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id)\
            .filter(Follow.follower_id == self.id)

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'posts_url': url_for('api.get_user_posts', id=self.id),
            'followed_posts_url': url_for('api.get_user_followed_posts',
                                            id=self.id),
            'post_count': self.posts.count()
        }
        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                        expires_in=expiration)
        return s.dumps({'id': self.id}).decode('utf-8')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])


    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


attributes = {
            'Global': [
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'a': [
                'download', 'href', 'hreflang', 'media', 'ping',
                'referrerpolicy', 'rel', 'shape', 'target', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'applet': [
                'align', 'alt', 'code', 'codebase', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'area': [
                'alt', 'coords', 'download', 'href', 'hreflang', 'media',
                'ping', 'referrerpolicy', 'rel', 'shape', 'target',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'audio': [
                'autoplay', 'buffered', 'controls', 'crossorigin', 'loop',
                'muted', 'preload', 'src', 'accesskey', 'autocapitalize',
                'class', 'contenteditable', 'contextmenu', 'data-*', 'dir',
                'draggable', 'hidden', 'id', 'itemprop', 'lang', 'slot',
                'spellcheck', 'style', 'tabindex', 'title', 'translate'
            ],
            'base': [
                'href', 'target', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'basefont': [
                'color', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'bgsound': [
                'loop', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'blockquote': [
                'cite', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'body': [
                'background', 'bgcolor', 'accesskey', 'autocapitalize',
                'class', 'contenteditable', 'contextmenu', 'data-*', 'dir',
                'draggable', 'hidden', 'id', 'itemprop', 'lang', 'slot',
                'spellcheck', 'style', 'tabindex', 'title', 'translate'
            ],
            'button': [
                'autofocus', 'disabled', 'form', 'formaction', 'formenctype',
                'formmethod', 'formnovalidate', 'formtarget', 'name', 'type',
                'value', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'canvas': [
                'height', 'width', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'caption': [
                'align', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'col': [
                'align', 'bgcolor', 'span', 'accesskey', 'autocapitalize',
                'class', 'contenteditable', 'contextmenu', 'data-*', 'dir',
                'draggable', 'hidden', 'id', 'itemprop', 'lang', 'slot',
                'spellcheck', 'style', 'tabindex', 'title', 'translate'
            ],
            'colgroup': [
                'align', 'bgcolor', 'span', 'accesskey', 'autocapitalize',
                'class', 'contenteditable', 'contextmenu', 'data-*', 'dir',
                'draggable', 'hidden', 'id', 'itemprop', 'lang', 'slot',
                'spellcheck', 'style', 'tabindex', 'title', 'translate'
            ],
            'command': [
                'checked', 'disabled', 'icon', 'radiogroup', 'type',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'data': [
                'value', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'del': [
                'cite', 'datetime', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'details': [
                'open', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'embed': [
                'height', 'src', 'type', 'width', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'fieldset': [
                'disabled', 'form', 'name', 'accesskey', 'autocapitalize',
                'class', 'contenteditable', 'contextmenu', 'data-*', 'dir',
                'draggable', 'hidden', 'id', 'itemprop', 'lang', 'slot',
                'spellcheck', 'style', 'tabindex', 'title', 'translate'
            ],
            'font': [
                'color', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'form': [
                'accept', 'accept-charset', 'action', 'autocomplete',
                'enctype', 'method', 'name', 'novalidate', 'target',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'hr': [
                'align', 'color', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'html': [
                'manifest ', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'iframe': [
                'align', 'allow', 'allowfullscreen' , 'csp ', 'frameborder', 'height', 'importance ', 'loading ',
                'name', 'referrerpolicy', 'sandbox', 'src', 'srcdoc', 'width',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'img': [
                'align', 'alt', 'border', 'crossorigin', 'decoding', 'height',
                'importance ', 'intrinsicsize ', 'ismap', 'loading ',
                'referrerpolicy', 'sizes', 'src', 'srcset', 'usemap', 'width',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'input': [
                'accept', 'alt', 'autocomplete', 'autofocus', 'capture',
                'checked', 'dirname', 'disabled', 'form', 'formaction',
                'formenctype', 'formmethod', 'formnovalidate', 'formtarget',
                'height', 'list', 'max', 'maxlength', 'minlength', 'min',
                'multiple', 'name', 'pattern', 'placeholder', 'readonly',
                'required', 'size', 'src', 'step', 'type', 'usemap', 'value',
                'width', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'ins': [
                'cite', 'datetime', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'keygen': [
                'autofocus', 'challenge', 'disabled', 'form', 'keytype',
                'name', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'label': [
                'for', 'form', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'li': [
                'value', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'link': [
                'crossorigin', 'href', 'hreflang', 'importance ', 'integrity',
                'media', 'referrerpolicy', 'rel', 'sizes', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'map': [
                'name', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'marquee': [
                'bgcolor', 'loop', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'menu': [
                'type', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'meta': [
                'charset', 'content', 'http-equiv', 'name', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'meter': [
                'form', 'high', 'low', 'max', 'min', 'optimum', 'value',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'object': [
                'border', 'data', 'form', 'height', 'name', 'type', 'usemap',
                'width', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'ol': [
                'reversed', 'start', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'optgroup': [
                'disabled', 'label', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'option': [
                'disabled', 'label', 'selected', 'value', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'output': [
                'for', 'form', 'name', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'param': [
                'name', 'value', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'progress': [
                'form', 'max', 'value', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'q': [
                'cite', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'script': [
                'async', 'charset', 'crossorigin', 'defer', 'importance ',
                'integrity', 'language ', 'referrerpolicy', 'src', 'type',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'select': [
                'autocomplete', 'autofocus', 'disabled', 'form', 'multiple',
                'name', 'required', 'size', 'accesskey', 'autocapitalize',
                'class', 'contenteditable', 'contextmenu', 'data-*', 'dir',
                'draggable', 'hidden', 'id', 'itemprop', 'lang', 'slot',
                'spellcheck', 'style', 'tabindex', 'title', 'translate'
            ],
            'source': [
                'media', 'sizes', 'src', 'srcset', 'type', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'style': [
                'media', 'scoped ', 'type', 'accesskey', 'autocapitalize',
                'class', 'contenteditable', 'contextmenu', 'data-*', 'dir',
                'draggable', 'hidden', 'id', 'itemprop', 'lang', 'slot',
                'spellcheck', 'style', 'tabindex', 'title', 'translate'
            ],
            'table': [
                'align', 'background', 'bgcolor', 'border', 'summary ',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'tbody': [
                'align', 'bgcolor', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'td': [
                'align', 'background', 'bgcolor', 'colspan', 'headers',
                'rowspan', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'textarea': [
                'autocomplete', 'autofocus', 'cols', 'dirname', 'disabled',
                'enterkeyhint ', 'form', 'inputmode', 'maxlength', 'minlength',
                'name', 'placeholder', 'readonly', 'required', 'rows', 'wrap',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ],
            'tfoot': [
                'align', 'bgcolor', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'th': [
                'align', 'background', 'bgcolor', 'colspan', 'headers',
                'rowspan', 'scope', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'thead': [
                'align', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'time': [
                'datetime', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'tr': [
                'align', 'bgcolor', 'accesskey', 'autocapitalize', 'class',
                'contenteditable', 'contextmenu', 'data-*', 'dir', 'draggable',
                'hidden', 'id', 'itemprop', 'lang', 'slot', 'spellcheck',
                'style', 'tabindex', 'title', 'translate'
            ],
            'track': [
                'default', 'kind', 'label', 'src', 'srclang', 'accesskey',
                'autocapitalize', 'class', 'contenteditable', 'contextmenu',
                'data-*', 'dir', 'draggable', 'hidden', 'id', 'itemprop',
                'lang', 'slot', 'spellcheck', 'style', 'tabindex', 'title',
                'translate'
            ],
            'video': [
                'autoplay', 'buffered', 'controls', 'crossorigin', 'height',
                'loop', 'muted', 'poster', 'preload', 'src', 'width',
                'accesskey', 'autocapitalize', 'class', 'contenteditable',
                'contextmenu', 'data-*', 'dir', 'draggable', 'hidden', 'id',
                'itemprop', 'lang', 'slot', 'spellcheck', 'style', 'tabindex',
                'title', 'translate'
            ]
        }
allowed_tags = list(set([
    'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li',
    'ol', 'pre', 'strong', 'ul', 'h1', 'h2', 'h3', 'p', 'div',
    'iframe', 'width', 'height', 'src', 'data-video' ]+list(attributes.keys())))


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    
    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        print(value)
        target.body_html = bleach.linkify(
            bleach.clean(markdown(value,
                                    output_format='html',
                                    enable_attributes=True),
                            tags=allowed_tags,
                            attributes=attributes,
                            strip=True))

    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'comments_url': url_for('api.get_post_comments', id=self.id),
            'comment_count': self.comments.count()
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)

db.event.listen(Post.body, 'set', Post.on_changed_body)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        target.body_html = bleach.linkify(bleach.clean(
            markdown(value, output_format='html',enable_attributes=True),
            tags=allowed_tags, attributes=attributes, strip=True))
            
    def to_json(self):
        json_comment = {
            'url': url_for('api.get_comment', id=self.id),
            'post_url': url_for('api.get_post', id=self.post_id),
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)


db.event.listen(Comment.body, 'set', Comment.on_changed_body)
