# -*- coding: utf-8 -*-
import json
import pprint
import gridfs
from app.models import User, Album, Photo, Temp, verify_password, db
from bson.objectid import ObjectId
from flask import request, render_template, url_for, redirect, flash, current_app
from flask_login import login_user, login_required, current_user, logout_user
from pymongo import MongoClient
from app.main.forms import LoginForm, RegisterForm, NewAlbumForm, NewPhotoForm
from . import main

ALLOWED_EXTENDSIONS = set(['txt','pdf','png','jpg','gif','jpeg', 'JPG'])

fs = gridfs.GridFS(db)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENDSIONS


@main.route('/new_album/', methods=['GET', 'POST'])
@login_required
def new_album():
    form = NewAlbumForm()
    if form.validate_on_submit():
        if request.method == 'POST':
            album_id = Album(album_name=form.name.data, about=form.about.data).new_album()
            pprint.pprint(db.images.find_one({'_id': album_id}))
            file = form.photo.data          #读取照片
            photo_id = Photo(file=file, album_id=album_id).new_photo()
            photo_ids = db.images.find_one({'_id': album_id})['photo_ids']
            photo_ids.append(photo_id)
            thumbnail_content = db.fs.files.find_one({'_id': ObjectId(str(photo_id))})['thumbnail']
            db.images.update_one({'_id': album_id}, {'$set': {'photo_ids': photo_ids, 'album_cover': thumbnail_content}}, upsert=True)   #将照片的id添加进相册的photo_ids中
            album_ids = db.images.find_one({'_id': ObjectId(current_user.id)})['album_ids']
            album_ids.append(album_id)
            db.images.update_one({'_id': ObjectId(current_user.id)}, {'$set': {'album_ids': album_ids}})  #将相册的id加入用户的album_ids中
        return redirect(url_for('main.show_albums'))
    return render_template('new_album.html', form=form)


@main.route('/newphoto/<id>', methods=['GET', 'POST'])
@login_required
def new_photo(id):
    print('album id is', id)
    form = NewPhotoForm()
    if form.validate_on_submit():
        photo_file = request.files.getlist("photo")
        for file in photo_file:
            photo_id = Photo(file=file, album_id=ObjectId(str(id))).new_photo()
            photo_ids = db.images.find_one({'_id': ObjectId(str(id))})['photo_ids']
            photo_ids.append(photo_id)
            thumbnail_content = db.fs.files.find_one({'_id': ObjectId(str(photo_id))})['thumbnail']
            db.images.update_one({'_id': ObjectId(str(id))}, {'$set': {'photo_ids': photo_ids, 'album_cover': thumbnail_content}},upsert=True)
        return redirect(url_for('main.new_photo', id=id))
    return render_template('new_photo.html', form=form, album=db.images.find_one({'_id': ObjectId(str(id))}))


@main.route('/photo/<id>', methods=['GET'])
@login_required
def show_photo(id):
    for f in fs.find({'_id': ObjectId(str(id))}):
        photo_content = f.read()
    rsp = current_app.make_response(photo_content)
    rsp.headers['Content-Type'] = 'image/jpeg'
    return rsp


@main.route('/fullphoto/<id>', methods=['GET'])
@login_required
def show_full_photo(id):
    photo = db.fs.files.find_one({'_id': ObjectId(str(id))})
    album = db.images.find_one({'_id': ObjectId(str(photo['album_id']))})
    photo_index_and_id = Album.get_photo_index_and_id(album, photo)
    print(photo_index_and_id)
    return render_template('full_photo.html', photo=photo, album=album, photo_index_and_id=photo_index_and_id)


@main.route('/thumbnail/<id>', methods=['GET', 'POST'])
@login_required
def show_thumbnail(id):
    #print('photo id is', id)
    thumbnail_content = db.fs.files.find_one({'_id': ObjectId(str(id))})['thumbnail']
    rsp = current_app.make_response(thumbnail_content)

    rsp.headers['Content-Type'] = 'image/jpeg'
    return rsp


@main.route('/show_album_cover/<id>', methods=['GET'])
@login_required
def show_album_cover(id):
    album_cover_content = db.images.find_one({'_id': ObjectId(id)})['album_cover']
    #print('album id is:',id)
    #print(type(album_cover_content))
    rsp = current_app.make_response(album_cover_content)
    rsp.headers['Content-Type'] = 'image/jpeg'
    return rsp


@main.route('/album/<id>', methods=['GET'])
@login_required
def show_album(id):
    album = db.images.find_one({'_id': ObjectId(id)})
    photos = []
    for photo_id in album['photo_ids']:
        photo_info = db.fs.files.find_one({'_id': ObjectId(str(photo_id))})
        photos.append(photo_info)
    return render_template('album.html', album=album, photos=photos)


