from newdominion.settings import * 
from newdominion.dominion.models import *
from django.db import models, connection, transaction
from math import *

from django.db.models import Q
import django

import json
import datetime
import operator
import random
import time
import redis, os
import cPickle
from pprint import pprint

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def insertrows(table,rows,values,intransaction=False):
  """
  >>> #insertrows('dominion_fleet_inviewof',('fleet_id','user_id'),[('1','1')])
  1
  """
  if len(values) == 0:
    return 0
  
  for row in values:
    for i in xrange(len(row)):
      if type(row[i])==str and ' ' in row[i]:
        row[i] = "'"+row[i]+"'"

  cursor = connection.cursor()
  query = ""

  """
  if STAGING == False and DEBUG == True:
    counter = 0
    for row in values:
      row = list(row)
      for i in xrange(len(row)):
        if row[i] == 'true':
          row[i] = '1'
        if row[i] == 'false':
          row[i] = '0'
          
      counter += 1
      if counter%100 == 0:
        print str(counter)
      #do it a row at a time for sqlite...
      query = 'INSERT INTO "%s" (%s) VALUES (%s);\n' % (table,
                                                        ', '.join(rows), 
                                                        ', '.join(row))
      cursor.execute(query)
  """      
  #"dominion_fleet_inviewof"
  #"fleet_id", "user_id"
  for valuelist in chunks(values,500):
    query = []
    for i in valuelist[:-1]:
      query.append('(' + ','.join(i) + '),')
    query.append('('+ ','.join(valuelist[-1]) + ');')
    with transaction.atomic():
      query = 'INSERT INTO "%s" (%s) VALUES\n' % (table,
                                                  ', '.join(rows)) + '\n'.join(query)
      cursor.execute(query)
  return len(values)


class Report():
  id = 0
  reportfiles = {} 
  def __init__(self,userid):
    if userid == None:
      userid = 0
    self.id = userid
    self.setslot('w')
  def append(self,output):
    self.setslot('a')
    Report.reportfiles[self.slot()]['file'].write((output+"\n").encode('utf-8'))
  def getreport(self):
    self.closefile()
    self.reportfile = open(REPORTDIR+"report"+str(self.id),'r')
    return self.reportfile.read()
  def remove(self):
    os.remove(REPORTDIR+"report"+str(self.id))
  def slot(self):
    return self.id % 50
  def closefile(self):
    if Report.reportfiles.has_key(self.slot()) and \
       Report.reportfiles[self.slot()]['id'] == self.id:
      Report.reportfiles[self.slot()]['file'].close()

  def setslot(self,mode):
    if Report.reportfiles.has_key(self.slot()) and \
       Report.reportfiles[self.slot()]['id'] != self.id:
      Report.reportfiles[self.slot()]['file'].close()
      del Report.reportfiles[self.slot()]
    if not Report.reportfiles.has_key(self.slot()):
      Report.reportfiles[self.slot()] = {'id':self.id, 
                                         'file':open(REPORTDIR+"report"+str(self.id),
                                                     mode)}
    

class BoundingBox():
  xmin = 10000.0
  ymin = 10000.0
  xmax = -10000.0
  ymax = -10000.0
  def __init__(self,stuff):
    if stuff[0] != None:
      self.xmin = stuff[0]
      self.ymin = stuff[1]
      self.xmax = stuff[2]
      self.ymax = stuff[3]
    else:
      self.xmin = 10000.0
      self.ymin = 10000.0
      self.xmax = -10000.0
      self.ymax = -10000.0
    

  def expand(self,expand):
    self.xmin -= expand
    self.xmax += expand
    self.ymin -= expand
    self.ymax += expand

  def printbb(self):
    print "bb = (%d,%d) - (%d,%d)" % (self.xmin,self.ymin,
                                      self.xmax,self.ymax)

  def addpoint(self,x,y):
    if x == None or y == None:
      return
    if x < self.xmin:
      self.xmin = x
    if y < self.ymin:
      self.ymin = y
    if x > self.xmax:
      self.xmax = x
    if y > self.ymax:
      self.ymax = y
      
  def intersection(self,other):
    minx = self.xmin if self.xmin > other.xmin else other.xmin
    miny = self.ymin if self.ymin > other.ymin else other.ymin
    maxx = self.xmax if self.xmax < other.xmax else other.xmax
    maxy = self.ymax if self.ymax < other.ymax else other.ymax
    return (minx,miny,maxx,maxy)

  def overlaps(self,other):
    if self.xmin == 10000 or self.ymin == 10000:
      return 0
    if self.xmin >= other.xmin and self.xmin <= other.xmax:
      if self.ymin >= other.ymin and self.ymin <= other.ymax:
        return 1
      if self.ymax >= other.ymin and self.ymax <= other.ymax:
        return 1
    if self.xmax >= other.xmin and self.xmax <= other.xmax:
      if self.ymin >= other.ymin and self.ymin <= other.ymax:
        return 1
      if self.ymax >= other.ymin and self.ymax <= other.ymax:
        return 1
    
    if other.xmin >= self.xmin and other.xmin <= self.xmax:
      if other.ymin >= self.ymin and other.ymin <= self.ymax:
        return 1
      if other.ymax >= self.ymin and other.ymax <= self.ymax:
        return 1
    if other.xmax >= self.xmin and other.xmax <= self.xmax:
      if other.ymin >= self.ymin and other.ymin <= self.ymax:
        return 1
      if other.ymax >= self.ymin and other.ymax <= self.ymax:
        return 1

    return 0


