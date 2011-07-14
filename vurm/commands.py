from twisted.protocols import amp

from lxml import etree


__all__ = ['CreateDomain', 'DestroyDomain', 'SpawnSlurmDaemon', ]



class CreateVirtualCluster(amp.Command):
    arguments = [
        ('size', amp.Integer()),
        ('minSize', amp.Integer(optional=True)),
    ]
    response = [
        ('cluserName', amp.String()),
    ]



class DestroyVirtualCluster(amp.Command):
    arguments = [
        ('cluserName', amp.String()),
    ]
