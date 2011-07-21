from twisted.protocols import amp

from lxml import etree


__all__ = ['CreateDomain', 'DestroyDomain', 'SpawnSlurmDaemon', ]



class XMLDocument(amp.Unicode):

    def fromString(self, inString):
        return etree.fromstring(amp.Unicode.fromString(self, inString))


    def toString(self, inObject):
        return amp.Unicode.toString(self, etree.tostring(inObject))



class CreateDomain(amp.Command):
    arguments = [
        ('description', XMLDocument()),
    ]
    response = [
        ('hostname', amp.String()),
    ]



class DestroyDomain(amp.Command):
    arguments = [
        ('nodeName', amp.String()),
    ]



class SpawnSlurmDaemon(amp.Command):
    arguments = [
        ('nodeName', amp.String()),
        ('slurmConfig', amp.String()),
    ]
