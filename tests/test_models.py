import unittest
from peewee import DoesNotExist
from cachebrowser.models import initialize_database, Host, CDN


class ModelsTest(unittest.TestCase):

    def test_database(self):
        initialize_database(":memory:")

        cdn1 = CDN.create(id="cdn1", name="Sample CDN", edge="1.2.3.4")
        cdn2 = CDN.create(id="cdn2", name="Sample CDN2", edge="1.2.3.5")
        host1 = Host.create(hostname="first.host", cdn=cdn1)
        host2 = Host.create(hostname="second.host", cdn=cdn2)
        host3 = Host.create(hostname="third.host", cdn=cdn1)

        self.assertEqual([host1, host2, host3], list(Host.select()))
        self.assertEqual([host1, host3], Host.select().where(Host.cdn == cdn1))
        self.assertEqual([host1, host3], Host.select().join(CDN).where(CDN.id == 'cdn1'))
        self.assertEqual(host2, Host.get(Host.cdn == cdn2))

        self.assertEqual([], CDN.select().where(CDN.id == "doesntexist"))
        with self.assertRaises(DoesNotExist):
            CDN.get(CDN.id == "doesntexist")
