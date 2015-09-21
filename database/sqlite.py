import os
import sqlite3
import logging
from database.base import CacheBrowserDatabase
from settings import settings


__all__ = ['SqliteDatabase']

CREATE_DATABASE_SQL = [
"""
create table cdn (
  id varchar(63) primary key,
  name varchar(255)
);
""",
"""
create table cdn_ip (
  cdn varchar(63) primary key,
  ip varchar(15) not null,
  foreign key(cdn) references cdn(id)
);
""",
"""
create table domain_cdn (
  domain varchar(127) primary key,
  cdn varchar(63),
  foreign key(cdn) references cdn(ip)
);
"""
]


class SqliteDatabase(CacheBrowserDatabase):
    def __init__(self, *args, **kwargs):
        self.connection = None

    def get_connection(self):
        if not self.connection:
            db_file = settings.get("sqlite_database", "/Users/hadi/.cachebrowser.db")
            is_db_new = not os.path.isfile(db_file)
            self.connection = sqlite3.connect(db_file)

            if is_db_new:
                logging.debug("No existing database found, creating database at %s" % (db_file))
                for sql in CREATE_DATABASE_SQL:
                    self.connection.execute(sql)
        return self.connection

    def get_cdn_for_domain(self, domain):
        connection = self.get_connection()
        cursor = connection.execute("select cdn from domain_cdn where domain=?", (domain,))
        return cursor.fetchone()

    def get_cdn_ips(self, cdn):
        connection = self.get_connection()
        cursor = connection.execute("select ip from cdn_ip where cdn=?", (cdn,))
        return cursor.fetchall()
        # return list(map(lambda x: x[0], cursor.fetchall()))

    def add_cdn_for_domain(self, domain, cdn):
        super(SqliteDatabase, self).add_cdn_for_domain(domain, cdn)
        connection = self.get_connection()
        connection.execute("insert into domain_cdn values (?, ?)", (domain, cdn))

    def add_cdn_ip(self, cdn, ip):
        super(SqliteDatabase, self).add_cdn_ip(cdn, ip)
        if type(ip) is not list and type(ip) is not tuple:
            ip = (ip,)
        connection = self.get_connection()
        for address in ip:
            connection.execute("insert into cdn_ip values (?, ?)", (cdn, address))
