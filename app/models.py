# -*- coding: utf-8 -*-
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin,current_user, LoginManager
from bson.objectid import ObjectId
from pymongo import MongoClient
from werkzeug.utils import secure_filename
import exifread
import gridfs
import time, datetime
import io
from . import login_manager
from PIL import Image


@login_manager.user_loader
def load_user(user_id):
    user = MongoClient('mongodb://webuser:user123@59.110.173.232:27017').admin.images.find_one({'_id':ObjectId(user_id)})
    return Temp(id=user.get('_id'), username=user.get('username'), password=user.get('password'), activate=user.get('activate'),
                       name=user.get('name'), album_ids=user.get('album_ids'), about_me=user.get('about_me'))


def encrypt_password(password):
    return generate_password_hash(password)


def verify_password(user_password,password):
    return check_password_hash(user_password,password)


class User(UserMixin):
    def __init__(self, username, password, name, album_ids=[], about_me=''):
        self.username = username
        self.password_hash = encrypt_password(password)
        self.name = name
        self.db = MongoClient('mongodb://webuser:user123@59.110.173.232:27017').admin
        self.album_ids = album_ids
        self.about_me = about_me

    def new_user(self):
        new_params = {
                        'username': self.username,
                        'password': self.password_hash,
                        'activate': False,
                        'name': self.name,
                        'album_ids': self.album_ids,
                        'about_me': self.about_me
                     }
        self.db.images.insert(new_params)


    def __repr__(self):
            return self.username


class Temp(UserMixin):
        is_active = True
        is_anonymous = False
        is_authenticated = True
        username = ''

        def __init__(self, id, username, password, activate, name, album_ids=[], about_me=''):
            self.id = str(id)
            self.username = username
            self.password_hash = password
            self.activate = activate
            self.name = name
            self.album_ids = album_ids
            self.about_me = about_me

        def get_id(self):
            return self.id

        def __repr__(self):
            return self.username


class Album(object):
    def __init__(self, album_name, about, photo_ids=[], album_cover=None):
            self.album_name = album_name
            self.photo_ids = photo_ids
            self.about = about
            self.album_cover = album_cover
            self.created_at = time.strftime('%Y-%m-%d', time.localtime(time.time()))
            self.db = MongoClient('mongodb://webuser:user123@59.110.173.232:27017').admin

    def new_album(self):
            new_params = {
                'album_name': self.album_name,
                'about_album': self.about,
                'photo_ids': self.photo_ids,
                'album_cover': self.album_cover,
                'created_at': self.created_at
            }
            return self.db.images.insert(new_params)


class Photo(object):
    def __init__(self, file, album_id, comments=''):
        self.filename = secure_filename(file.filename)
        self.file = file
        self.exif_tags = exifread.process_file(file)
        self.comments = comments
        self.album_id = album_id
        file.seek(0)
        self.thumbnail = Thumbnail(file).get_thumbnail()
        self.created_at = self.get_created_date()

    def new_photo(self):
        db = MongoClient('mongodb://webuser:user123@59.110.173.232:27017').admin
        fs = gridfs.GridFS(db)
        file_content = self.get_orientation()
        if self.exif_tags != {}:
            return fs.put(file_content, filename=self.filename,location=self.get_gps(self.exif_tags),
                             comments=self.comments, album_id=self.album_id, thumbnail=self.thumbnail, created_at=self.created_at)
        else:
            return fs.put(file_content, filename=self.filename, location=self.exif_tags,
                             comments=self.comments, album_id=self.album_id, thumbnail=self.thumbnail, created_at=self.created_at)

    def get_gps(self, gps_exif_tags):
        if ('GPS GPSLatitude' in gps_exif_tags) and ('GPS GPSLongitude' in gps_exif_tags):
            latitude_ref = gps_exif_tags['GPS GPSLatitudeRef'].values == 'N' and 1 or -1
            longitude_ref = gps_exif_tags['GPS GPSLongitudeRef'].values == 'E' and 1 or -1
            latitude = self.get_location(gps_exif_tags['GPS GPSLatitude'].values)*latitude_ref
            longitude = self.get_location(gps_exif_tags['GPS GPSLongitude'].values)*longitude_ref
            return {'location': {'lat': latitude, 'lng': longitude}}
        else:
            return {}

    def get_location(self, location_Ratio):
        if '/' in str(location_Ratio[0]):
            return (int(str(location_Ratio[0]).split('/')[0])/int(str(location_Ratio[0]).split('/')[1]))/3600
        elif '/' in str(location_Ratio[1]):
            return int(str(location_Ratio[0]))+(int(str(location_Ratio[1]).split('/')[0])/int(str(location_Ratio[1]).split('/')[1]))/3600
        return int(str(location_Ratio[0]))+int(str(location_Ratio[1]))/60+(int(str(location_Ratio[2]).split('/')[0])/int(str(location_Ratio[2]).split('/')[1]))/3600

    def get_orientation(self):
        Image_Orientation = str(self.exif_tags['Image Orientation']).split(' ')
        self.file.seek(0)
        if Image_Orientation[0] == 'Horizontal':
            return self.file.read()
        else:
            im = Image.open(self.file)
            angle = int(Image_Orientation[1])
            im_rotated = im.rotate(angle)
            bytes_data = io.BytesIO()
            im_rotated.save(bytes_data, format='JPEG')
            return bytes_data.getvalue()

    def get_created_date(self):
        time_original = str(self.exif_tags['EXIF DateTimeOriginal'])
        date_time = datetime.datetime.strptime(time_original, '%Y:%m:%d %H:%M:%S')
        return date_time

class Thumbnail(object):

    def __init__(self, file):
        self.size = (512, 512)
        file.seek(0)
        self.exif_tags = exifread.process_file(file)
        file.seek(0)
        self.im = Image.open(file)
        self.thumbnail_file_path = 'D:/thumbnail/'+'thumbnails '+file.filename

    def get_thumbnail(self):
        Image_Orientation = str(self.exif_tags['Image Orientation']).split(' ')
        if Image_Orientation[0] == 'Horizontal':
            self.im.thumbnail(self.size)
            bytes_data = io.BytesIO()
            self.im.save(bytes_data, format='JPEG')
            return bytes_data.getvalue()
        else:
            angle = int(Image_Orientation[1])
            im_rotated = self.im.rotate(angle)
            im_rotated.thumbnail(self.size)
            bytes_data = io.BytesIO()
            im_rotated.save(bytes_data, format='JPEG')
            return bytes_data.getvalue()
