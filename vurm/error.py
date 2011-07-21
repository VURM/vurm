"""
VURM related errors.
"""



from twisted.spread import pb



class RemoteVurmException(pb.Error):
    """
    A marker class to mark exceptions having this class as superclass as
    expected on the server side. They will be transparently raised remotely and
    not logged by the server.

    The remote user can access the type and the message of these exceptions.

    NOTE: The traceback is hidden for these types of exceptions too. It is
          possible to activate traceback passing for **ALL** exception types
          by setting the ``debug`` directive to ``True`` in the configuration
          file.
    """



class InsufficientResourcesException(RemoteVurmException):
    """
    Raised when the current provisioners fail to fullfill a request for a given
    operation due to a lack of resources.
    """



class ReconfigurationError(RemoteVurmException):
    """
    Raised when the controller is not able to correctly reconfigure the SLURM
    controller.
    """



class InvalidClusterName(RemoteVurmException):
    """
    Raised when an operation which requires a cluster name fails because the
    given cluster name is either invalid or was not found.
    """



class UnknownDomain(RemoteVurmException):
    """
    Raised when an unknown domain is registered or requested.
    """



class ConnectError(RemoteVurmException):
    """
    Raised when a connection attempt fails.
    """
