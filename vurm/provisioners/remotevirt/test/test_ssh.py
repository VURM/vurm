import struct
import shlex
import getpass

from cStringIO import StringIO

from twisted.trial import unittest
from twisted.cred import portal
from twisted.conch.ssh import factory, session, filetransfer, keys
from twisted.conch import avatar, interfaces, checkers
from twisted.internet import reactor, defer, protocol, error
from twisted.python import filepath, failure

from zope.interface import implements

from vurm.provisioners.remotevirt import ssh



PUBLIC_KEY = """ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAuk1btr7Povi0g1VgmZIedhte\
yvQYvZHCXy8xMiFcTAh7Mn7TzRg2R6BVHNFEoPtU2oHQ9fwx8XNFkm9MjHcK52tHHS5ax9d7Yhi+\
EJ/DsGVbFTInxSy5y3a4Vvp8NfwysF8r/xqlryigRtZzSCsQRHfsth9SApOslqFnWFM8K1vYkPtg\
Wl7DPyf1DmyueaeJZgWPV+SZUfGP6waWtYKbD8OCdGf7YKYJ6JtLW+ykBqHgE/RvVGFpvXNbYPUl\
NOeyl2GBciMSUaJ1Z3vSevajiBQdKUv8HYjeaRshoGL68y8OpvHIzxB8J62fiL/MQuIrwkPtaVGx\
170MA8HtKAihBQ=="""



PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQEAuk1btr7Povi0g1VgmZIedhteyvQYvZHCXy8xMiFcTAh7Mn7T
zRg2R6BVHNFEoPtU2oHQ9fwx8XNFkm9MjHcK52tHHS5ax9d7Yhi+EJ/DsGVbFTIn
xSy5y3a4Vvp8NfwysF8r/xqlryigRtZzSCsQRHfsth9SApOslqFnWFM8K1vYkPtg
Wl7DPyf1DmyueaeJZgWPV+SZUfGP6waWtYKbD8OCdGf7YKYJ6JtLW+ykBqHgE/Rv
VGFpvXNbYPUlNOeyl2GBciMSUaJ1Z3vSevajiBQdKUv8HYjeaRshoGL68y8OpvHI
zxB8J62fiL/MQuIrwkPtaVGx170MA8HtKAihBQIBIwKCAQBlIq4hYETU0Cd6fs4K
OWD+SV9YO13jQH91gATDcTIapYS1AwVDc4suMndYyV/FGrkI52LOrXoynalswBOc
tabVZh9KWv4Uts3zbIRvbKwPTPbuP8xyWhu3mDgvN4VB4K3NdX5IqBDMzOlLBrOc
NKJuT7sDx9wQBwXrXu71bwNn/bucN2HbLgysde+H6Xl+Ddh9xzyPriffiWxOJAT4
KK0zkXd3wKvikpOmk2C6/5MbSrSMI7Nhkt8CCsfSrZLbATHHMzR9zQP5sAuUsANa
L4Momy3p9oPt85OUkDOggLRfDHHxcOOJYwZghTnLs+tHYLK7FHwYveyEKBPkr4K0
O5hLAoGBAN7LLbBHjsitx777hdMtAhiFSL7F0HFm2YbhV9c2z0NTeVrK9OMgWj/2
18bzKqo5MBR/8j4dmeKO1FuUkekjDcj79Nj0xAsE5mXvgqPf8Yx9+sZCiEMNinzY
Ew9PWpbFYvBrk776O360bSlGIqnu5bIAM4Ubl5Vphvpen6RpPLPVAoGBANYR03UT
RUGJlG9b5+4GICVyTczMxd53vJJeyrZXP/27nIF8ArMzItTnVbdGLoyAOQW6Ryok
uPnaBGdIS+otlFgEDlVEymvEJuypcZQ4QccdnSq+hFo+tvNkajnzeZ6nIPt+m48b
HpNjIqABRDsGZUt26qwgJltE3sSUFN62KEBxAoGBANhtmhj1DlyLjtbIc19tjQHg
j89D0c0/VvgOGtEQrBWESgBtYutD/+ZdgSeqY/XRJ2RfCJQcwV+98tye9CRN8CJT
1+izQhlVN5Y5H9JkhD9Vzwm8+WW1YfWes231UK+4br2qVQKp8Kb4agrWatD2sz8z
ZT9547W2+CZqjHPT8dNDAoGAdDWQDFrrFPLqLdLOXKQ9VigbmxATpKdmXhYzh45z
MfghwqJn3Z9qrhcuiBAn5d805domodlrutVwGs95qwLM31KosfIkviinaofekkps
2c4/YFjLgXKAksF7fot8iVNprRjYGnxvrxiPI6jqhnEvrJ+j9wojc1/mpTpxurqo
IvsCgYBJ8cuw/mYGBDxVkdyJbCLS8Qc2oto6qpEEBpaPERFr1/JOdzNyMR1BOcV6
WpQx+4/Tzu1JalMTsNllfPhqHL/Jr7P8SOGio19sLPQYirWhYn5wM6ACEO0QMQiS
d2LrKkwxpj+V9RNN8VDiNZF8sITgfKGc7yy1IY+DinyfgqvE8A==
-----END RSA PRIVATE KEY-----"""



class TestFile(object):
    def __init__(self, name):
        self.name = name
        self.value = ''
        self.closed = False


    def writeChunk(self, offset, chunk):
        # TODO: Ignoring offset
        self.value += chunk


    def close(self):
        self.closed = True



class TestUser(avatar.ConchUser):
    implements(interfaces.ISFTPServer, interfaces.ISession)

    def __init__(self, server):
        avatar.ConchUser.__init__(self)

        self.server = server
        self.server.users.append(self)

        self.executedCommands = []
        self.openedFiles = []

        self.loggedOut = False

        self.channelLookup['session'] = session.SSHSession
        self.subsystemLookup['sftp'] = filetransfer.FileTransferServer


    def logout(self):
        self.loggedOut = True

    # ISession methods

    def getPty(self, term, windowSize, modes):
        pass

    def openShell(self, proto):
        pass

    def execCommand(self, proto, command):
        self.executedCommands.append(command)

        self.session = proto.session

        command = shlex.split(command)

        if hasattr(self, 'command_' + command[0]):
            ret = getattr(self, 'command_' + command[0])(*command[1:])
            if not ret:
                ret = 0
        else:
            ret = 0

        proto.transport = self
        proto.session.conn.sendRequest(proto.session, 'exit-status',
                struct.pack('!L', ret))

    def command_retcode(self, code):
        return int(code)

    def command_echo(self, *args):
        self.session.write(' '.join(args))

    def windowChanged(self, newWindowSize):
        pass

    def eofReceived(self):
        pass

    def closed(self):
        pass

    # Transport methods

    def loseConnection(self):
        pass

    # ISFTPServer methods

    def openFile(self, filename, flags, attrs):
        self.openedFiles.append(TestFile(filename))
        return self.openedFiles[-1]



class TestRealm(object):
    def __init__(self, server):
        self.server = server


    def requestAvatar(self, avatarId, mind, *ifaces):
        user = TestUser(self.server)
        return interfaces.IConchUser, user, user.logout



class TestKeyAuthChecker(checkers.SSHPublicKeyDatabase):
    def __init__(self, path):
        self.keysPath = path

    def getAuthorizedKeysFiles(self, credentials):
        return [self.keysPath]



class TestSSHServer(object):

    def __init__(self, key, keysPath):
        self.key = key
        self.port = None
        self.keysPath = keysPath
        self.users = []


    def startListening(self, port=0):
        checker = TestKeyAuthChecker(self.keysPath)

        f = factory.SSHFactory()
        f.privateKeys = {'ssh-rsa': self.key}
        f.publicKeys = {'ssh-rsa': self.key.public()}
        f.portal = portal.Portal(TestRealm(self))
        f.portal.registerChecker(checker)

        self.port = reactor.listenTCP(port, f)
        return self.port.getHost().port


    def stopListening(self):
        self.port.stopListening()


class SSHClientTestCase(unittest.TestCase):


    @defer.inlineCallbacks
    def setUp(self):
        key = keys.Key.fromString(PRIVATE_KEY)

        self.tmpKeys = filepath.FilePath(self.mktemp())

        with self.tmpKeys.open('w') as fh:
            fh.write(key.public().toString('OPENSSH'))

        self.server = TestSSHServer(key, self.tmpKeys)
        port = self.server.startListening()

        creator = protocol.ClientCreator(reactor, ssh.ClientTransport,
                getpass.getuser(), key)
        self.client = yield creator.connectTCP('localhost', port)


    @defer.inlineCallbacks
    def tearDown(self):
        yield self.client.disconnect()
        self.server.stopListening()


    @defer.inlineCallbacks
    def test_loseConnectionErr(self):
        yield self.client.disconnect()

        d = self.client.disconnectionDeferred = defer.Deferred()

        def disconnect():
            self.client.connectionLost(failure.Failure(error.ConnectionLost()))
        reactor.callLater(.1, disconnect)

        yield self.failUnlessFailure(d, error.ConnectionLost)


    @defer.inlineCallbacks
    def test_loseConnectionOk(self):
        self.client.loseConnection()

        d = defer.Deferred()
        reactor.callLater(.5, d.callback, None)
        yield d

        yield self.client.disconnect()


    @defer.inlineCallbacks
    def test_executeCommandOk(self):
        result = yield self.client.executeCommand('echo this has to come back')
        self.assertEquals(result, 'this has to come back')


    @defer.inlineCallbacks
    def test_executeTriple(self):
        d1 = self.client.executeCommand('echo res1')
        d2 = self.client.executeCommand('echo res2')
        res1 = yield d1
        res2 = yield d2
        res3 = yield self.client.executeCommand('echo res3')

        self.assertEquals(res1, 'res1')
        self.assertEquals(res2, 'res2')
        self.assertEquals(res3, 'res3')


    @defer.inlineCallbacks
    def test_filetransfer(self):
        fh = StringIO('this is the file to transfer to the remote side')
        yield self.client.transferFile(fh, filepath.FilePath('/remote'))

        remoteFile = self.server.users[0].openedFiles[0]
        self.assertEquals(remoteFile.value, fh.getvalue())


    def test_executeCommandFail(self):
        return self.failUnlessFailure(
            self.client.executeCommand('retcode 1'),
            ssh.RemoteCommandFailed
        )
