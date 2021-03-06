#!/usr/bin/python2
import django
django.setup()

from newdominion.dominion.models import *
from newdominion.dominion.util import *
from django.db import connection, transaction
from django.db.models import Avg, Max, Min, Count
import sys
import os
import random
import time
import newdominion.settings
import copy
from pprint import pprint

def doencounter(f1, f2, f1report, f2report):
  if f1.numships() == 0:
    return
  if f2.numships() == 0:
    return
  allied = alliancesimple(f1.owner_id,f2.owner_id)
  if f2 == f1 or allied:
    print "allied"
    return
  hostile = atwar(f1,f2)

  if f1.disposition == 9:
    dopiracy(f1,f2, f1report, f2report)
  elif f2.disposition == 9:
    dopiracy(f2,f1, f2report, f1report)
  elif hostile:
    dobattle(f1,f2, f1report,f2report)
  else:
    return

def dopiracy(f1, f2, f1report, f2report):
  """
  >>> s = Sector(key=125123,x=100,y=100)
  >>> s.save()
  >>> u = User(username="dopiracy")
  >>> u.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p = Planet(resources=r, society=75,owner=u, sector=s,
  ...            x=626, y=617, r=.1, color=0x1234, name="Planet X")
  >>> p.save()
  >>> pl = Player(user=u, capital=p, color=112233)
  >>> pl.lastactivity = datetime.datetime.now()
  >>> pl.lastreset = datetime.datetime.now()
  >>> pl.save()

  >>> u2 = User(username="dopriacy2")
  >>> u2.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p2 = Planet(resources=r, society=75,owner=u2, sector=s,
  ...            x=626, y=617, r=.1, color=0x1234, name="Planet X")
  >>> p2.save()
  >>> pl2 = Player(user=u2, capital=p2, color=112233)
  >>> pl2.lastactivity = datetime.datetime.now()
  >>> pl2.lastreset = datetime.datetime.now()
  >>> pl2.save()
  >>> f1sc = Manifest(quatloos=1000,steel=1000)
  >>> f1sc.save()
  >>> f2sc = Manifest(quatloos=1000,steel=1000)
  >>> f2sc.save()
  >>> f1 = Fleet(owner=u, subspacers=20,sector=s, sunk_cost=f1sc, x=626.5, y=617.5)
  >>> f1.disposition = 9 # piracy -- need to enumerate these
  >>> f1.save()
  >>> f2 = Fleet(owner=u2, sector=s, sunk_cost=f2sc, x=626.5, y=617.5, 
  ...            destination=p2, homeport=p2, source=p2)
  >>> f2.merchantmen=100
  >>> tm = Manifest(steel=100)
  >>> tm.save()
  >>> f2.trade_manifest=tm
  >>> f2.save()

  >>> report1 = []
  >>> report2 = []
  >>> random.seed(0)
  >>> dopiracy(f1,f2,report1,report2)
  >>> print report1
  ['Piracy - Fleet # ...(pirate) Prey dropped cargo, retrieved.']
  >>> print report2
  ["Piracy - Fleet # ...(pirate's target) Pirates attacked, we dropped our cargo to escape."]
  >>> pprint(f1.trade_manifest.manifestlist())
  {'antimatter': 0,
   'charm': 0,
   'consumergoods': 0,
   'food': 0,
   'helium3': 0,
   'hydrocarbon': 0,
   'krellmetal': 0,
   'people': 0,
   'quatloos': 0,
   'steel': 100,
   'strangeness': 0,
   'unobtanium': 0}
  >>> pprint(f2.trade_manifest.manifestlist())
  {'antimatter': 0,
   'charm': 0,
   'consumergoods': 0,
   'food': 0,
   'helium3': 0,
   'hydrocarbon': 0,
   'krellmetal': 0,
   'people': 0,
   'quatloos': 0,
   'steel': 0,
   'strangeness': 0,
   'unobtanium': 0}

  >>> f2.owner = u2
  >>> f2.save()
  >>> FleetUserView(fleet=f2,user=u2).save()
  >>> random.seed(5)
  >>> report1 = []
  >>> report2 = []
  >>> dopiracy(f1,f2,report1,report2)
  >>> print report1
  [u'Fleet: Fleet -  #7, 20 subspacers (7) Battle! -- ', '   They Lost          merchantmen -- 9']
  >>> print report2
  [u'Fleet: Fleet -  #8, 100 merchantmen (8) Battle! -- ', '   We Lost            merchantmen -- 9']
  >>> f2.merchantmen
  91
  >>> pprint(f1.shipdict())
  {'subspacers': 20}
  >>> random.seed(7)
  >>> report1 = []
  >>> report2 = []
  >>> dopiracy(f1,f2,report1,report2)
  >>> print report1
  ['Piracy - Fleet # 7(pirate) Prey surrendered:', '         merchantmen: 7 (84 remaining)']
  >>> print report2
  ["Piracy - Fleet # 8(pirate's target) Ships surrendered to pirates:", '         merchantmen: 7 (84 remaining)']
  >>> pprint(f1.shipdict())
  {'subspacers': 20}
  >>> pprint(f2.shipdict())
  {'merchantmen': 84}
  >>> f3 = Fleet.objects.get(merchantmen=7)
  >>> pprint(f3.shipdict())
  {'merchantmen': 7}
  >>> pprint(f1.racecomposition())
  (1000, {5: 954, 6: 46})
  >>> pprint(f3.racecomposition())
  (140, {5: 46, 6: 94})
  """
  falsenegatives = ['Swamp Gas',
                    'Strange Tachyon Emissions',
                    'Suspicious Particle Trail',
                    'Reverse Polarity Neutron Flow',
                    'Subatomic Fluctuations',
                    'Warp Bobbles',
                    'Sub Space Deformations',
                    'Quantum Fissures',
                    'Subspace Field Pulses']
  numpirates = f1.numships()
  numprey = f2.numships()
  if numpirates == 0:
    return
  if numprey == 0:
    return
  distance = getdistance(f1.x,f1.y,f2.x,f2.y)

  relations = 'neutral'
  if alliancesimple(f1.owner_id,f2.owner_id):
    relations = 'friend'
  elif atwarsimple(f1.owner_id,f2.owner_id):
    relations = 'enemy'


  replinestart1 = "Piracy - Fleet # " + str(f1.id) + "(pirate) "
  replinestart2 = "Piracy - Fleet # " + str(f2.id) + "(pirate's target) "
  
  hascapitalship = False
  numcapital = 0
  for shiptype in f2.shipdict():
    if shiptypes[shiptype]['capitalship'] == True:
      numcapital += getattr(f2,shiptype)
  if random.random() < gompertz(1, -2, 2, numcapital):
      hascapitalship = True
   
  
  if (f2.numattacks() > f1.numattacks()/4 or hascapitalship == True) or \
     (relations=="enemy" and f2.numattacks() > 0):
    # Ok, f2 has combatants, so attempt to sulk away,
    # unless f2 is wise to f1's piratical nature
    # (f2 attacks f1 if within sense range and
    # a random factor is met...
    f1report.append(replinestart1 + "The other fleet is not a pushover...")
    if distance < f2.senserange():
      if relations == "enemy":
        f1report.append(replinestart1 + "They see us and are attacking.")
        f2report.append(replinestart2 + "Pirate scum found.")
        dobattle(f2,f1, f2report, f1report)
      elif random.random() < .25:
        f1report.append(replinestart1 + "Found by neutral combatants.  ")
        f2report.append(replinestart2 + "Neutral pirate scum found, attacking.")
        dobattle(f2,f1, f2report, f1report)
      else:
        anomoly = falsenegatives[random.randint(0,len(falsenegatives)-1)]
        f1report.append(replinestart1 + "Possible Detection by neutral combatants.  ")
        f2report.append("Fleet # " + str(f2.id) + " reports finding nearby " +anomoly)
  elif f1.ownerratio() < .66:
    f1report.append(replinestart1 + "Fleet unable to commit piracy due to not having")
    f1report.append(replinestart1 + "enough native population.  Fleet needs to return")
    f1report.append(replinestart1 + "to one of your planets to exchange foreign crew.")
  else:
    # aha, actual piracy happens here --
    outcome = random.random()
    takeships = {}
    if outcome < .5:          # surrender...
      totaltotake = min(int(ceil(numpirates/3.0)),numprey)
      if totaltotake < numprey:
        ships = f2.shipdict()
        ships = sorted([[shiptypes[i]['rank'],i,ships[i]] for i in ships],
                       key=itemgetter(0),
                       reverse=True)
        for shiptype in ships:
          numtotake = min(totaltotake,shiptype[2])
          takeships[shiptype[1]]=numtotake
          totaltotake -= numtotake
          if totaltotake <= 0:
            break
        newfleet = f2.splitfleet(takeships)
        newfleet.changeowner(f1.owner,f1.homeport)
        f1.swappeople(newfleet,int(min(f1.numcrew()/3.0, newfleet.numcrew()/3.0)))
        newfleet.save()
        f2.save()
      else:
        f2.changeowner(f1.owner,f1.homeport)
        f1.swappeople(f2,int(min(f1.numcrew()/3.0, f2.numcrew()/3.0)))
        newfleet = f2
        f2.save()

      f1report.append(replinestart1 + "Prey surrendered:")
      f2report.append(replinestart2 + "Ships surrendered to pirates:")
      for ships in newfleet.shipdict():
        if newfleet != f2:
          rep = "%20s: %d (%d remaining)" % (ships,
                                             getattr(newfleet,ships),
                                             getattr(f2,ships))
        else:
          rep = "%20s: %d" % (ships,getattr(f2,ships))
        f1report.append(rep)
        f2report.append(rep)

    elif outcome < .75:        # duke it out...
      dobattle(f1,f2,f1report,f2report)
    else:                     # run...
      if f2.trade_manifest:
        f1report.append(replinestart1 + "Prey dropped cargo, retrieved.")
        f2report.append(replinestart2 + "Pirates attacked, we dropped our cargo to escape.")
        if f1.trade_manifest is None:
          f1.trade_manifest = Manifest()
        for item in f2.trade_manifest.manifestlist(['id','people','quatloos']):
          # f1 is attacker, f2 defender...
          cur = getattr(f1.trade_manifest,item)
          more = getattr(f2.trade_manifest,item)
          setattr(f1.trade_manifest,item,cur+more)
          setattr(f2.trade_manifest,item,0)
        f2.damaged = True
        f2.gotoplanet(f2.homeport)
        f1.trade_manifest.save()
        f2.trade_manifest.save()
      else:
        f1report.append(replinestart1 + "Prey escaped.")
        f2report.append(replinestart2 + "Pirates seen.")
        # there's nothing to steal, odd...



