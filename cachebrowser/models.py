import peewee
from bootstrap import bootstrapper, BootstrapError

db = peewee.SqliteDatabase('')


class BaseModel(peewee.Model):
    pass
    # @classmethod
    # def get(cls, **kwargs):
    #     args = []
    #     for key in kwargs:
    #         args.append(getattr(cls, key)==kwargs[key])
    #     return super(BaseModel, cls).get(*args)


class CDN(BaseModel):
    id = peewee.CharField(primary_key=True)
    name = peewee.CharField(null=True)
    edge_server = peewee.CharField(null=True)

    valid = peewee.BooleanField(null=False, default=True)

    class Meta:
        database = db

    @classmethod
    def get_or_bootstrap(cls, id):
        try:
            return super(CDN, cls).get(CDN.id == id)
        except DoesNotExist:
            try:
                cdn_data = bootstrapper.lookup_cdn(id)
                cdn = CDN(**cdn_data)
                cdn.save(force_insert=True)
                return cdn
            except BootstrapError:
                raise DoesNotExist

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.__str__()


class Host(peewee.Model):
    hostname = peewee.CharField(primary_key=True)
    cdn = peewee.ForeignKeyField(CDN, null=True)
    ssl = peewee.BooleanField(default=False)
    is_active = peewee.BooleanField(default=True)

    class Meta:
        database = db

    @classmethod
    def get_or_bootstrap(cls, hostname):
        try:
            return super(Host, cls).get(Host.hostname == hostname)
        except DoesNotExist:
            try:
                host_data = bootstrapper.lookup_host(hostname)
            except BootstrapError:
                raise DoesNotExist

            host = Host(**host_data)

            try:
                host.cdn = CDN.get_or_bootstrap(host.cdn_id)
            except DoesNotExist:
                host.cdn = CDN.create(id=host.cdn_id, valid=False)

            host.save(force_insert=True)

            return host

    def __eq__(self, other):
        return self.hostname == other.hostname

    def __str__(self):
        return self.hostname

    def __unicode__(self):
        return self.__str__()


DoesNotExist = peewee.DoesNotExist


def initialize_database(db_filename, reset=False):
    db.database = db_filename

    if reset:
        Host.drop_table(True)
        CDN.drop_table(True)

    CDN.create_table(True)
    Host.create_table(True)

    return db