def gompertz(upperbound,displacement,rate,value):
  # upperbound = maximum output value
  # displacement = where curve starts (starts at displacement-2)
  # rate = steepness of curve
  # value = current value on curve
  return upperbound * math.e**(displacement*(math.e**((-1.0/rate)*value)))

def getdistanceobj(o1,o2):
  return getdistance(o1.x,o1.y,o2.x,o2.y)

def getdistance(x1,y1,x2,y2):
  return sqrt((x1-x2)*(x1-x2) + (y1-y2)*(y1-y2))

def expandsectors(sectors):
  """
  >>> expandsectors([100100])
  set([100099, 100100, 100101, 101099, 101100, 101101, 99099, 99100, 99101])
  >>> expandsectors([100100,100101])
  set([100099, 100100, 100101, 100102, 101099, 101100, 101101, 101102, 99099, 99100, 99101, 99102])
  >>> len(expandsectors([100100,100101,95095]))
  21
  """
  allsectors = dict([(int(x),1) for x in sectors])
  for sector in sectors:
    sector = int(sector)
    x = sector/1000
    y = sector%1000
    for i in range(x-1,x+2):
      for j in range(y-1,y+2):
        testsector = i*1000 + j
        if testsector not in allsectors:
          allsectors[testsector]=1
  return set(allsectors.keys())

def sectorsincircle(x,y,distance):
  # only works for distance < 5...
  sectorkeys = []
  sectorkeys.append((buildsectorkey(x,y)))
  
  if int(x/5.0) > int((x-distance)/5.0):
    sectorkeys.append((buildsectorkey(x-5,y)))
    if int(y/5.0) > int((y-distance)/5.0):
      sectorkeys.append((buildsectorkey(x-5,y-5)))
    elif int(y/5.0) < int((y+distance)/5.0):
      sectorkeys.append((buildsectorkey(x-5,y+5)))
  elif int(x/5.0) < int((x+distance)/5.0):
    sectorkeys.append((buildsectorkey(x+5,y)))
    if int(y/5.0) > int((y-distance)/5.0):
      sectorkeys.append((buildsectorkey(x+5,y-5)))
    elif int(y/5.0) < int((y+distance)/5.0):
      sectorkeys.append((buildsectorkey(x+5,y+5)))
  
  if int(y/5.0) > int((y-distance)/5.0):
    sectorkeys.append((buildsectorkey(x,y-5)))
  elif int(y/5.0) < int((y+distance)/5.0):
    sectorkeys.append((buildsectorkey(x,y+5)))
  return sectorkeys

def playernamestr(id):
  name = ""
  if localcache['players'].has_key(id):
    if localcache['players'][id].has_key('name'):
      name += localcache['players'][id]['name']
    if localcache['players'][id].has_key('racename'):
      name += " ("+localcache['players'][id]['racename']+")"
  return name

