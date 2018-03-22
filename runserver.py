#!/usr/bin/env python
# _*_ coding:utf-8 _*_

from app import create_app
#from flask_script import Manager
from pprint import pprint

app = create_app()
#manager = Manager(app)

if __name__ == '__main__':
    #pprint(app.url_map)
    app.run()