def doattack(fleet1, fleet2, minatt=0, justonce=True):
  dead = []
  done = 1

  # if one fleet is much bigger than the other,
  # assume that  
  startship = 0
  multiplier = 1.2 
  
  # if fleet1 is bigger than fleet2
  if len(fleet1) > len(fleet2)*multiplier:
    startship = len(fleet1)-int(max(0,((len(fleet2)*multiplier))))
    if len(fleet2) < 5:
      startship = max(len(fleet1),startship+3)
  
  for i in xrange(startship,len(fleet1)):
    while fleet1[i]['att'] >= minatt:
      done = 0 
      if random.random() < .3:
        # see if we've hit something...
        hit = random.randint(0,len(fleet2)-1)
        dodged = False
        # you get 3 chances to dodge (if you have defences left...)
        for j in xrange(4):
          if fleet2[hit]['def'] and random.random() < .6:
            fleet2[hit]['def'] -= 1
            # successful defense
            dodged = True
            break
        if not dodged:
          # kaboom...
          dead.append(hit)
      fleet1[i]['att'] -= 1
      if justonce == True:
        break

  return done, dead


def testtotalcost(fleettype, planet):
  cost = 0
  for c in shiptypes[fleettype]['required']:
    amount = shiptypes[fleettype]['required'][c]
    if c == 'quatloos':
      cost += amount
    else:
      cost += amount * planet.getprice(c,False)
  return cost

  


def testcombat(f1, f2):
  avgs = {}
  random.seed(0)
  
  for j in f1.shipdict():
    avgs['f1'+j]=0.0
  for j in f2.shipdict():
    avgs['f2'+j]=0.0
  for i in xrange(50):
    f1t = copy.copy(f1)
    f2t = copy.copy(f2)
    dobattle(f1t,f2t,[],[])
    for j in f1.shipdict():
      total = avgs['f1'+j]
      new = getattr(f1t,j)
      avgs['f1'+j] = total+new
    for j in f2.shipdict():
      total = avgs['f2'+j]
      new = getattr(f2t,j)
      avgs['f2'+j] = total+new
  for j in f1.shipdict():
    print "f1: ",
    total = avgs['f1'+j]
    avg = total/50
    setattr(f1,j,int(avg))
    print j + ": " + str(avg),
  print " --"
  for j in f2.shipdict():
    print "f2: ",
    total = avgs['f2'+j]
    avg = total/50
    setattr(f2,j,int(avg))
    print j + ": " + str(avg),
  print " --"

def testcosteffectiveness(type1, type2, f1, f2, planet):
  acost = float(testtotalcost(type1,planet))
  bcost = float(testtotalcost(type2,planet))
  numa = 1000
  numb = int((acost/bcost)*1000)
  setattr(f1, type1, numa) 
  setattr(f2, type2, numb)
  print type1 + " --> " + str(getattr(f1,type1))
  print type2 + " --> " + str(getattr(f2,type2))
  testcombat(f1,f2)
  
  print type1 + " - %.2f"%(float(getattr(f1,type1))/numa)+"%"
  print type2 + " - %.2f"%(float(getattr(f2,type2))/numb)+"%"
  setattr(f1, type1, 0) 
  setattr(f2, type2, 0)

