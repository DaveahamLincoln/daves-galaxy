# Create your views here.
from django.template import Context, loader
from django.contrib.auth.decorators import login_required
from newdominion.dominion.models import *
from newdominion.dominion.forms import *
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from newdominion.dominion.menus import *

from registration.forms import RegistrationForm
from registration.models import RegistrationProfile
from registration.views import register
from django.contrib.auth import authenticate, login

import simplejson
import sys
import datetime

def fleetmenu(request,fleet_id,action):
  fleet = get_object_or_404(Fleet, id=int(fleet_id))
  menuglobals['fleet'] = fleet
  if request.POST:
    if action == 'movetoloc':
      fleet.gotoloc(request.POST['x'],request.POST['y']);
    elif action == 'movetoplanet': 
      planet = get_object_or_404(Planet, id=int(request.POST['planet']))
      fleet.gotoplanet(planet)
    else:
      form = fleetmenus[action]['form'](request.POST, instance=fleet)
      form.save()
    menu = eval(fleetmenus['root']['eval'],menuglobals)
    return render_to_response('planetmenu.xhtml', {'menu': menu}, mimetype='application/xhtml+xml')

  else:
    menu = eval(fleetmenus[action]['eval'],menuglobals)
    return render_to_response('planetmenu.xhtml', {'menu': menu}, mimetype='application/xhtml+xml')


def dologin(request):
  if request.POST and request.POST.has_key('username') and request.POST.has_key('password'):
    username = request.POST['username']
    password = request.POST['password']
    user = authenticate(username=username, password=password)
    if user is not None:
      if user.is_active:
        login(request, user)
        return HttpResponseRedirect('/view/')
        # Redirect to a success page.
      else:
        # Return a 'disabled account' error message
        return render_to_response('index.xhtml',{'loginerror': 'Account Disabled'})
    else:
      return render_to_response('index.xhtml',{'loginerror': 'Invalid Login'})
      
def index(request):
  return register(request, template_name='index.xhtml')

def planetmenu(request,planet_id,action):
  planet = get_object_or_404(Planet, id=int(planet_id))
  menuglobals['planet'] = planet
  if request.POST:
    form = planetmenus[action]['form'](request.POST, instance=planet)
    form.save()
    menu = eval(planetmenus['root']['eval'],menuglobals)
    return render_to_response('planetmenu.xhtml', {'menu': menu}, mimetype='application/xhtml+xml')
  else:
    menu = eval(planetmenus[action]['eval'],menuglobals)
    return render_to_response('planetmenu.xhtml', {'menu': menu}, mimetype='application/xhtml+xml')

def sector(request, sector_id):
  x = int(sector_id)/1000*5
  y = int(sector_id)%1000*5
  sector = get_object_or_404(Sector, key=sector_id) 
  planets = sector.planet_set.all()
  t = loader.get_template('show.xhtml')
  context = {'sector': sector, 'planets': planets, 'viewable': (x,y,5,5)}
  return render_to_response('show.xhtml', context, 
                             mimetype='application/xhtml+xml')
@login_required
def preferences(request):
  user = request.user
  player = user.get_profile()
  player.color = "FF0000"
  if request.POST:
    if request.POST.has_key('color'):
      player.color = request.POST['color']
      player.save()
  context = {'user': user, 'player':player}  
  return render_to_response('preferences.xhtml', context,
                             mimetype='application/xhtml+xml')


@login_required
def sectors(request):
  if request.POST:
    sectors = {}
    for key in request.POST:
      if key.isdigit():
        sector = get_object_or_404(Sector, key = int(key))
        planets = sector.planet_set.all()
        fleets = sector.fleet_set.all()
        sectors[key] = {}
        sectors[key]['planets'] = {}
        sectors[key]['fleets'] = {}



        for planet in planets:
          if planet.owner == request.user:
            sectors[key]['planets'][planet.id] = planet.json(playersplanet=1)
          else:
            sectors[key]['planets'][planet.id] = planet.json()
        for fleet in fleets:
          sectors[key]['fleets'][fleet.id] = fleet.json()
    output = simplejson.dumps( sectors )
    return HttpResponse(output)
  return HttpResponse("Nope")

def testforms(request):
  fleet = Fleet.objects.get(pk=1)
  form = AddFleetForm(instance=fleet)
  return render_to_response('form.xhtml',{'form':form})

@login_required
def buildfleet(request, planet_id):
  statusmsg = ""
  user = request.user
  player = user.get_profile()
  planet = get_object_or_404(Planet, id=int(planet_id))
  buildableships = planet.buildableships()
  if request.POST:
    newships = {}
    for index,key in enumerate(request.POST):
      key=str(key)
      if 'num-' in key:
        shiptype = key.split('-')[1]
        numships = int(request.POST[key])
        if numships > 0:
          newships[shiptype]=numships

        if shiptype not in buildableships['types']:
          statusmsg = "Ship Type '"+shiptype+"' not valid for this planet."
          break
    if statusmsg == "":
      fleet = Fleet()
      statusmsg = fleet.newfleetsetup(planet,newships)  
  buildableships = planet.buildableships()
  context = {'shiptypes': buildableships, 'planet': planet}
  return render_to_response('buildfleet.xhtml', context,
                             mimetype='application/xhtml+xml')