def nearbythingsbybbox(thing, bbox, otherowner=None):
  xmin = int(bbox.xmin/5.0)
  ymin = int(bbox.ymin/5.0)
  xmax = int(bbox.xmax/5.0)
  ymax = int(bbox.ymax/5.0)
  xr = xrange(xmin-1,xmax+1)
  yr = xrange(ymin-1,ymax+1)
  sectorkeys = []
  for i in xr:
    for j in yr:
      sectorkeys.append(i*1000 + j)
  if otherowner == "everyone":
    return thing.objects.filter(sector__in=sectorkeys)
  else:
    return thing.objects.filter(sector__in=sectorkeys,
                                owner = otherowner)

def nearbythings(thing, x, y, numexpands=0):
  sx = int(x)/5
  sy = int(y)/5
  sectors = [(((sx-1)*1000)+sy-1),
             (((sx-2)*1000)+sy),
             (((sx-1)*1000)+sy),
             (((sx-1)*1000)+sy+1),
             ((sx*1000)+sy-2),
             ((sx*1000)+sy-1),
             ((sx*1000)+sy),
             ((sx*1000)+sy+1),
             ((sx*1000)+sy+2),
             (((sx+1)*1000)+sy-1),
             (((sx+2)*1000)+sy),
             (((sx+1)*1000)+sy),
             (((sx+1)*1000)+sy+1)]
  if numexpands:
    for i in xrange(numexpands):
      sectors = list(expandsectors(sectors))

  if type(thing) == django.db.models.query.QuerySet:
    return thing.filter(sector__in=sectors)
  else:
    return thing.objects.filter(sector__in=sectors)


def nearbysortedthings(Thing,curthing, numexpands=0):
  nearby = list(nearbythings(Thing,curthing.x,curthing.y,numexpands))
  nearby.sort(lambda x,y:int((getdistanceobj(curthing,x) -
                              getdistanceobj(curthing,y))*100000 ))
  return nearby

def setextents(x,y,extents):
  x *= 5
  y *= 5
  if x < extents[0]:
    extents[0] = x
  if x > extents[2]:
    extents[2] = x
  if y < extents[1]:
    extents[1] = y
  if y > extents[3]:
    extents[3] = y
  return extents






def cullneighborhood(neighborhood):
  player = neighborhood['player']
  neighborhood['fbys'] = {}
  playersensers = []
  for planet in neighborhood['planets']:
    if planet.owner and planet.owner.id == player.id:
      playersensers.append({'x': planet.x, 'y': planet.y, 'r': planet.senserange()})

  for fleet in neighborhood['fleets']:
    if fleet.owner == player:
      playersensers.append({'x': fleet.x, 'y': fleet.y, 'r': fleet.senserange()})
    
  for f in neighborhood['fleets']:
    f.keep=0
    if f.owner == player:
      f.keep=1
      continue
    f.keep=0
    for s in playersensers:
      d = sqrt((s['x']-f.x)**2 + (s['y']-f.y)**2)
      if d < s['r']:
        f.keep=1
  
  for f in neighborhood['fleets']:
    if f.keep == 1:
      if f.sector.key not in neighborhood['fbys']:
        neighborhood['fbys'][f.sector.key] = []
      neighborhood['fbys'][f.sector.key].append(f)
  return neighborhood

def point_in_poly(x,y,poly):

  n = len(poly)
  inside = False

  p1x,p1y = poly[0]
  for i in range(n+1):
    p2x,p2y = poly[i % n]
    if y > min(p1y,p2y):
      if y <= max(p1y,p2y):
        if x <= max(p1x,p2x):
          if p1y != p2y:
            xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
          if p1x == p2x or x <= xinters:
            inside = not inside
    p1x,p1y = p2x,p2y

  return inside


def insidenebulae(sector,x,y):
  """
  >>> s = Sector()
  >>> s.nebulae = u'{"1": [[[485.00, 1210.00, 486.97, 1210.00, 486.61, 1208.70, 485.09, 1207.98, 485.00, 1208.06]]]}'
  >>> insidenebulae(s,485.01,1209.99)
  True
  >>> insidenebulae(s,484.99,1209.99)
  False
  """
  if sector.nebulae == "":
    return False
  neb = json.loads(sector.nebulae)
  for i in neb['1']:
    poly = [(i[0][j],i[0][j+1]) for j in xrange(0,len(i[0]),2)]
    if point_in_poly(x,y,poly):
      return True
  return False

## Test


