"""
Interfaces and utilities to work with pluggable resource provisioners to
dynamically adding physical and/or virtual resources to SLURM.
"""



# Shut PyLint to complain about classes not having __init__ methods. These are
# interfaces.
# pylint: disable-msg=W0232

# Shut PyLint to complain about methods not having 'self' in their arguments.
# These are interfaces.
# pylint: disable-msg=E0213,E0211



from zope.interface import Interface, Attribute



class IResourceProvisioner(Interface):  # pragma: no cover
    """
    Base interface to be implemented by all provisioner classes.
    """

    def getNodes(count, **kwargs):
        """
        Creates *count* nodes and returns a **list of deferreds**, each one
        calling back with the respective INode instance as soon as it is ready
        to be launched.

        If the provisioner can't allocate resources for all *count* nodes, less
        than *count* can be returned. The vurm controller will take care to
        ask for the remaining nodes to other providers.

        Note that the slurm daemon does not have to run on the returned nodes
        until the INode.spawn method is called, but each node shall have the
        resources it needs granted for usage.

        This allows to get a set of nodes guaranteed to have the necessary
        resources to be started and then defer to the vurm controller the
        decision of *when* they have to be started.

        Additional keyword arguments can be passed to this method; the
        implementation has to be able to use the needed arguments and ignore
        the additional ones, by providing adequate fallbacks if a certain value
        is not defined.

        Keyword arguments are used to provide additional directives to the
        provisioner, as for example a disk image to use to boot a virtual
        machine. Such an argument would be ignored by a provisioner running
        nodes on physical machines.
        """



class INode(Interface):  # pragma: no cover
    """
    A model representing a single physical or virtual node to be provided to
    SLURM.
    """

    nodeName = Attribute("""The NodeName entry for this node in the slurm
                            configuration file""")

    hostname = Attribute("""The hostname to which the slurm controller deamon
                            will connect to to reach this node""")

    port = Attribute("""The port on which the slurmd related to this node has
                        to listen for incoming connections""")


    def getConfigEntry():
        """
        Returns the line which has to be added to the ``slurmctld``
        configuration file for this node to be recoqgnized as such.
        """


    def spawn():
        """
        Does all what necessary to start the slurmd daemon for this node and
        having it registered to the slurm controller.

        The spawned slurm daemon will listen on the given port and register to
        the slurm controller daemon using the provided name.

        """


    def release():
        """
        Releases all resources currently allocated to this node. If necessary,
        this method causes the slurm daemon to terminate.
        """
