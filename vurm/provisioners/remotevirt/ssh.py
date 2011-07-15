
import struct

from twisted.conch.ssh import transport, connection, userauth, channel, common, filetransfer
from twisted.internet import defer



class RemoteCommandFailed(Exception):
    def __init__(self, exitCode, output):
        self.exitCode = exitCode
        self.output = output



class ClientTransport(transport.SSHClientTransport):

    def __init__(self, username, key):
        self.username = username
        self.key = key
        self.serviceRequests = []
        self.service = ClientConnection()


    def transferFile(self, fh, remotePath):
        d = defer.Deferred()
        self.service.openChannelWhenReady(FileTransferChannel(fh, remotePath,
                d, conn=self.service))
        return d


    def executeCommand(self, command):
        d = defer.Deferred()
        self.service.openChannelWhenReady(CommandChannel(command, d,
                conn=self.service))
        return d


    def verifyHostKey(self, pubKey, fingerprint):
        # TODO: Check that the fingerprint matches the saved one (is this
        #       really necessary?)
        return defer.succeed(True)


    def connectionSecure(self):
        self.requestService(PublickeyAuth(self.username, self.key,
                self.service))



class PublickeyAuth(userauth.SSHUserAuthClient):

    def __init__(self, user, key, connection):
        userauth.SSHUserAuthClient.__init__(self, user, connection)
        self.key = key


    def getPassword(self, prompt=None):
        return


    def getPublicKey(self):
        print self.key.public().toString('OPENSSH')
        return self.key.public().blob()


    def getPrivateKey(self):
        return defer.succeed(self.key.keyObject)



class ClientConnection(connection.SSHConnection):

    def __init__(self):
        connection.SSHConnection.__init__(self)

        self.channelRequests = []
        self.ready = False


    def serviceStarted(self):
        self.ready = True

        reqs, self.channelRequests = self.channelRequests, []
        for args, kwargs in reqs:
            self.openChannel(*args, **kwargs)


    def openChannelWhenReady(self, *args, **kwargs):
        if self.ready:
            self.openChannel(*args, **kwargs)
        else:
            self.channelRequests.append((args, kwargs))



class CommandChannel(channel.SSHChannel):

    name = 'session'


    def __init__(self, command, deferred, *args, **kwargs):
        channel.SSHChannel.__init__(self, *args, **kwargs)
        self.deferred = deferred
        self.command = command
        self.exitStatus = 0
        self.reply = ''


    def channelOpen(self, data):
        self.conn.sendRequest(self, 'exec', common.NS(self.command))
        self.conn.sendEOF(self)


    def request_exit_status(self, data):
        status = struct.unpack('>L', data)[0]
        self.exitStatus = status
        self.loseConnection()


    def dataReceived(self, data):
        self.reply += data


    def closed(self):
        if self.exitStatus:
            self.deferred.errback(RemoteCommandFailed(self.exitStatus,
                    self.reply))
        else:
            self.deferred.callback(self.reply)



class FileTransferChannel(channel.SSHChannel):

    name = 'session'

    def __init__(self, fh, remotePath, deferred, *args, **kwargs):
        channel.SSHChannel.__init__(self, *args, **kwargs)
        self.deferred = deferred
        self.fh = fh
        self.remotePath = remotePath


    @defer.inlineCallbacks
    def channelOpen(self, data):
        print "CHANNEL OPENED"
        yield self.conn.sendRequest(self, 'subsystem', common.NS('sftp'),
                wantReply=1)
        print "GOT SUBSYSTEM"
        self.client = SFTPClient(self.fh, self.remotePath, self.deferred)
        self.client.makeConnection(self)
        self.dataReceived = self.client.dataReceived



class SFTPClient(filetransfer.FileTransferClient):

    chunkSize = 1024


    def __init__(self, fh, remotePath, deferred):
        filetransfer.FileTransferClient.__init__(self)
        self.fh = fh
        self.remotePath = remotePath
        self.deferred = deferred


    def packet_STATUS(self, data):
        # TODO: Remove this as soon as #3009 is released as part of mainstream
        #       twisted distributions (keep an eye on debian's version).
        #       Reference: http://twistedmatrix.com/trac/ticket/3009
        d, data = self._parseRequest(data)
        code, = struct.unpack('!L', data[:4])
        data = data[4:]

        if data:
            msg, data = filetransfer.getNS(data)
            lang = filetransfer.getNS(data)
        else:
            msg, lang = None, None

        if code == filetransfer.FX_OK:
            d.callback((msg, lang))
        elif code == filetransfer.FX_EOF:
            d.errback(EOFError(msg))
        elif code == filetransfer.FX_OP_UNSUPPORTED:
            d.errback(NotImplementedError(msg))
        else:
            d.errback(filetransfer.SFTPError(code, msg, lang))


    @defer.inlineCallbacks
    def connectionMade(self):
        flags = filetransfer.FXF_WRITE | filetransfer.FXF_CREAT
        flags |= filetransfer.FXF_TRUNC
        remoteFile = yield self.openFile(self.remotePath.path, flags, {})

        offset = 0
        while True:
            chunk = self.fh.read(self.chunkSize)

            if not chunk:
                break
            else:
                yield remoteFile.writeChunk(offset, chunk)
                offset += self.chunkSize

        yield defer.maybeDeferred(remoteFile.close)
        self.deferred.callback(None)
