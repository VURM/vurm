


from vurm import settings

from twisted.trial import unittest
from twisted.python import filepath


CONFIG1 = """
[section1]
loaded=True
"""

CONFIG2 = """
[section2]
loaded=True
"""

CONFIG3 = """
[section3]
loaded=True
"""



class SettingsTestCase(unittest.TestCase):

    def setUp(self):
        self.config1 = filepath.FilePath(self.mktemp())

        with self.config1.open('w') as fh:
            fh.write(CONFIG1)


        self.config2 = filepath.FilePath(self.mktemp())

        with self.config2.open('w') as fh:
            fh.write(CONFIG2)


        self.config3 = filepath.FilePath(self.mktemp())

        with self.config3.open('w') as fh:
            fh.write(CONFIG3)


    def tearDown(self):
        self.config1.remove()
        self.config2.remove()
        self.config3.remove()


    def test_empty(self):
        conf = settings.loadConfig(defaults=[])

        self.assertEquals(conf.sections(), [])


    def test_pathOnly(self):
        conf = settings.loadConfig(self.config1, defaults=[])

        self.assertEquals(conf.sections(), ['section1'])
        self.assertTrue(conf.getboolean('section1', 'loaded'))


    def test_defaultsOnly(self):
        conf = settings.loadConfig(defaults=[self.config1.path,
                self.config2.path, self.config3.path])

        self.assertIn('section1', conf.sections())
        self.assertTrue(conf.getboolean('section1', 'loaded'))

        self.assertIn('section2', conf.sections())
        self.assertTrue(conf.getboolean('section1', 'loaded'))

        self.assertIn('section3', conf.sections())
        self.assertTrue(conf.getboolean('section1', 'loaded'))


    def test_pathAndDefaults(self):
        conf = settings.loadConfig(self.config1, defaults=[self.config2.path,
                self.config3.path])

        self.assertIn('section1', conf.sections())
        self.assertTrue(conf.getboolean('section1', 'loaded'))

        self.assertIn('section2', conf.sections())
        self.assertTrue(conf.getboolean('section1', 'loaded'))

        self.assertIn('section3', conf.sections())
        self.assertTrue(conf.getboolean('section1', 'loaded'))
