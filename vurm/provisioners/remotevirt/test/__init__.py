
import imp
import sys
import os



class MockedModule(object):

    def __init__(self, moduleName, modulePath):
        self.moduleName = moduleName
        self.modulePath = modulePath
        self.install()


    def find_module(self, fullname, path=None):
        if fullname == self.moduleName:
            return self


    def load_module(self, fullname):
        fh = open(self.modulePath)
        suffix = ('.py', 'U', 1)

        try:
            return imp.load_module(fullname, fh, fh.name, suffix)
        finally:
            fh.close()

        raise ImportError


    def install(self):
        sys.meta_path.insert(0, self)


MockedModule('libvirt', os.path.dirname(__file__) + '/libvirt_mock.py')
