"""
VURM related errors.
"""



from twisted.spread import pb



class RemoteVurmException(pb.Error):
    pass



class InsufficientResourcesException(RemoteVurmException):
    pass



class ReconfigurationError(RemoteVurmException):
    pass



class InvalidClusterName(pb.Error):
    pass
