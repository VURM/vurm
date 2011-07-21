from twisted.protocols import amp


__all__ = ['CreateVirtualCluster', 'DestroyVirtualCluster', ]



class CreateVirtualCluster(amp.Command):
    arguments = [
        ('size', amp.Integer()),
        ('minSize', amp.Integer(optional=True)),
    ]
    response = [
        ('clusterName', amp.String()),
    ]



class DestroyVirtualCluster(amp.Command):
    arguments = [
        ('clusterName', amp.String()),
    ]


class DestroyAllVirtualClusters(amp.Command):
    pass