def buildsectorkey(x,y):
  """
  >>> x = 100.0
  >>> y = 100.0
  >>> key = buildsectorkey(x,y)
  >>> print key
  20020
  >>> newx,newy = xyfromsectorkey(key)
  >>> print str(newx) + "," + str(newy)
  100.0,100.0
  >>> x==newx
  True
  >>> y==newy
  True
  """
  return (int(x/5.0) * 1000) + int(y/5.0)

def xyfromsectorkey(key):
  return ((key/1000)*5.0, (key%1000)*5.0)

class RedisQueueClient():
  def __init__(self):
    self.r = redis.StrictRedis(host='localhost', port=6379, db=0)
    self.pid = str(os.getpid())
    self.counter = 0
    self.r.delete('dg:response:'+str(self.pid))
  def timestamp(self,id):
    self.r.hset('dg:timestamps',str(id),datetime.datetime.utcnow())
  def beer(self,queue,msg):
    self.r.rpush('dg:queue:'+queue,cPickle.dumps(msg))
  def beerAndABump(self,queue,msg):
    self.r.rpush('dg:queue:'+queue,cPickle.dumps((self.pid,self.counter,msg)))
    rkey          = 'dg:response:'+str(self.pid)+':'+str(self.counter)
    response      = self.r.blpop(rkey,5)
    if response:
      response = cPickle.loads(response[1])
    self.counter += 1
    return response

class RedisQueueServer():
  def __init__(self,name):
    self.r    = redis.StrictRedis(host='localhost', port=6379, db=0)
    self.name = name
  def getTimeStamps(self):
    stamps = self.r.hgetall('dg:timestamps')
    if len(stamps):
      self.r.hdel(*['dg:timestamps']+stamps.keys())
    return stamps
  def doBeer(self):
    msg = self.r.blpop('dg:queue:'+self.name)[1]
    return cPickle.loads(msg)
  def doBeerAndABump(self,func):
    (pid,counter,msg) = cPickle.loads(self.r.blpop('dg:queue:'+self.name)[1])
    result            = cPickle.dumps(func(msg))
    rkey              = 'dg:response:'+str(pid)+':'+str(counter)
    self.r.rpush (rkey,result)
    self.r.expire(rkey,10)
    
     
class Point():  
  """
  >>> p = Point(5.0,0.0)
  >>> p.x
  5.0
  >>> p.y
  0.0
  """
  def __init__(self,newx,newy=0):
      if type(newx) in (tuple,list):
        self.x = newx[0]
        self.y = newx[1]
      else:
        self.x = newx
        self.y = newy


def distancetoline(p, l1, l2):
  """
  >>> p  = Point(5.0,0.0)
  >>> l1 = Point(0.0,-5.0)
  >>> l2 = Point(0.0,5.0)
  >>> distancetoline(p,l1,l2) 
  5.0
  >>> p  = Point(5.0,0.0)
  >>> l1 = Point(0.0,1.0)
  >>> l2 = Point(0.0,10.0)
  >>> distancetoline(p,l1,l2) == getdistanceobj(p,l1) 
  True
  >>> p  = Point(1.0,2.0)
  >>> l1 = Point(0.0,0.0)
  >>> l2 = Point(5.0,5.0)
  >>> distancetoline(p,l1,l2) 
  0.7071067811865476
  >>> p  = Point(0.0,0.0)
  >>> l1 = Point(0.0,-5.0)
  >>> l2 = Point(0.0,5.0)
  >>> distancetoline(p,l1,l2) 
  0.0
  """
  vx = l1.x-p.x 
  vy = l1.y-p.y
  ux = l2.x-l1.x
  uy = l2.y-l1.y

  length = ux*ux+uy*uy;

  det = (-vx*ux)+(-vy*uy); 
  # if this is < 0 or > length then its outside the line segment
  if det<0 or det>length:
    ux=l2.x-p.x
    uy=l2.y-p.y
    return sqrt(min(vx*vx+vy*vy, ux*ux+uy*uy))

  det = ux*vy-uy*vx
  if length == 0.0:
    return 0.0
  else:
    return sqrt((det*det)/length)


