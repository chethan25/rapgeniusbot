# -*- coding: utf-8 -*-
"""
Module to connect to mysql database which is used
to store comment ids.
"""
import os

from peewee import *


# Initializing the database.
db = MySQLDatabase('rapgeniusbot',
                   host='localhost',
                   user='root',
                   passwd=os.environ.get('MYSQL_PASSWORD'))


class Comments(Model):
    cid = TextField()

    class Meta:
        database = db


db.connect()

# The True flag won't alarm if table exists.
Comments.create_table(True)