def dobattle(f1, f2, f1report, f2report):
  """
  >>> random.seed(0)
  >>> s = Sector(key=125123,x=100,y=100)
  >>> s.save()
  >>> u = User(username="dobattle")
  >>> u.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p = Planet(resources=r, society=75,owner=u, sector=s,
  ...            x=626, y=617, r=.1, color=0x1234, name="Planet X")
  >>> p.save()
  >>> pl = Player(user=u, capital=p, color=112233)
  >>> pl.lastactivity = datetime.datetime.now()
  >>> pl.lastreset = datetime.datetime.now()
  >>> pl.save()

  >>> u2 = User(username="dobattle2")
  >>> u2.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p2 = Planet(resources=r, society=75,owner=u2, sector=s,
  ...            x=626, y=617, r=.1, color=0x1234, name="Planet X")
  >>> p2.save()
  >>> pl2 = Player(user=u2, capital=p2, color=112233)
  >>> pl2.lastactivity = datetime.datetime.now()
  >>> pl2.lastreset = datetime.datetime.now()
  >>> pl2.save()
  >>> pl2.setpoliticalrelation(pl,'enemy')
  >>> f1sc = Manifest(quatloos=1000,steel=1000)
  >>> f1sc.save()
  >>> f2sc = Manifest(quatloos=1000,steel=1000)
  >>> f2sc.save()
  >>> f1 = Fleet(owner=u, sector=s, sunk_cost=f1sc, x=626.5, y=617.5)
  >>> f1.save()
  >>> f2 = Fleet(owner=u2, sector=s, sunk_cost=f2sc, x=626.5, y=617.5)
  >>> f2.save()
  >>> for i in shiptypes:
  ...   stype = shiptypes[i]
  ...   if stype['att'] > 0:
  ...     spread = 0
  ...     avg = 0
  ...     print "--- " + i
  ...     for j in xrange(50):
  ...       setattr(f1,i,50)
  ...       setattr(f2,i,50)
  ...       dobattle(f1,f2,[],[])
  ...       spread += abs(getattr(f1,i)-getattr(f2,i))
  ...       avg += getattr(f1,i)
  ...       avg += getattr(f2,i)
  ...       #print "(" + str(getattr(f1,i)) + "," + str(getattr(f2,i)) + ") ",
  ...     spread /= 50.0
  ...     avg /= 100.0
  ...     print "s="  + str(spread)
  ...     print "a="  + str(avg)
  ...     setattr(f1,i,0)
  ...     setattr(f2,i,0)
  --- subspacers
  s=7.4
  a=24.0
  --- battleships
  s=5.4
  a=38.52
  --- fighters
  s=7.94
  a=22.71
  --- frigates
  s=6.6
  a=31.42
  --- superbattleships
  s=3.54
  a=39.77
  --- destroyers
  s=6.02
  a=31.15
  --- scouts
  s=4.28
  a=27.22
  --- cruisers
  s=9.3
  a=24.15


  >>> f1.battleships = 0 
  >>> f1.destroyers = 20
  >>> f1.frigates = 0
  >>> f2.frigates = 20 
  >>> testcombat(f1,f2)
  f1:  destroyers: 18.4  --
  f2:  frigates: 6.02  --

  >>> f1.destroyers = 20
  >>> f1.frigates = 0
  >>> f2.frigates = 0
  >>> f2.cruisers = 20
  >>> testcombat(f1,f2)
  f1:  destroyers: 5.62  --
  f2:  cruisers: 18.22  --

  >>> f1.cruisers = 0
  >>> f1.destroyers = 0
  >>> f1.battleships = 20
  >>> testcombat(f1,f2)
  f1:  battleships: 19.04  --
  f2:  cruisers: 3.9  --
 
  >>> f1.cruisers = 0
  >>> f2.cruisers = 0
  >>> f2.superbattleships = 20
  >>> testcombat(f1,f2)
  f1:  battleships: 8.3  --
  f2:  superbattleships: 17.68  --
 
  >>> f1.superbattleships=0
  >>> f2.superbattleships=0
  >>> f1.battleships = 0

  >>> testcosteffectiveness('subspacers','frigates',f1,f2,p)
  subspacers --> 1000
  frigates --> 1357
  f1:  subspacers: 523.12  --
  f2:  frigates: 1011.36  --
  subspacers - 0.52%
  frigates - 0.75%
 
  >>> testcosteffectiveness('frigates','destroyers',f1,f2,p)
  frigates --> 1000
  destroyers --> 727
  f1:  frigates: 589.78  --
  f2:  destroyers: 453.48  --
  frigates - 0.59%
  destroyers - 0.62%

  >>> testcosteffectiveness('frigates','cruisers',f1,f2,p)
  frigates --> 1000
  cruisers --> 395
  f1:  frigates: 694.9  --
  f2:  cruisers: 302.38  --
  frigates - 0.69%
  cruisers - 0.76%

  >>> testcosteffectiveness('frigates','battleships',f1,f2,p)
  frigates --> 1000
  battleships --> 194
  f1:  frigates: 848.46  --
  f2:  battleships: 180.48  --
  frigates - 0.85%
  battleships - 0.93%

  >>> testcosteffectiveness('frigates','superbattleships',f1,f2,p)
  frigates --> 1000
  superbattleships --> 99
  f1:  frigates: 930.58  --
  f2:  superbattleships: 92.92  --
  frigates - 0.93%
  superbattleships - 0.93%

  >>> testcosteffectiveness('destroyers','cruisers',f1,f2,p)
  destroyers --> 1000
  cruisers --> 542
  f1:  destroyers: 757.48  --
  f2:  cruisers: 323.14  --
  destroyers - 0.76%
  cruisers - 0.60%


  >>> testcosteffectiveness('destroyers','battleships',f1,f2,p)
  destroyers --> 1000
  battleships --> 266
  f1:  destroyers: 878.7  --
  f2:  battleships: 239.12  --
  destroyers - 0.88%
  battleships - 0.90%

  >>> testcosteffectiveness('destroyers','superbattleships',f1,f2,p)
  destroyers --> 1000
  superbattleships --> 136
  f1:  destroyers: 947.84  --
  f2:  superbattleships: 123.86  --
  destroyers - 0.95%
  superbattleships - 0.90%

  >>> testcosteffectiveness('cruisers','battleships',f1,f2,p)
  cruisers --> 1000
  battleships --> 491
  f1:  cruisers: 748.3  --
  f2:  battleships: 388.58  --
  cruisers - 0.75%
  battleships - 0.79%

  >>> testcosteffectiveness('cruisers','superbattleships',f1,f2,p)
  cruisers --> 1000
  superbattleships --> 250
  f1:  cruisers: 901.04  --
  f2:  superbattleships: 216.74  --
  cruisers - 0.90%
  superbattleships - 0.86%

  >>> pprint(p.getprices([]))
  {'antimatter': 3564,
   'charm': 100,
   'consumergoods': 29,
   'food': 7,
   'helium3': 12000,
   'hydrocarbon': 100,
   'krellmetal': 7128,
   'people': 33,
   'steel': 71,
   'strangeness': 100,
   'unobtanium': 14257}

  >>> f1.battleships = 1
  >>> f2.destroyers = 1000
  >>> rep1 = []
  >>> rep2 = []
  >>> dobattle(f1,f2,rep1,rep2)
  >>> pprint(rep1)
  []
  >>> pprint(rep2)
  []
  
  >>> rep1 = []
  >>> rep2 = []
  >>> dobattle(f1,f2,rep1,rep2)
  >>> pprint(rep1)
  [u'Fleet: Fleet -  #1, 1 battleship (1) Battle! -- ',
   '   They Lost           destroyers -- 2']

  >>> pprint(rep2)
  [u'Fleet: Fleet -  #2, 1000 destroyer (2) Battle! -- ',
   '   We Lost             destroyers -- 2']

  >>> f1.battleships = 1
  >>> f2.destroyers = 1000
  >>> testcombat(f1,f2)
  f1:  battleships: 1.0  --
  f2:  destroyers: 999.84  --

  """

  def generatelossreport(casualties1,casualties2,f1report,f2report,
                         f1replinestart,f2replinestart):

    #Fleet: Fleet #57, 290 frigates (57) Battle! -- Our Ships Lost:
    #               frigates -- 73
    if len(casualties1) or len(casualties2):
      f1report.append(f1replinestart)
      f2report.append(f2replinestart)

    if len(casualties1):
      for casualties in casualties1:
        f1report.append("   We Lost   %20s -- %d" % (casualties, casualties1[casualties]))
        f2report.append("   They Lost %20s -- %d" % (casualties, casualties1[casualties]))

    if len(casualties2):
      for casualties in casualties2:
        f2report.append("   We Lost   %20s -- %d" % (casualties, casualties2[casualties]))
        f1report.append("   They Lost %20s -- %d" % (casualties, casualties2[casualties]))
  
  def removedestroyed(dead,casualtylist,fleet):
    # remove duplicates and sort last to first
    dead = sorted(list(set(dead)),reverse=True)
    for i in dead:
      if not casualtylist.has_key(fleet[i]['type']):
        casualtylist[fleet[i]['type']] = 1
      else: 
        casualtylist[fleet[i]['type']] += 1

      fleet.pop(i)
  
  def handlecasualties(fleet, fleetlist, casualties):
    fleet.damaged = True
    fleet.removeships(casualties)
    if not len(fleetlist):
      fleet.destroyed = True

  report = []
  total1 = f1.numships()
  total2 = f2.numships()
  noncombatants1 = f1.numnoncombatants() 
  noncombatants2 = f2.numnoncombatants() 
  combatants1 = f1.numcombatants() 
  combatants2 = f2.numcombatants() 
  casualties1 = {}
  casualties2 = {}
 
  if total1 == 0:
    return
  if total2 == 0:
    return
  
  f1replinestart = "Fleet: " + f1.shortdescription(0) + " (" + str(f1.id) + ") Battle! -- "
  f2replinestart = "Fleet: " + f2.shortdescription(0) + " (" + str(f2.id) + ") Battle! -- "
  

  # what if we had a war, and nobody could fight?
  if combatants1 == 0 and combatants2 == 0:
    f1report.append(f1replinestart + "Menacing jestures were made, but no damage was done.")
    f2report.append(f2replinestart + "Menacing jestures were made, but no damage was done.")
    return

  fleet1 = f1.listrepr(True if f1.disposition == 9 else False)
  fleet2 = f2.listrepr(True if f2.disposition == 9 else False)
  
  distance = getdistance(f1.x,f1.y,f2.x,f2.y)

  attackoccurred = 0

  done1 = 0
  done2 = 0 
  
  counter = 1 
  
  dead1=[]
  dead2=[]
 

  #TODO: fix this
  multiplier = 1.2
  f1start = 0
  """ 
  # if fleet1 is bigger than fleet2
  if len(fleet1) > len(fleet2)*multiplier:
    f1start = len(fleet1)-int(max(0,((len(fleet2)*multiplier))))
    if len(fleet2) < 5:
      f1start = max(len(fleet1),startship+3)
  """

  done1, dead2 = doattack(fleet1, fleet2,0,True)
  done2, dead1 = doattack(fleet2, fleet1,0,True) 
  
  while (not (done1 and done2)) and len(fleet1) and len(fleet2):
    if fleet1[0]['att'] > fleet2[0]['att'] and counter % 4 != 1:
      done1, dead2 = doattack(fleet1, fleet2,fleet2[0]['att'])
    elif fleet2[0]['att'] > fleet1[0]['att'] and counter % 4 != 1:
      done2, dead1 = doattack(fleet2, fleet1,fleet2[0]['att']) 
    else:
      done1, dead2 = doattack(fleet1, fleet2)
      done2, dead1 = doattack(fleet2, fleet1) 

    if len(dead1) > 0:
      removedestroyed(dead1,casualties1,fleet1)
      dead1 = []

    if len(dead2) > 0:
      removedestroyed(dead2,casualties2,fleet2)
      dead2 = []
    
    counter += 1

          #fleet2.pop(hit)
    
  if len(casualties1) or len(casualties2):
    # write a report...
    generatelossreport(casualties1,casualties2,
                       f1report,f2report,f1replinestart,f2replinestart)

    if len(casualties1):
      handlecasualties(f1, fleet1, casualties1)
    if len(casualties2):
      handlecasualties(f2, fleet2, casualties2)


  f1.save()
  f2.save()




