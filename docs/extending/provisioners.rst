Custom resource provisioners
============================

VURM supports the use of custom resource provisioners. Additionally, multiple provisioners can be stacked one upon the other, each additional provisioners acting as a fallback if the former runs out of resources.

The resource provisioners to use are defined during the ``VurmController`` instantiation as illustrated in the following code example::

   from vurm import controller
   from vurm.provisioners import multilocal, kvm

   # ... more imports and setup code

   daemon = controller.VurmController(config, [
       kvm.Provisioner(reactor, config, use_defaults=False),
       multilocal.Provisioner(reactor, config),
   ])

   # ... code to publish the controller daemon

The controller will always try to get the resources from the first found in the list, continuing with the second if needed until either the necessary resources where allocated or the provisioners list exhausted.

All resource provisioner instances need to either provide the IResourceProvisioner interface or being able to be adapted to it. Let's first take a look at the interface and then at how a new provisioner can be implemented:

.. autointerface:: vurm.resources.IResourceProvisioner
   :members:

As noted in the ``getNodes`` method documentation, it has to return a list of deferreds which fire with an object providing the ``INode`` interface. The API for this interface is as follows:

.. autointerface:: vurm.resources.INode
   :members:

A good starting point to create your custom IResourceProvisioner class are the currently existing implementations to be found in the `provisioners`_ package, and in particular the `multilocal`_ module, which provides one of the simplest implementations.

.. _`multilocal`: http://jonathan.stoppani.name/projects/vurm/static/apidocs/


.. _`provisioners`: http://jonathan.stoppani.name/projects/vurm/static/apidocs/vurm.provisioners-module.html




.. note::

   This guide will not cover component adaptation, the Twisted manual has some good documentation about this topic here: `Components: Interface and Adapters`_


   .. _`Components: Interface and Adapters`: http://twistedmatrix.com/documents/current/core/howto/components.html