@main.route('/', methods=['GET'])
@login_required
def show_albums():
    albums = []
    print('当前用户ID为：', current_user.id)
    for album_id in db.images.find_one({'_id': ObjectId(current_user.id)})['album_ids']:
        album_info = db.images.find_one({'_id': album_id})
        albums.append(album_info)
    return render_template('albums.html', albums=albums)


@main.route('/editalbum/<id>', methods=['GET', 'POST'])
@login_required
def edit_album(id):
    album = db.images.find_one({'_id':ObjectId(id)})
    photos = []
    for photo_id in album['photo_ids']:
        photo = db.fs.files.find_one({'_id':photo_id})
        photos.append(photo)
    if request.method == 'POST':
        for edit_photo_id in album['photo_ids']:
            db.fs.files.update_one({'_id': ObjectId(edit_photo_id)}, {'$set': {'comments': request.form[str(edit_photo_id)+'comments']}})
        print ('album_cover_id is',request.form['album_cover_id'])
        album_cover = db.fs.files.find_one({'_id': ObjectId(request.form['album_cover_id'])})['thumbnail']
        db.images.update_one({'_id': ObjectId(id)}, {'$set': {'album_cover': album_cover}})
        return redirect(url_for('main.show_album', id=id))
    return render_template('edit_album.html', album=album, photos=photos)


@main.route('/editphoto/<id>', methods=['GET', 'POST'])
@login_required
def edit_photo(id):
    photo = db.fs.files.find_one({'_id':ObjectId(id)})
    if request.method == 'POST':
        db.fs.files.update_one({'_id': ObjectId(id)}, {'$set': {'comments': request.form['comments']}})
    return redirect(url_for('main.show_full_photo', id=id))


@main.route('/map/')
@login_required
def show_map():
    all_location = []
    album_ids = User.get_user(current_user.id)['album_ids']
    for album_id in album_ids:
        photo_ids = Album.get_photo_ids(album_id)
        print('photo_ids is',photo_ids)
        for photo_id in photo_ids:
            photo_location = Photo.get_gps_info(photo_id)
            print ('photo_location is',photo_location)
            if photo_location != {'lat': None, 'lng': None}:
                all_location.append([photo_location['lng'], photo_location['lat']])
    print ('当前用户位置信息有：', all_location)
    return render_template('location.html', all_location=json.dumps(all_location))


@main.route('/changepassword/')
@login_required
def change_password():

    return render_template('change_password.html')


@main.route('/editprofile/')
@login_required
def edit_profile():
    return render_template('edit_profile.html')


@main.route('/about_me/')
@login_required
def about_me():
    return render_template('about_me.html')


@main.route('/album/orderphoto/<id>', methods=['GET'])
@login_required
def order_photo(id):
    photo_ids = []
    for photo in db.fs.files.find({'album_id': ObjectId(id)}).sort('created_at', -1):
        photo_ids.append(photo['_id'])
    db.images.update_one({'_id': ObjectId(id)}, {'$set': {'photo_ids': photo_ids}})
    return redirect(url_for('main.show_album', id=id))


@main.route('/delete/photo/<id>', methods=['GET', 'POST'])
@login_required
def delete_photo(id):
    album_id = db.fs.files.find_one({'_id':ObjectId(id)})['album_id']
    print('the album of this photo is', album_id)
    photo_ids = db.images.find_one({'_id':ObjectId(album_id)})['photo_ids']
    print('the photo ids of this album is', photo_ids)
    photo_ids.remove(ObjectId(id))
    db.images.update_one({'_id': album_id}, {'$set': {'photo_ids': photo_ids}})
    fs.delete(ObjectId(id))
    return redirect(url_for('main.edit_album', id=album_id))

@main.route('/login/', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
            user = db.images.find_one({'username': form.username.data})
            if user is not None and verify_password(user.get('password'), form.password.data):
                    user = Temp(id=user.get('_id'), username=user.get('username'), password=user.get('password'), activate=user.get('activate'),
                                       name=user.get('name'), album_ids=user.get('album_ids'), about_me=user.get('about_me'))
                    login_user(user)
                    return redirect(url_for('main.show_albums'))
            flash('Invalid username or password!')
    return render_template('login.html', form=form)


@main.route('/logout/')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.login'))


@main.route('/register/', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        User(username=form.username.data, password=form.password1.data, name=form.name.data).new_user()
        flash('Registered successfully!')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)


@main.route('/deletedata/', methods=['GET'])
@login_required
def delete_data():
    for f in fs.list():
        fs.delete(ObjectId(str(db.fs.files.find_one({'filename': f})['_id'])))
    album_ids = db.images.find_one({'_id': ObjectId(current_user.id)})['album_ids']
    for album_id in album_ids:
            db.images.delete_one({'_id': ObjectId(album_id)})
    db.images.update_one({'_id': ObjectId(current_user.id)}, {'$set': {'album_ids': []}})
    return redirect(url_for('main.show_albums'))