#@print_timing
def dobuildinview2():
  """
  >>> u = User(username="dobuildinview2")
  >>> u.save()
  >>> u2 = User(username="dobuildinview2-2")
  >>> u2.save()
  >>> r = Manifest(people=5000, food=1000)
  >>> r.save()
  >>> x1 = 500.1
  >>> y1 = 500.1
  >>> s = Sector(key=buildsectorkey(x1,y1),x=101,y=101)
  >>> s.save()

  >>> s1 = Sector(key=buildsectorkey(x1-5,y1-5),x=100,y=100)
  >>> s1.save()
  >>> s2 = Sector(key=buildsectorkey(x1-5,y1),x=100,y=100)
  >>> s2.save()
  >>> s3 = Sector(key=buildsectorkey(x1-5,y1+5),x=100,y=100)
  >>> s3.save()

  >>> s4 = Sector(key=buildsectorkey(x1,y1-5),x=100,y=100)
  >>> s4.save()
  >>> s5 = Sector(key=buildsectorkey(x1,y1+5),x=100,y=100)
  >>> s5.save()

  >>> s6 = Sector(key=buildsectorkey(x1+5,y1-5),x=100,y=100)
  >>> s6.save()
  >>> s7 = Sector(key=buildsectorkey(x1+5,y1),x=100,y=100)
  >>> s7.save()
  >>> s8 = Sector(key=buildsectorkey(x1+5,y1+5),x=100,y=100)
  >>> s8.save()
  >>> p = Planet(resources=r, society=1,owner=u, sector=s,
  ...            x=505.5, y=506.5, r=.1, color=0x1234)
  >>> p.save()
  >>> p2 = Planet(resources=r, sensorrange=1, society=1,owner=u2, sector=s,
  ...            x=505.5, y=509.5, r=.1, color=0x1234)
  >>> p2.save()
  >>> f = Fleet(owner=u, homeport=p, destroyers=1, sensorrange=1, sector=s, x=p.x,y=p.y)
  >>> f.save()
  >>> f1 = Fleet(owner=u2, homeport=p, scouts=1, sector=s, x=p.x+.1,y=p.y)
  >>> f1.save()
  >>> f2 = Fleet(owner=u2, homeport=p, scouts=1, sector=s, x=p.x,y=p.y+.1)
  >>> f2.save()
  >>> f3 = Fleet(owner=u2, homeport=p, scouts=1, sector=s, x=p.x+.1,y=p.y+.1)
  >>> f3.save()
  >>> # senserange is 0:
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> f = Fleet.objects.get(destroyers=1)
  >>> f.inviewoffleet.count()
  0
  >>> # senserange is 1:
  >>> f1.sensorrange=1
  >>> f1.save()
  >>> f2.sensorrange=1
  >>> f2.save()
  >>> f3.sensorrange=1
  >>> f3.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> f = Fleet.objects.get(destroyers=1)
  >>> f.inviewoffleet.count()
  3
  >>> f.x = 500.1
  >>> f.y = 500.1
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> f1.x = 499.9
  >>> f1.y = 499.9
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 499.9
  >>> f2.y = 500.1
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 500.1
  >>> f3.y = 499.9
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> f.inviewoffleet.count()
  0
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> f.x = 504.9
  >>> f.y = 500.1
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> f.inviewoffleet.count()
  0
  >>> f1.x = 504.9
  >>> f1.y = 499.9
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 505.1
  >>> f2.y = 499.9
  >>> print str(buildsectorkey(f2.x, f2.y))
  101099
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 505.1
  >>> f3.y = 500.1
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> f.x = 504.9
  >>> f.y = 504.9
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  0
  >>> f1.x = 505.1
  >>> f1.y = 504.9
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 505.1
  >>> f2.y = 505.1
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 504.9
  >>> f3.y = 505.1
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> f.x = 500.1
  >>> f.y = 504.9
  >>> f.sector = Sector.objects.get(key=buildsectorkey(f.x,f.y))
  >>> f.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  0
  >>> f1.x = 500.1
  >>> f1.y = 505.1
  >>> f1.sector = Sector.objects.get(key=buildsectorkey(f1.x,f1.y))
  >>> f1.save()
  >>> f2.x = 499.9
  >>> f2.y = 505.1
  >>> f2.sector = Sector.objects.get(key=buildsectorkey(f2.x,f2.y))
  >>> f2.save()
  >>> f3.x = 499.9
  >>> f3.y = 504.9
  >>> f3.sector = Sector.objects.get(key=buildsectorkey(f3.x,f3.y))
  >>> f3.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> f.inviewoffleet.count()
  3
  >>> # these are 1 because we don't keep
  >>> # track of inview on fleets owned by
  >>> # the same player
  >>> f1.inviewoffleet.count()  
  1
  >>> f2.inviewoffleet.count()
  1
  >>> f3.inviewoffleet.count()
  1
  >>> FleetUserView.fleetsbyuser(f.owner).count()
  4
  >>> # now test planet --> fleet
  >>> f1.x = 0
  >>> f1.save()
  >>> f2.x = 0
  >>> f2.save()
  >>> f3.x = 0
  >>> f3.save()
  >>> f.x = p2.x
  >>> f.y = p2.y+.1
  >>> f.save()
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> FleetUserView.fleetsbyuser(p2.owner).count()
  4
  >>> FleetUserView.fleetsbyuser(p.owner).count()
  1
  >>> # test sneakiness
  >>> f.subspacers = 1
  >>> f.destroyers = 0
  >>> f.y = p2.y+.5
  >>> f.save()
  >>> random.seed(1)
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> FleetUserView.fleetsbyuser(p2.owner).count()
  3
  >>> random.seed(2)
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> FleetUserView.fleetsbyuser(p2.owner).count()
  4
  >>> fv = FleetUserView.objects.get(fleet=f, user=p2.owner)
  >>> fv.seesubs
  False
  >>> f.subspacers=10000
  >>> f.save()
  >>> random.seed(2)
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> FleetUserView.fleetsbyuser(p2.owner).count()
  4
  >>> fv = FleetUserView.objects.get(fleet=f, user=p2.owner)
  >>> fv.seesubs
  True
  """
  X=0
  Y=1
  ID=2
  OWNER=3
  SECTOR=4
  SENSORRANGE=5
  SNEAKY=6
  NUMSUBS=7
  curx = 0
  def cansee(viewer,fleet):
    d = getdistance(viewer[X],viewer[Y],fleet[X],fleet[Y])
    if d < viewer[SENSORRANGE]:
      if fleet[SNEAKY]:
        if random.random() > (d/viewer[SENSORRANGE])*1.2:
          return True
        else:
          return False
      else:
        return True



  def issneaky(fleet):
    if fleet['subspacers'] == 0:
      return False
    for shiptype in shiptypes.keys():
      if fleet[shiptype] > 0 and shiptype != 'subspacers':
        return False
    # must be sneaky
    return True
 
  def dosee(viewer,fleet,both):
    seesubs = 'false' 
    if fleet[NUMSUBS] and \
       random.random() < gompertz(1,-5,15,fleet[NUMSUBS]):
      seesubs = 'true' 

    if not friends(viewer,fleet):
      if both:
        addtodefinite(fleetfleetview, [(str(fleet[ID]),str(viewer[ID]))])
      addtodefinite(fleetplayerview, [(str(fleet[ID]),str(viewer[OWNER]),str(seesubs))])
    
    if localcache['allies'].has_key(viewer[OWNER]):
      [ addtodefinite(fleetplayerview, [(str(fleet[ID]),str(j),str(seesubs))])
        for j in localcache['allies'][viewer[OWNER]] 
        if not (j==fleet[OWNER] or \
                (localcache['allies'].has_key(j) and \
                localcache['allies'][j].has_key(fleet[OWNER])))
      ]
        
  def friends(thing1, thing2):
    return localcache['allies'].has_key(thing1[OWNER]) and \
           localcache['allies'][thing1[OWNER]].has_key(thing2[OWNER])
  
  def scansectorfleets(f1, sector, scanrange):
    for i in scanrange:
      f2 = sector[i]
      if f1[OWNER] != f2[OWNER]:
        if cansee(f1,f2):
          dosee(f1,f2,True)
            
        if cansee(f2,f1):
          dosee(f2,f1,True)

  def scansectorplanets(f, sector):
    [ dosee(sector[i],f,False) 
      for i in xrange(len(sector)) 
      if f[OWNER] != sector[i][OWNER] and 
         cansee(sector[i],f)
    ]

  def addtodefinite(deflist, stuff):
    for i in stuff:
      if not deflist.has_key(i):
        deflist[i] = 1
  
  def buildfleets():
    fleets = Fleet.objects.all().values().order_by('sector')
   
    fleetsbysector = {}
    fleetsbyowner = {}
    for f in fleets:
      f2 = [f['x'],
            f['y'],
            f['id'],
            f['owner_id'],
            f['sector_id'],
            f['sensorrange'],
            issneaky(f),
            f['subspacers']]

      if f2[SECTOR] not in fleetsbysector:
        fleetsbysector[f2[SECTOR]] = []
      fleetsbysector[f2[SECTOR]].append(f2)

      if f2[OWNER] not in fleetsbyowner:
        fleetsbyowner[f2[OWNER]] = []
      fleetsbyowner[f2[OWNER]].append(f2)
    return fleetsbysector, fleetsbyowner

  def buildplanets():
    planets = Planet.objects.exclude(owner=None).values('id','sector_id',
                                                        'owner_id','sensorrange',
                                                        'x','y')
    for p in planets:
      p2 = [p['x'],
            p['y'],
            p['id'],
            p['owner_id'],
            p['sector_id'],
            p['sensorrange']]
      if p2[SECTOR] not in planetsbysector:
        planetsbysector[p2[SECTOR]] = []
      planetsbysector[p2[SECTOR]].append(p2)

      if p2[OWNER] not in planetsbyowner:
        planetsbyowner[p2[OWNER]] = [] 
      planetsbyowner[p2[OWNER]].append(p2)
    return planetsbysector, planetsbyowner

  fleetsbysector = {}
  fleetsbyowner = {}

  fleetsbysector,fleetsbyowner = buildfleets()
  
  planetsbysector = {}
  planetsbyowner = {}
  planetsbysector,planetsbyowner = buildplanets()



  
 
  fleetplayerview = []
  
  def writerows(rows):
    insertrows('dominion_fleetuserview',
               ('fleet_id', 'user_id', 'seesubs'),
               rows)
  # do player owned fleets
  for user in fleetsbyowner:
    [fleetplayerview.append((str(i[ID]),str(user),'true')) for i in fleetsbyowner[user]]
    if len(fleetplayerview) > 5000:
      writerows(fleetplayerview)
      fleetplayerview = []
    
  # do allied fleets
  for user in localcache['allies']:
    for friend in localcache['allies'][user]:
      if user==friend:
        print "user = friend?"
        continue
      if fleetsbyowner.has_key(friend):
        [fleetplayerview.append((str(i[ID]),str(user),'true')) for i in fleetsbyowner[friend]]
      if len(fleetplayerview) > 5000:
        writerows(fleetplayerview)
        fleetplayerview = []
  writerows(fleetplayerview)
        

  fleetplayerview = {}
  fleetfleetview = {}
  prevx=0
  prevy=0

  # find unallied fleets
  for sid in sorted(fleetsbysector.iterkeys()):
    s = fleetsbysector[sid]
    newx = int(xyfromsectorkey(sid)[0])
    if newx < prevx:
      print "fuck!!!!!!"
    if newx > prevx:
      prevx = newx
      
    #print str(newx)+","+str(newy)

    startx = int(s[0][X])/5*5
    starty = int(s[0][Y])/5*5
    endx = startx+5
    endy = starty+5

    for i in xrange(len(s)):
      f1 = s[i]
      
      
      scansectorfleets(f1, s, xrange(i+1,len(s)))
      if planetsbysector.has_key(sid):
        scansectorplanets(f1, planetsbysector[sid])

      othersectors = [] 
      scansectors = sectorsincircle(f1[X],f1[Y],f1[SENSORRANGE]) 
      
      for osid in scansectors:
        if fleetsbysector.has_key(osid):
          os = fleetsbysector[osid]
          scansectorfleets(f1, os, xrange(len(os)))
        if planetsbysector.has_key(osid):
          os = planetsbysector[osid]
          scansectorplanets(f1, os)





  #print "fleet player view = " + str(len(fleetplayerview))
  #print "fleet fleet  view = " + str(len(fleetfleetview))
  insertrows('dominion_fleetuserview',
             ('fleet_id', 'user_id','seesubs'),
             fleetplayerview.keys())
  insertrows('dominion_fleet_inviewoffleet',
             ('from_fleet_id', 'to_fleet_id'),
             fleetfleetview.keys())


