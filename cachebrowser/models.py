from settings import settings
import logging
import sqlite3
import os

# TODO: limit cache sizes

CLEAN = 0
DIRTY = 1

db = None


def initialize_database(db_filename):
    global db
    if db is not None:
        return
    is_db_new = not os.path.isfile(db_filename)
    db = sqlite3.connect(db_filename, check_same_thread=False)

    if is_db_new:
        logging.debug("No existing database found, creating database at %s" % db_filename)
        for model in [CDN, Host]:
            for sql in model.schema:
                logging.debug(sql)
                db.execute(sql)
                db.commit()

    return db


def get_db():
    global db
    if db is None:
        initialize_database(settings['database'])
    return db


class CDN(object):
    schema = [
        "create table cdn (id varchar(15) primary key, name varchar(20));",
        "create table cdn_ip (cdn varchar(15), ip varchar(15), primary key (cdn, ip));"
    ]
    _cache = {}

    def __init__(self, id=None, name=None):
        self.id = id
        self.name = name
        self._addresses = None
        self._new = True

    def save(self):
        if self._new:
            db.execute('insert into cdn values (?, ?)', (self.id, self.name))
            self._new = False

        if self._addresses is not None:
            dirty_addresses = [addr for addr in self._addresses if self._addresses[addr] == DIRTY]
            if len(dirty_addresses) != 0:
                values = map(lambda addr: ("('%s', '%s')" % (self.id, addr)), dirty_addresses)
                for val in values:
                    sql = "insert into cdn_ip values %s;" % val
                    get_db().execute(sql)
        get_db().commit()

    def add_address(self, address):
        if self._addresses is None:
            self._addresses = {}
        if address in self._addresses:
            return
        self._addresses[address] = DIRTY

    def get_addresses(self):
        if self._addresses is None:
            cursor = db.execute("select ip from cdn_ip where cdn=?", (self.id,))
            for addr in cursor.fetchall():
                if self._addresses is None:
                    self._addresses = {}
                self._addresses[addr[0]] = CLEAN
        return self._addresses.keys()

    def __getattr__(self, item):
        if item == 'addresses':
            return self.get_addresses()

    @staticmethod
    def select():
        cursor = get_db().execute("select * from cdn")
        items = cursor.fetchall()
        hosts = map(lambda item: CDN(id=item[0], name=item[1]), items)
        return list(hosts)

    @staticmethod
    def get(id):
        if id in CDN._cache:
            return CDN._cache[id]

        cursor = get_db().execute("select * from cdn where id=?", (id,))
        item = cursor.fetchone()

        if item is None:
            raise CDN.DoesNotExist()

        cdn = CDN(id=item[0], name=item[1])
        cdn._new = False

        CDN._cache[id] = cdn
        return cdn

    @staticmethod
    def create(id, name, addresses=None):
        cdn = CDN(id=id, name=name)
        if addresses is not None:
            cdn._addresses = {}
            for address in addresses:
                cdn._addresses[address] = DIRTY
        cdn.save()
        return cdn

    class DoesNotExist(Exception):
        pass


class Host(object):
    schema = [
        "create table hosts (url varchar(127) primary key, cdn varchar(15), ssl INTEGER default 0, foreign key (cdn) references cdn(id));"
    ]
    _cache = {}

    def __init__(self, url=None, cdn=None, ssl=False):
        self.url = url
        self.ssl = ssl
        if type(cdn) == CDN:
            self._cdn = cdn.id
        else:
            self._cdn = cdn
        self._new = True

    def save(self):
        if self._new:
            get_db().execute('insert into hosts values (?, ?, ?)', (self.url, self._cdn, self.ssl))
            get_db().commit()
            self._new = False

    @staticmethod
    def select():
        cursor = get_db().execute("select * from hosts")
        items = cursor.fetchall()
        hosts = map(lambda item: Host(url=item[0], cdn=item[1], ssl=item[2]), items)
        return list(hosts)

    @staticmethod
    def get(url):
        if url in Host._cache:
            return Host._cache[url]

        cursor = get_db().execute("select * from hosts where url=?", (url,))
        item = cursor.fetchone()

        if item is None:
            raise Host.DoesNotExist()

        host = Host(url=item[0], cdn=item[1])
        host._new = False

        Host._cache[url] = host
        return host

    @staticmethod
    def create(url, cdn, ssl=False):
        host = Host(url=url, cdn=cdn, ssl=ssl)
        host.save()
        return host

    def _get_cdn(self):
        return CDN.get(self._cdn)

    def __getattr__(self, item):
        if item == 'cdn':
            return self._get_cdn()

    class DoesNotExist(Exception):
        pass


initialize_database('/tmp/cachebrowser.db')