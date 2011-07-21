"""
Abstractions to make working with libvirt feel more pythonic.
"""

from __future__ import absolute_import

import libvirt

from lxml import etree

from twisted.python import filepath


# Shut PyLint to complain about undefined names in the logging module (the
# __future__ import is not correctly handled).
# pylint: disable-msg=E1101


__all__ = ['open', 'DomainDescription', 'LibvirtError']


LibvirtError = libvirt.libvirtError


class LibvirtConnectionContextManager(object):
    def __init__(self, connectionURI):
        self.connectionURI = connectionURI
        self.connection = libvirt.open(self.connectionURI)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()

open = LibvirtConnectionContextManager



class DomainDescription(object):

    def __init__(self, xml):
        if isinstance(xml, basestring):
            self.document = etree.fromstring(xml)
        else:
            self.document = xml


    def getName(self):
        return self.document.find('name').text


    def getRootImagePath(self):
        path = self.document.find(
                'devices/disk[@device="disk"]/source[@file]').get('file')

        return filepath.FilePath(path)


    def setRootImagePath(self, path):
        element = self.document.find(
                'devices/disk[@device="disk"]source[@file]')

        element.set('file', path.path)


    def addSerialToTCPDevice(self, host, port, mode='connect'):
        device = etree.Element('serial')
        device.set('type', 'tcp')

        source = etree.Element('source')
        source.set('mode', mode)
        source.set('host', host)
        source.set('service', str(port))
        device.append(source)

        target = etree.Element('target')
        target.set('port', '1')
        device.append(target)

        self.document.find('devices').append(device)


    def __str__(self):
        return etree.tostring(self.document)