@print_timing
def doclearinview():
  cursor = connection.cursor()

  # Data modifying operation
  cursor.execute("DELETE FROM dominion_fleetuserview;")
  cursor.execute("DELETE FROM dominion_fleet_inviewoffleet;")
  #cursor.execute("DELETE FROM dominion_player_neighbors;")




@transaction.atomic
def doturn():
  random.seed()
  reports = {}
  info = {}
  localcache['upgrades']       = allupgrades()
  localcache['attributes']     = allattributes()
  localcache['connections']    = allconnections()
  localcache['competition']    = allcompetition()
  localcache['players']        = allplayers()
  localcache['planets']        = allplanetsbysector()
  localcache['costs']          = {}
  localcache['energy']         = {}
  localcache['planetarrivals'] = {}
  localcache['arrivals']       = []
  doclearinview()                 #done
  doatwar(reports)                #done
  doregionaltaxation(reports)     #done
  doplanets(reports)              #done
  doclearenergy()
  doupgrades(reports)             #done
  cullfleets(reports)             #done
  dofleets(reports)               #done
  doarrivals(reports)             #done
  dobuildinview2()                #done
  doplanetarydefense(reports)     #done
  doassaults(reports)             #done
  doencounters(reports)           #done 
  sendreports(reports)            #done
  

