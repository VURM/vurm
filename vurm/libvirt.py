"""
Abstractions to make working with libvirt feel more pythonic.
"""

from __future__ import absolute_import

import libvirt
import uuid
from libvirt import libvirtError as LibvirtError

from lxml import etree

from twisted.python import filepath


# Shut PyLint to complain about undefined names in the logging module (the
# __future__ import is not correctly handled).
# pylint: disable-msg=E1101


__all__ = ['open', 'DomainDescription', 'LibvirtError']


class LibvirtConnectionContextManager(object):
    def __init__(self, connectionURI):
        self.connectionURI = connectionURI
        self.connection = None

    def __enter__(self):
        self.connection = libvirt.open(self.connectionURI)
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


    def getUUID(self):
        try:
            return self.document.find('uuid').text
        except AttributeError:
            return None


    def setUUID(self, uuid):
        element = self.document.find('uuid')

        if element is None:
            element = etree.Element("uuid")
            self.document.append(element)

        element.text = uuid


    def getOrSetUUID(self):
        domainUUID = self.getUUID()

        if not domainUUID:
            domainUUID = str(uuid.uuid1())
            self.setUUID(domainUUID)

        return domainUUID


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