def checkintersection(p1,p2,p3,p4):
  """
  >>> p1 = Point(0.0,0.0)
  >>> p2 = Point(1.0,0.0)
  >>> p3 = Point(1.0,1.0)
  >>> p4 = Point(0.0,1.0)
  >>> checkintersection(p1,p3,p2,p4)
  True
  >>> checkintersection(p4,p2,p3,p1)
  True
  >>> checkintersection(p1,p4,p2,p3)
  False
  >>> checkintersection(p1,p2,p4,p3)
  False
  >>> p1 = Point(1.0,1.0)
  >>> p2 = Point(1.0,4.0)
  >>> p3 = Point(4.0,1.0)
  >>> p4 = Point(1.1,4.0)
  >>> checkintersection(p1,p2,p3,p2)
  False
  >>> checkintersection(p1,p2,p3,p4)
  False
  """
  def isonsegment(i,j,k):
    return ((i.x <= k.x or j.x <= k.x) and (k.x <= i.x or k.x <= j.x) and
           (i.y <= k.y or j.y <= k.y) and (k.y <= i.y or k.x <= j.y))

  def computedirection(i,j,k):
    a = (k.x - i.x) * (j.y - i.y);
    b = (j.x - i.x) * (k.y - i.y);
    if a < b:
      return -1
    elif a > b:
      return 1
    else:
      return 0

  # return no intersection if they
  if p1.x == p3.x and p1.y == p3.y:
    return False 
  if p1.x == p4.x and p1.y == p4.y:
    return False
  if p2.x == p3.x and p2.y == p3.y:
    return False
  if p2.x == p4.x and p2.y == p4.y:
    return False


  d1 = computedirection(p3,p4,p1)
  d2 = computedirection(p3,p4,p2)
  d3 = computedirection(p1,p2,p3)
  d4 = computedirection(p1,p2,p4)
  return ((((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and
          ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))) or
         (d1 == 0 and isonsegment(p3,p4,p1)) or
         (d2 == 0 and isonsegment(p3,p4,p2)) or
         (d3 == 0 and isonsegment(p1,p2,p3)) or
         (d4 == 0 and isonsegment(p1,p2,p4)))
         




def print_timing(func):
  def wrapper(*arg):
    print "----- starting %s -----" % (func.func_name)
    t1 = time.time()
    res = func(*arg)
    t2 = time.time()
    print '----- %s took %0.3f ms -----' % (func.func_name, (t2-t1)*1000.0)
    return res
  return wrapper
def dprint(stuff):
  if DEBUG_PRINT:
    print stuff

def cubicrandomchoice(maxnum,numchoices):
  """
  >>> random.seed(1)
  >>> cubicrandomchoice(10,3)
  [0, 4, 6]
  >>> cubicrandomchoice(5,5)
  [0, 1, 2, 3, 4]
  >>> cubicrandomchoice(10000,5)
  [1216, 4906, 908, 165, 2766]
  """
  if numchoices >= maxnum:
    return range(maxnum)
  else:
    chosen = {} 
    for i in xrange(numchoices):
      while len(chosen) < numchoices:
        x = random.random()
        choice = int(floor(((x*x*x)*maxnum)))
        if choice not in chosen:
          chosen[choice] = 1
          break
    return chosen.keys()


def normalizecolor(color):
  splitcolor = [0,0,0]

  if color[0] == '#':
    color = color[1:]
  
  color = int(color,16)
  splitcolor[0] = color >> 16
  splitcolor[1] = (color >> 8)%256
  splitcolor[2] = color % 256
  maxcomp = max(splitcolor)
  if maxcomp < 127:
    brighten = 255-maxcomp
    splitcolor[0] += brighten
    splitcolor[1] += brighten
    splitcolor[2] += brighten

  color = 0
  color += splitcolor[0] << 16
  color += splitcolor[1] << 8
  color += splitcolor[2]

  #color = '#'+hex(color)[2:]
  color = "#%06X" % color
  return color 

if __name__ == '__main__':

  import doctest

  from django.test.utils import setup_test_environment
  from django.test.utils import teardown_test_environment
  from django.db import connection
  from django.conf import settings
  verbosity = 1
  interactive = True
  setup_test_environment()


  settings.DEBUG = False    
  old_name = settings.DATABASE_NAME
  connection.creation.create_test_db(verbosity, autoclobber=not interactive)


  doctest.testmod()

  connection.creation.destroy_test_db(old_name, verbosity)
  teardown_test_environment()

  exit()