@print_timing
def doassaults(reports):
  assaults = {}
  dispositions = [5,10]
  fleets = Fleet.objects.filter(disposition__in=dispositions, 
                                speed__lt=2,
                                owner__in=localcache['atwar'].keys())
  for fleet in fleets.iterator():
    sectors = sectorsincircle(fleet.x,fleet.y,fleet.senserange())
    for sector in sectors:
      if not localcache['planets'].has_key(sector):
        continue
      planets = localcache['planets'][sector]
      for planet in planets:

        #print str(planet[1]) + "," + str(fleet.owner_id)
        if atwarsimple(planet[1],fleet.owner_id) and \
           getdistance(planet[2],planet[3],fleet.x,fleet.y) < .5:
          if not assaults.has_key(planet[0]):
            assaults[planet[0]] = []
          assaults[planet[0]].append(fleet.id)
  
  fleetids = set(sum(assaults.values(),[]))

  planets  = Planet.objects\
                   .filter(id__in=assaults.keys())
  fleets   = Fleet.objects\
                  .filter(id__in=fleetids)\
                  .in_bulk(fleetids)
  for planet in planets.iterator():
    if not reports.has_key(planet.owner_id):
      reports[planet.owner_id] = Report(planet.owner_id)
    otherreport = reports[planet.owner_id]
    damaged=False
    for fid in assaults[planet.id]:
      fleet = fleets[fid]
      if not reports.has_key(fleet.owner_id):
        reports[fleet.owner_id] = Report(fleet.owner_id)
      report = reports[fleet.owner_id]

      result = fleet.doassault(planet, report, otherreport)
      if result == 'Capitulation':
        damaged=True
        break
      elif result == True:
        damaged=True
    if damaged:
      planet.resources.save()
      planet.damaged=True
      planet.save()
    
