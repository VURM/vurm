.. _architecture:


Architecture
============

The VURM framework was built from ground up to support extensive customization. It features pluggable and stackable resource provisioner and exposes numerous configuration options.

.. todo::

   Move a rewrite of this to the final report

.. todo::

   Add examples of further customization possibilities

To a great extent, these extension capabilities are made possible by the underlying architecture; this section aims to provide a global view of its implementation and insights into the most important details.

The class diagram provides an overview of the current implementation and will be referenced when discussed in further details in the subsections below.

.. image:: /assets/architecture-overview.png


The VURM controller
-------------------

The controller is the main entry point to the whole system and is responsible for a great part of its management. It is capable to create and destroy virtual clusters on users request by keeping track of them, requesting resource reservation, reconfiguring SLURM and much more.

A controller owns a list of provisioners which are used to reserve and allocate
specific resource types. When a request for a new virtual cluster comes in, the controller iterates over the provisioners in the order they were registered and asks them for nodes until the desired size is reached or the provisioners list is exhausted.

If, when the provisioners list is exhausted, the number of allocated nodes does not reach the minimum requested size, all nodes are deallocated and an error reported back to the client.

The following sequence diagram illustrates in more detail how a cluster is created.

.. image:: /assets/provisioning-workflow.png

.. note::

   The UML ``loop`` fragment with the alternative operand is a particularity of Python. The ``else`` clause get executed if and only if the loop was not interrupted by a ``break`` statement.
   
   More details about the exact semantics can be found on the python `python documentation`_.

.. _`python documentation`: http://docs.python.org/reference/compound_stmts.html#the-for-statement
   