@login_required
def politics(request, action):
  user = request.user
  player = user.get_profile()
  statusmsg = ""
  try:
    for postitem in request.POST:
      if '-' not in postitem:
        continue
      action, key = postitem.split('-')
      
      otheruser = get_object_or_404(User, id=int(key))
      otherplayer = otheruser.get_profile() 
      
      if action == 'begforpeace' and len(request.POST[postitem]):
        msg = Message()
        msg.subject="offer of peace" 
        msg.fromplayer=user
        msg.toplayer=otheruser
        msgtext = []
        msgtext.append("<h1>"+user.username+" is offering the hand of peace</h1>")
        msgtext.append("")
        msgtext.append(request.POST[postitem])
        msgtext.append("")
        msgtext.append("<h1>Declare Peace?</h1> ")
        msg.message = "\n".join(msgtext)
        msg.save()
        statusmsg = "message sent"
      if action == 'changestatus':
        currelation = player.getpoliticalrelation(otherplayer)
        if currelation != "enemy" and currelation != request.POST[postitem]:
          player.setpoliticalrelation(otherplayer,request.POST[postitem])
          player.save()
          otherplayer.save()
          user.save()
          otheruser.save()
          statusmsg = "status changed"
  except:
    raise
  neighborhood = buildneighborhood(user)
  neighbors = {}
  neighbors['normal'] = []
  neighbors['enemies'] = []
  for neighbor in neighborhood['neighbors']:
    if neighbor.relation == "enemy":
      neighbors['enemies'].append(neighbor)
    else:
      neighbors['normal'].append(neighbor)
  context = {'neighbors': neighbors,
             'player':player}
  if statusmsg:
    context['statusmsg'] = statusmsg
  return render_to_response('neighbors.xhtml', context,
                             mimetype='application/xhtml+xml')

@login_required
def messages(request,action):
  user = request.user
  player = user.get_profile()
  messages = user.to_player.all()
  neighborhood = buildneighborhood(user)
  context = {'messages': messages,
             'neighbors': neighborhood['neighbors'] }
  if request.POST:
    for postitem in request.POST:
      if postitem == 'newmsgsubmit':
        if not request.POST.has_key('newmsgto'):
          continue
        elif not request.POST.has_key('newmsgsubject'):
          continue
        elif not request.POST.has_key('newmsgtext'):
          continue
        else:
          otheruser = get_object_or_404(User, id=int(request.POST['newmsgto']))
          body = request.POST['newmsgtext']  
          subject = request.POST['newmsgsubject']
          msg = Message()
          msg.subject = subject
          msg.message = body
          msg.fromplayer = user
          msg.toplayer = otheruser
          msg.save()
      if '-' in postitem:
        action, key = postitem.split('-')
        if action == 'msgdelete':
          msg = get_object_or_404(Message, id=int(key))
          if msg.toplayer==user:
            msg.delete()
        if action == 'replymsgtext' and len(request.POST[postitem]) > 0:
          othermsg = get_object_or_404(Message, id=int(key))
          otheruser = othermsg.fromplayer
          otherplayer = otheruser.get_profile() 
          msg = Message()
          msg.subject = "Re: " + othermsg.subject
          msg.message = request.POST[postitem]
          msg.fromplayer = user
          msg.toplayer = otheruser
          msg.save()
  return render_to_response('messages.xhtml', context,
                            mimetype='application/xhtml+xml')

@login_required
def playermap(request):
  player = request.user
  afform = AddFleetForm(auto_id=False);
  neighborhood = buildneighborhood(player)

  curtime = datetime.datetime.utcnow()
  endofturn = datetime.datetime(curtime.year, curtime.month, curtime.day, 2, 0, 0)
  timeleft = 0
  if curtime.hour > 2:
    # it's after 2am, and the turn will happen tommorrow at 2am... 
    endofturn = endofturn + datetime.timedelta(days=1)
  timeleft = "+" + str((endofturn-curtime).seconds) + "s"
  
    

  nummessages = len(player.to_player.all())
  context = {'fleets':      neighborhood['fleets'], 
             'planets':     neighborhood['planets'], 
             'viewable':    neighborhood['viewable'],
             'afform':      afform, 
             'neighbors':   neighborhood['neighbors'], 
             'player':      player,
             'nummessages': nummessages,
             'timeleft':    timeleft}
  
  if Planet.objects.filter(owner=request.user).count() == 1:
    context['newplayer'] = 1
  
  return render_to_response('show.xhtml', context,
                             mimetype='application/xhtml+xml')