#@print_timing
def doplanetarydefense(reports):
  """
  >>> random.seed(0)
  >>> buildinstrumentalities()
  >>> px = 1275.5
  >>> py = 617.0
  >>> s = Sector(key=buildsectorkey(px,py),x=100,y=100)
  >>> s.save()
  >>> u = User(username="doplanetarydefense")
  >>> u.save()
  >>> r = Manifest(people=50000, food=10000, steel = 10000, 
  ...              antimatter=10000, unobtanium=10000, 
  ...              krellmetal=10000 )
  >>> r.save()
  >>> p = Planet(resources=r, society=75,owner=u, sector=s,
  ...            x=px, y=py, r=.1, color=0x1234, name="Planet X")
  >>> p.calculatesenserange()
  1.25
  >>> p.save()
  >>> pl = Player(user=u, capital=p, color=112233)
  >>> pl.lastactivity = datetime.datetime.now()
  >>> pl.lastreset = datetime.datetime.now()
  >>> pl.save()

  >>> u2 = User(username="doplanetarydefense2")
  >>> u2.save()
  >>> p2 = Planet(resources=r, society=75,owner=u2, sector=s,
  ...            x=1277.5, y=617, r=.1, color=0x1234, name="Planet Y")
  >>> p2.save()
  >>> pl2 = Player(user=u2, capital=p2, color=112233)
  >>> pl2.lastactivity = datetime.datetime.now()
  >>> pl2.lastreset = datetime.datetime.now()
  >>> pl2.save()
  
  
  >>> f = Fleet(owner=u2, sector=s, x=1275.8, y=617, cruisers=100, destroyers=100)
  >>> f.save()
  >>> fid = f.id
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----
  >>> dobuildinview2()
  >>> report = {7:[],8:[]}
 
  >>> # no war
  >>> doplanetarydefense(report)
  >>> f.destroyers
  100
  >>> f.cruisers
  100
  >>> pprint(report)
  {7: [], 8: []}

  >>> pl2.setpoliticalrelation(pl,'enemy')
  >>> doclearinview()
  ----- starting doclearinview -----
  ----- doclearinview took ... ms -----
  >>> doatwar()
  ----- starting doatwar -----
  ----- doatwar took ... ms -----

  >>> dobuildinview2()
  >>> report = {7:[],8:[]}

  >>> # no defenses
  >>> f.x = 1290.0
  >>> f.save()
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  100
  >>> f.cruisers
  100
  >>> pprint(report)
  {7: [], 8: []}

  >>> # capital defense only...
  >>> f.x = 1276.9
  >>> f.save()
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  90
  >>> f.cruisers
  98
  >>> pprint(report)
  {7: [u'Capital Defenses: Engaged! -- Planet X (7) -- Fleet #10 owned by: doplanetarydefense2',
       'Capital Defenses: before: 100 destroyers, 100 cruisers',
       'Capital Defenses: after: 90 destroyers, 98 cruisers'],
   8: [u'Capital Defenses: Encountered!  Fleet #10 -- attacked by Planet: Planet X (7) owned by: doplanetarydefense',
       'Capital Defenses: before: 100 destroyers, 100 cruisers',
       'Capital Defenses: after: 90 destroyers, 98 cruisers']}

  >>> report = {7:[],8:[]}
  
  >>> # note: f is attacking p, not p2 at x=1275.5
  >>> # defenses, too far
  >>> f.x = 1279.6
  >>> f.save()
  >>> p.startupgrade(Instrumentality.MATTERSYNTH1)
  1
  >>> p.setupgradestate(Instrumentality.MATTERSYNTH1)
  >>> p.startupgrade(Instrumentality.PLANETARYDEFENSE)
  1
  >>> p.setupgradestate(Instrumentality.PLANETARYDEFENSE)
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  90
  >>> f.cruisers
  98
  >>> pprint(report)
  {7: [], 8: []}

  >>> report = {7:[],8:[]}
  
  >>> #kaboom!
  >>> f.x = 1279.4
  >>> f.save()
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  84
  >>> f.cruisers
  91
  >>> pprint(report)
  {7: [u'Planetary Defenses: Engaged! -- Planet X (7) -- Fleet #10 owned by: doplanetarydefense2',
       'Planetary Defenses: before: 90 destroyers, 98 cruisers',
       'Planetary Defenses: after: 84 destroyers, 91 cruisers'],
   8: [u'Planetary Defenses: Encountered!  Fleet #10 -- attacked by Planet: Planet X (7) owned by: doplanetarydefense',
       'Planetary Defenses: before: 90 destroyers, 98 cruisers',
       'Planetary Defenses: after: 84 destroyers, 91 cruisers']}
  
  >>> report = {7:[],8:[]}
 
  >>> # move in close...
  >>> f.x = 1275.4
  >>> f.save()
  >>> doplanetarydefense(report)
  >>> f = Fleet.objects.get(id=fid)
  >>> f.destroyers
  46
  >>> f.cruisers
  63
  >>> pprint(report)
  {7: [u'Capital Defenses: Engaged! -- Planet X (7) -- Fleet #10 owned by: doplanetarydefense2',
       'Capital Defenses: before: 84 destroyers, 91 cruisers',
       'Capital Defenses: after: 60 destroyers, 73 cruisers',
       u'Planetary Defenses: Engaged! -- Planet X (7) -- Fleet #10 owned by: doplanetarydefense2',
       'Planetary Defenses: before: 60 destroyers, 73 cruisers',
       'Planetary Defenses: after: 46 destroyers, 63 cruisers'],
   8: [u'Capital Defenses: Encountered!  Fleet #10 -- attacked by Planet: Planet X (7) owned by: doplanetarydefense',
       'Capital Defenses: before: 84 destroyers, 91 cruisers',
       'Capital Defenses: after: 60 destroyers, 73 cruisers',
       u'Planetary Defenses: Encountered!  Fleet #10 -- attacked by Planet: Planet X (7) owned by: doplanetarydefense',
       'Planetary Defenses: before: 60 destroyers, 73 cruisers',
       'Planetary Defenses: after: 46 destroyers, 63 cruisers']}

  """
  def pdattackfleet(p,f,effectiverange,replinestart):
    gothit = False
    distance = getdistance(p[1],p[2],f.x,f.y) 
    #print "d="+str(distance)+" e="+str(effectiverange)
    if distance < effectiverange:
      if not reports.has_key(p[5]):
        reports[p[5]] = Report(p[5])
      preport = reports[p[5]]
      if not reports.has_key(f.owner.id):
        reports[f.owner.id] = Report(f.owner.id)
      freport = reports[f.owner.id]
      preport.append(replinestart+"Engaged! -- "+p[3]+
                     " ("+str(p[0])+") -- Fleet #" \
                     +str(f.id)+" owned by: "+f.owner.username)
      freport.append(replinestart+"Encountered!  Fleet #"+str(f.id)+
                     " -- attacked by Planet: "+ \
                     p[3]+" ("+str(p[0])+") owned by: "+p[4])
      ships = f.shipdict()
      hitchance = .05 + (.15 - (.15 * math.log(1.0+distance,
                                               effectiverange+1)))
      for st in ships:
        numships = ships[st]
        for i in xrange(numships):
          if random.random() < hitchance:
            numships -= 1
            if not gothit:
              preport.append(replinestart+"before: " + f.shiplistreport())
              freport.append(replinestart+"before: " + f.shiplistreport())
              gothit = True
        setattr(f,st,numships)
      if gothit:
        if f.numships():
          f.damaged=True
        else:
          f.destroyed=True
        preport.append(replinestart+"after: " + f.shiplistreport())
        freport.append(replinestart+"after: " + f.shiplistreport())
      else:
        preport.append("no hits.")
        freport.append("no hits.")
      f.save()
  
  replinestart = "Capital Defenses: "
  for p in Player.objects\
                 .all()\
                 .select_related('capital','capital__owner','user'):
    if p.capital.owner_id == p.user_id and \
       localcache['atwar'].has_key(p.user_id):
      
      enemies = localcache['atwar'][p.user_id]
      fleets = closethings(FleetUserView.objects\
                                        .filter(user=p.user,
                                                fleet__owner__in=enemies)\
                                        .distinct()
                                        .select_related('fleet','fleet__owner'),
                           p.capital.x, p.capital.y,
                           1.5)
      plist = [p.capital.id, 
               p.capital.x, 
               p.capital.y, 
               p.capital.name, 
               p.capital.owner.username,
               p.capital.owner_id]
      for f in fleets:
        #print "x"
        pdattackfleet(plist,f.fleet,1.5,replinestart)
  
  replinestart = "Planetary Defenses: "
  users = User.objects\
              .filter(planet__planetupgrade__instrumentality__type=Instrumentality.PLANETARYDEFENSE, 
                      planet__planetupgrade__state=PlanetUpgrade.ACTIVE, 
                      player__enemies__isnull=False).distinct()

  for u in users.iterator():
    planets = Planet.objects\
                    .filter(owner=u,
                            planetupgrade__instrumentality__type=Instrumentality.PLANETARYDEFENSE,
                            planetupgrade__state=PlanetUpgrade.ACTIVE)\
                    .values_list('id','x','y','name','owner__username','owner_id')
    enemies = []
    if localcache and localcache['atwar'].has_key(u.id):
      enemies = localcache['atwar'][u.id]
    else:
      enemies = u.player\
                 .enemies.all()\
                 .values_list('user__id', flat=True)\
                 .distinct()\
                 .select_related('owner')\
                 .values_list('id', flat=True)

    fleets  = FleetUserView.objects\
                   .filter(user=u,
                           fleet__owner__in=enemies)\
                   .distinct()\
                   .select_related('owner')
    
    if not reports.has_key(u.id):
      reports[u.id]= Report(u.id)
    preport = reports[u.id]
    for p in planets.iterator():
      for f in fleets:
        # don't use iterator for fleets, because fleets can get
        # hit multiple times.
        pdattackfleet(p,f.fleet,4.0,replinestart)





@print_timing
def doatwar(reports={}):
  localcache['atwar'] = {}
  localcache['allies'] = {}
  atwar = User.objects.filter(player__enemies__isnull=False).distinct()
  allies = User.objects.filter(player__friends__isnull=False).distinct()
  for user in atwar:
    localcache['atwar'][user.id] = {}
    if not reports.has_key(user.id):
      reports[user.id] = Report(user.id)
    reports[user.id].append("WAR! -- you are at war with the following players:")
    for enemy in user.player.enemies.all():
      localcache['atwar'][user.id][enemy.user_id] = 1
      reports[user.id].append("  " + enemy.user.username)
  for user in allies:
    localcache['allies'][user.id] = {}
    for ally in user.player.friends.all():
      localcache['allies'][user.id][ally.user_id] = 1

@print_timing
def doclearenergy():
  planets = Planet.objects.filter(consumedenergy__gt=0)
  planets.update(consumedenergy=0)
  
