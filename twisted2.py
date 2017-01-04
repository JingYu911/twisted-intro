#coding:utf-8
#xiaorui.cc
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
import os,sys
from twisted.python import threadable; threadable.init(1)
deferred =deferToThread.__get__
import time
def todoprint_(result):
  print result
def running():
  "Prints a few dots on stdout while the reactor is running."
  sys.stdout.write("."); sys.stdout.flush()
  print '.'
  reactor.callLater(.1, running)
@deferred
def sleep(sec):
  "A blocking function magically converted in a non-blocking one."
  print 'start sleep %s'%sec
  time.sleep(sec)
  print '\nend sleep %s'%sec
  return "ok"
def test(n,m):
  print "fun test() is start"
  m=m
  vals = []
  keys = []
  for i in xrange(m):
    vals.append(i)
    keys.append('a%s'%i)
  d = None
  for i in xrange(n):
    d = dict(zip(keys, vals))
  print "fun test() is end"
  return d
if __name__== "__main__":
#one
  sleep(10).addBoth(todoprint_)
  reactor.callLater(.1, running)
  reactor.callLater(3, reactor.stop)
  print "go go !!!"
  reactor.run()
#two
  aa=time.time()
  de = defer.Deferred()
  de.addCallback(test)
  reactor.callInThread(de.callback,10000000,100 )
  print time.time()-aa
  print "我这里先做别的事情"
  print de
  print "go go end"
