from flask_wtf import Form , FlaskForm
from flask import flash
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo,DataRequired
from wtforms import ValidationError
from ..models import User
from wtforms.fields.html5 import EmailField


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[Required(), Length(1, 64),Email()])
    password = PasswordField('Password', validators=[Required()])
    show_password = BooleanField('Show password', id='check')
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class RegistrationForm(FlaskForm):
    email = EmailField('Email', validators=[Required(), Length(1, 64), Email()])
    username = StringField('Username', validators=[
        Required(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                            'Usernames must have only letters, '
                                            'numbers, dots or underscores')])
    password = PasswordField('Password', validators=[ Required(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm password', validators=[Required()])
    show_password = BooleanField('Show password', id='check')
    show_password2 = BooleanField('Show Confirmation password', id='check')
    submit = SubmitField('Register')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            flash('Email already registered')
            raise ValidationError('Email already registered.')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            flash('User already registered or try other user name')
            raise ValidationError('Username already in use.')

class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[Required()])
    password = PasswordField('New password', validators=[
        Required(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm new password', validators=[Required()])
    show_password = BooleanField('Show password', id='check')
    show_password2 = BooleanField('Show Confirmation password', id='check')
    submit = SubmitField('Update Password')


class PasswordResetRequestForm(FlaskForm):
    email = StringField('Email', validators=[Email()])
    submit = SubmitField('Reset Password')


class PasswordResetForm(FlaskForm):
    email = EmailField('Email', validators=[Required(), Length(1, 64), Email()])
    password = PasswordField('New Password', validators=[
        Required(), EqualTo('password2', message='Passwords must match')])
    password2 = PasswordField('Confirm password', validators=[Required()])
    show_password = BooleanField('Show password', id='check')
    show_password2 = BooleanField('Show Confirmation password', id='check')
    submit = SubmitField('Reset Password')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first() is None:
            raise ValidationError('Unknown email address.')


class ChangeEmailForm(FlaskForm):
    email = EmailField('New Email', validators=[Required(), Length(1, 64),
                                                    Email()])
    password = PasswordField('Password', validators=[Required()])
    show_password = BooleanField('Show password', id='check')
    submit = SubmitField('Update Email Address')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')