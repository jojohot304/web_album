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


db = MongoClient('mongodb://webuser:user123@59.110.173.232:27017').admin
#db = MongoClient('127.0.0.1:27017').photo


@login_manager.user_loader
def load_user(user_id):
    user = db.images.find_one({'_id': ObjectId(user_id)})
    return Temp(id=user.get('_id'), username=user.get('username'), password=user.get('password'), activate=user.get('activate'),
                       name=user.get('name'), album_ids=user.get('album_ids'), about_me=user.get('about_me'))


def encrypt_password(password):
    return generate_password_hash(password)


def verify_password(user_password, password):
    return check_password_hash(user_password, password)


class User(UserMixin):
    def __init__(self, username, password, name, album_ids=[], about_me=''):
        self.username = username
        self.password_hash = encrypt_password(password)
        self.name = name
        self.db = db
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

    @classmethod
    def get_user(cls, user_id):
        return db.images.find_one({'_id': ObjectId(str(user_id))})


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
            self.db = db

    def new_album(self):
            new_params = {
                'album_name': self.album_name,
                'about_album': self.about,
                'photo_ids': self.photo_ids,
                'album_cover': self.album_cover,
                'created_at': self.created_at
            }
            return self.db.images.insert(new_params)

    @classmethod
    def get_photo_ids(cls, album_id):
        return db.images.find_one({'_id': ObjectId(str(album_id))})['photo_ids']

    @classmethod
    def get_photo_index_and_id(cls, album, photo):
        photo_ids = Album.get_photo_ids(album['_id'])
        photo_id = photo['_id']
        photo_index = photo_ids.index(photo_id)+1
        next_photo_id = photo_ids[photo_index] if photo_index<len(photo_ids) else photo_ids[0]
        pre_photo_id = photo_ids[photo_index-2] if photo_index>1 else photo_ids[-1]
        return [photo_index, pre_photo_id, next_photo_id]

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
        fs = gridfs.GridFS(db)
        file_content = self.get_orientation()
        if self.exif_tags != {}:
            return fs.put(file_content, filename=self.filename, location=self.get_exif_location(self.exif_tags),
                             comments=self.comments, album_id=self.album_id, thumbnail=self.thumbnail, created_at=self.created_at)
        else:
            return fs.put(file_content, filename=self.filename, location=self.exif_tags,
                             comments=self.comments, album_id=self.album_id, thumbnail=self.thumbnail, created_at=self.created_at)

    def _get_if_exist(self, data, key):
        if key in data:
            return data[key]

        return None

    def _convert_to_degress(self, value):
        """
        Helper function to convert the GPS coordinates stored in the EXIF to degress in float format
        :param value:
        :type value: exifread.utils.Ratio
        :rtype: float
        """
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)

        return d + (m / 60.0) + (s / 3600.0)

    def get_exif_location(self, exif_data):
        """
        Returns the latitude and longitude, if available, from the provided exif_data (obtained through get_exif_data above)
        """
        lat = None
        lon = None

        gps_latitude = self._get_if_exist(exif_data, 'GPS GPSLatitude')
        gps_latitude_ref = self._get_if_exist(exif_data, 'GPS GPSLatitudeRef')
        gps_longitude = self._get_if_exist(exif_data, 'GPS GPSLongitude')
        gps_longitude_ref = self._get_if_exist(exif_data, 'GPS GPSLongitudeRef')

        if gps_latitude and gps_latitude_ref and gps_longitude and gps_longitude_ref:
            lat = self._convert_to_degress(gps_latitude)
            if gps_latitude_ref.values[0] != 'N':
                lat = 0 - lat

            lon = self._convert_to_degress(gps_longitude)
            if gps_longitude_ref.values[0] != 'E':
                lon = 0 - lon

        return {'lat': lat, 'lng': lon}


    """
    def get_gps(self, gps_exif_tags):
        if ('GPS GPSLatitude' in gps_exif_tags) and ('GPS GPSLongitude' in gps_exif_tags):
            latitude_ref = gps_exif_tags['GPS GPSLatitudeRef'].values == 'N' and 1 or -1
            longitude_ref = gps_exif_tags['GPS GPSLongitudeRef'].values == 'E' and 1 or -1
            latitude = self.get_location(gps_exif_tags['GPS GPSLatitude'].values)*latitude_ref
            longitude = self.get_location(gps_exif_tags['GPS GPSLongitude'].values)*longitude_ref
            return {'lat': latitude, 'lng': longitude}
        else:
            return {}

    def get_location(self, location_Ratio):
        if '/' in str(location_Ratio[0]):
            return (int(str(location_Ratio[0]).split('/')[0])/int(str(location_Ratio[0]).split('/')[1]))/3600
        elif '/' in str(location_Ratio[1]):
            return int(str(location_Ratio[0]))+(int(str(location_Ratio[1]).split('/')[0])/int(str(location_Ratio[1]).split('/')[1]))/3600
        return int(str(location_Ratio[0]))+int(str(location_Ratio[1]))/60+(int(str(location_Ratio[2]).split('/')[0])/int(str(location_Ratio[2]).split('/')[1]))/3600
    """

    def get_orientation(self):
        if 'Image Orientation' in self.exif_tags:
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
        return self.file.read()

    def get_created_date(self):
        time_original = str(self.exif_tags['EXIF DateTimeOriginal'])
        date_time = datetime.datetime.strptime(time_original, '%Y:%m:%d %H:%M:%S')
        return date_time

    @classmethod
    def get_gps_info(cls, photo_id):
        return db.fs.files.find_one({'_id': ObjectId(str(photo_id))})['location']


class Thumbnail(object):

    def __init__(self, file):
        self.size = (512, 512)
        file.seek(0)
        self.exif_tags = exifread.process_file(file)
        file.seek(0)
        self.im = Image.open(file)
        self.thumbnail_file_path = 'D:/thumbnail/'+'thumbnails '+file.filename

    def get_thumbnail(self):
        if 'Image Orientation' in self.exif_tags:
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
        self.im.thumbnail(self.size)
        bytes_data = io.BytesIO()
        self.im.save(bytes_data, format='JPEG')
        return bytes_data.getvalue()