@print_timing
def doupgrades(reports):
  upgrades = PlanetUpgrade.objects\
                          .all()\
                          .select_related('planet', 'planet__resources',
                                          'raised', 'instrumentality',
                                          'instrumentality__required')\
                          .order_by('instrumentality__priority')

  for upgrade in upgrades.iterator():
    if not reports.has_key(upgrade.planet.owner_id):
      reports[upgrade.planet.owner_id] = Report(upgrade.planet.owner_id)
    if not upgrade.planet.resources:
      print "planet with upgrades but no resources?"
      continue
    upgrade.doturn(reports[upgrade.planet.owner_id])
  
  planets = Planet.objects\
                  .filter(id__in=localcache['costs'].keys())\
                  .select_related('resources')
  
  #TODO scan manifests instead of planets?
  #should be cheaper on memory/cpu...
  for p in planets.iterator():
    costs = localcache['costs'][p.id]
    [p.resources.consume(line,costs[line]) for line in costs]

    available = localcache['energy'][p.id]['available']
    used = available - localcache['energy'][p.id]['left']
    totals = localcache['energy'][p.id]['totals']
    if used > 0:
      p.consumeenergy(used,totals)
      p.save()
    
    p.resources.save()
    
def doregionaltaxation(reports):
  def hasregtax(planetid):
    if localcache['upgrades'].has_key(planetid) and \
       localcache['upgrades'][planetid].has_key(Instrumentality.RGLGOVT):
      return 1
    else:
      return 0

  planetids = [i for i in localcache['upgrades'].keys() if hasregtax(i)]
  planets = Planet.objects.filter(id__in=planetids).select_related('resources')
  for planet in planets.iterator():
    if not reports.has_key(planet.owner_id):
      reports[planet.owner_id] = Report(planet.owner_id)
    totaltax = planet.nextregionaltaxation(True,reports[planet.owner_id])

@print_timing
def doplanets(reports):
  # do planets update
  planets = Planet.objects.\
                  filter(owner__isnull=False).\
                  select_related('owner', 'resources')
  for planet in planets.iterator():
    if not reports.has_key(planet.owner_id):
      reports[planet.owner_id] = Report(planet.owner_id)

    planet.doturn(reports[planet.owner_id])

@print_timing
def cullfleets(reports):
  # cull fleets...
  print "Num Destroyed = " + str(Fleet.objects.filter(destroyed=True).count())
  Fleet.objects.filter(destroyed=True).delete()

  print "Num Damaged = " + str(Fleet.objects.filter(damaged=True).count())
  Fleet.objects.filter(damaged=True).update(damaged=False)

  # spin through and remove all empty fleets (colony fleets that colonized, etc...)
  # should be able to do this inside the db with another couple flags... (see
  # above destroyed/damaged flags...)
  fleets = Fleet.objects.all()
  for fleet in fleets.iterator():
    if fleet.numships() == 0:
      fleet.delete()

@print_timing
def dofleets(reports):
  fleets = Fleet.objects.all().select_related('owner','route')

  for fleet in fleets.iterator():
    if not reports.has_key(fleet.owner_id):
      reports[fleet.owner_id] = Report(fleet.owner_id)
    report = reports[fleet.owner_id] 
    
    replinestart = "Fleet: " + fleet.shortdescription(0) + " (" + str(fleet.id) + ") "
    fleet.move(report, replinestart)

@print_timing
def doarrivals(reports):
  planets = Planet.objects\
                  .filter(id__in=localcache['planetarrivals'].keys())\
                  .select_related('resources','owner',
                                  'prices', 'foreignprices')\
  
  fleetids = set(sum(localcache['planetarrivals'].values(),[]))
    
  fleets = Fleet.objects\
                .select_related('trade_manifest', 'owner', 'route',
                                'homeport', 'destination', 'sunk_cost',
                                'source', 'homeport__resources')\
                .in_bulk(fleetids)
  # fleets arriving at planets
  for planet in planets.iterator():
    for fid in localcache['planetarrivals'][planet.id]:
      fleet = fleets[fid]
      report = reports[fleet.owner_id] 
      replinestart = "Fleet: " + fleet.shortdescription(0) + " (" + str(fleet.id) + ") "
      fleet.arrive(replinestart,report,planet)
  
  fleets = Fleet.objects\
                .filter(id__in=localcache['arrivals'])\
                .select_related('route')
  
  # fleets arriving at empty space
  for fleet in fleets.iterator():
    report = reports[fleet.owner_id] 
    replinestart = "Fleet: " + fleet.shortdescription(0) + " (" + str(fleet.id) + ") "
    fleet.arrive(replinestart,report,None)

    
@print_timing
def doencounters(reports):
  encounters = {}
  fleets = Fleet.objects.filter(viewable__isnull=False).order_by('?')
  for i in fleets.values_list('id', flat=True):
    f = Fleet.objects.get(id=i)
    for otherfleet in f.viewable.all():
      if otherfleet.owner_id == f.owner_id:
        continue
      if not reports.has_key(otherfleet.owner_id):
        reports[otherfleet.owner_id] = Report(otherfleet.owner_id)
      if not reports.has_key(f.owner_id):
        reports[f.owner.id] = Report(f.owner.id)

      encounterid = '-'.join([str(x) for x in sorted([f.id,otherfleet.id])]) 
      if encounters.has_key(encounterid):
        continue
      if f.disposition == 10:
        # ignore other fleets if doing planetary assault
        # other fleet still gets a chance, so don't set
        # this pair as encountered...
        continue        
      encounters[encounterid] = 1
      if otherfleet.owner_id == f.owner_id:
        continue
      else:
        doencounter(f,
                    otherfleet,
                    reports[f.owner_id],
                    reports[otherfleet.owner_id])

@print_timing
def sendreports(reports):
  existing = {}
  cursor = connection.cursor()
  cursor.execute("DELETE FROM dominion_turnreport;")
  #transaction.set_dirty()
  for report in reports:
    if report == None:
      continue
    user = User.objects.get(id=report)
   
    try:
      player = user.player 
    except:
      print "player doesn't exist --> " + user.username
      continue 



    turnreport = TurnReport(user_id=report)
    fullreport = reports[report].getreport()
    if len(fullreport) == 0:
      turnreport.report = "Nothing to report."
    else:
      if (datetime.datetime.now() - user.date_joined).days > 5:
        fullreport += "\n\n\n"
        fullreport += "---\n"
        fullreport += "If you do not wish to recieve email turn reports,\n"
        fullreport += "you can turn them off in the preferences panel\n"
        fullreport += "within the game.\n\n"
        fullreport += "Thanks for Playing! -- davesgalaxy.com\n"
      turnreport.report = fullreport
    turnreport.save()

    #print "---"
    #print fullreport
    #print "---"
    if user.username=="Dave":
      print fullreport

    if newdominion.settings.DEBUG == False and player.emailreports == True:
      try:
        send_mail("Dave's Galaxy Turn Report for "+user.username, 
                  fullreport, 
                  'turns@davesgalaxy.com', 
                  [user.email])
      except:
        print "bad email? -->" + str(user.id)
  print "-- successful end of turn --"


if __name__ == "__main__":
  starttime = time.time()
  if len(sys.argv) == 2 and sys.argv[1] in ['--test','-t','--t','test','-test']:
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

    doctest.testmod(optionflags=doctest.ELLIPSIS)
    connection.creation.destroy_test_db(old_name, verbosity)
    teardown_test_environment()

    exit()

  doturn()
  
  endtime = time.time()
  elapsed = endtime-starttime
  print "Elapsed: " + str(elapsed) + "s"
