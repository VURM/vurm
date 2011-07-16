


class libvirtError(Exception):
    def __init__(self, errorCode):
        self.errorCode = errorCode

    def get_error_code(self):
        return self.errorCode

    def get_error_message(self):
        return ''


class Domain(object):
    destroyed = False

    def destroy(self):
        self.destroyed = True


class Hypervisor(object):

    lastDomain = None
    descriptions = {}

    def __init__(self, uri):
        action = uri.split(':///', 1)[1]

        if action.startswith('error'):
            code = int(action.split('/')[1])
            raise libvirtError(code)

        if action.startswith('called'):
            self.key = action.split('/')[1]

        self.uri = uri
        self.closed = False


    def lookupByName(self, name):
        if name == 'inexistent':
            raise libvirtError(0)
        elif name == 'existent':
            Hypervisor.lastDomain = Domain()
            return Hypervisor.lastDomain


    def createLinux(self, desc, flag):
        Hypervisor.descriptions[self.key] = desc


    def close(self):
        self.closed = True

open = Hypervisor
