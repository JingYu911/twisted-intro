from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import reactor

class Echo(Protocol):
    def connectionMade(self):
        self.transport.write("hi, sever")

    def dataReceived(self, data):
        print data
class EchoClientFactory(ClientFactory):
    def startedConnecting(self,connector):
        print "connection starting..."
    def buildProtocol(self,addr):
        print addr

        return Echo()
    def clientConnectionLost(self,connector,reason):
        print "lose reason:", reason
    def clientConnectionFailed(self,connector,reason):
        print "failed reason:",reason
def fun():
    print "callLater"
reactor.callLater(1,fun)
reactor.callLater(3,fun)
reactor.connectTCP('127.0.0.1',8001,EchoClientFactory())
reactor.run()
