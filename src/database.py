import os
from peewee import *


mysqlpasswd = os.environ.get("MYSQL_PASSWORD")

db = MySQLDatabase("rapgeniusbot", host="localhost",
                   user="root", passwd=mysqlpasswd)


class Comments(Model):
    cid = TextField()

    class Meta:
        database = db


db.connect()

Comments.create_table(True)
