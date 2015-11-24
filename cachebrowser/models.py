from peewee import *

db = SqliteDatabase('')


class CDN(Model):
    id = CharField(primary_key=True)
    name = CharField()
    edge = CharField()

    class Meta:
        database = db


class Host(Model):
    hostname = CharField(primary_key=True)
    cdn = ForeignKeyField(CDN)

    class Meta:
        database = db

    def __eq__(self, other):
        return self.hostname == other.hostname

    def __str__(self):
        return self.hostname

    def __unicode__(self):
        return self.__str__()


def initialize_database(db_filename):
    db.database = db_filename
    CDN.create_table()
    Host.create_table()
    return db