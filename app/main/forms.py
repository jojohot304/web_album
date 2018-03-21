from flask_wtf import FlaskForm
from pymongo import MongoClient
from wtforms import StringField, PasswordField, BooleanField, SubmitField, validators, TextAreaField
from flask_wtf.file import FileField, FileRequired, FileAllowed
#from wtforms import required, Length, Email, Regexp, EqualTo

ALLOWED_EXTENDSIONS = set(['txt','pdf','png','jpg','gif','jpeg', 'JPG'])


class LoginForm(FlaskForm):
    username = StringField('UserName', validators=[validators.DataRequired(), validators.length(6, 32)])
    password = PasswordField('Password', validators=[validators.DataRequired()])
    remember_me = BooleanField('remember_login')
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[validators.DataRequired(), validators.length(6, 32)])
    password1 = PasswordField('Password', validators=[validators.DataRequired()])
    password2 = PasswordField('Password Confirm', validators=[validators.DataRequired(), validators.equal_to('password1', message='两次输入密码必须一致')])
    name = StringField('Your Name', validators=[validators.DataRequired()])
    submit = SubmitField('Register')


class UploadForm(FlaskForm):
    photo = FileField(validators=[FileAllowed(ALLOWED_EXTENDSIONS, 'only image file'), FileRequired('please select the image file')])
    submit = SubmitField(u'Upload.')


class NewAlbumForm(FlaskForm):
    name = StringField('Album Name')
    about = TextAreaField('About this Album', render_kw={'rows': 8})
    photo = FileField('Photo', validators=[FileAllowed(ALLOWED_EXTENDSIONS, 'only image file'), FileRequired('please select the image file')])
    submit = SubmitField('Create and Upload')


class NewPhotoForm(FlaskForm):
    photo = FileField(validators=[FileAllowed(ALLOWED_EXTENDSIONS, '只能上传图片'), FileRequired('请选择图片文件')])
    submit = SubmitField('上传照片')