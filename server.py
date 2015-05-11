from bottle import route, run, template, get, post, debug, static_file, response, request
from mako.template import Template
from mako.lookup import TemplateLookup
from models import *
from celery import Celery
from celery.result import AsyncResult
from celery.exceptions import TimeoutError
import requests, re, logging
from bs4 import BeautifulSoup
from decimal import Decimal
import json
import time
from datetime import datetime, timedelta
from StringIO import StringIO
from PIL import Image
import signal, sys
from hashlib import md5
from time import sleep

BROKER_URL = 'mongodb://localhost:27017/tasks'

SERVER = 'http://server2.maxanet.com/cgi-bin'
## celery

celery = Celery()
import celeryconfig
celery.config_from_object(celeryconfig)

def auction_time_parse(timestr):
	now = datetime.now()	
	timestr = timestr[:-2] + timestr[-2:].upper()
	timestr = timestr.lstrip("Bids Close on").lstrip("Bid closing on ")
	timestr = "%s:%s" % (now.year, timestr)
	timefmt = time.strptime(timestr, "%Y:%A, %B %dth, Bids Start Closing at %I %p")
	utctimetuple = time.gmtime(time.mktime(timefmt))
	return datetime(*utctimetuple[0:6])

def auction_list_time_parse(timestr):
	timefmt = time.strptime(timestr, "%A, %B %d, %Y at %I:%M %p %Z")
	utctimetuple = time.gmtime(time.mktime(timefmt))
	return datetime(*utctimetuple[0:6])

class Result(object):
	def __init__(self, message=""):
		self.message = message
	
@celery.task(name='tasks.auction_list_scrape')
def auction_list_scrape():
	print("Updating auction list")
	res = requests.get('http://rlspear.com/auction_list.php')
	soup = BeautifulSoup(res.text)
	titles = soup.find_all('h1', 'ui-widget ui-widget-header ui-corner-all')
	auctions = soup.find_all('div', 'auctionListingMiddle')
	for title, auction in zip(titles, auctions):
		text = map(lambda x: x.strip(), auction.find_all('div')[1].get_text().strip().split('\n'))
		auction = auction.find_all('div')[1].a['href'].split('?')[-1]
		begin = auction_list_time_parse(text[2])
		end = auction_list_time_parse(text[5])
		if datetime.utcnow() < end: # if it hasn't ended yet...
			auctionobj = Auction.objects(name=auction).modify(upsert=True, new=True, name=auction)
			auctionobj.title = title.text.strip()
			auctionobj.begin = begin
			auctionobj.end = end
			auctionobj.last_modified = datetime.utcnow
			auctionobj.save()
	return "Auction List Updated - {0} entries updated".format(len(auctions))

@celery.task(name='tasks.auction_scrape')
def auction_scrape(auctionId, begin=None, end=None):
	print("Updating auction %s" % auctionId)
	# TODO: limit updates for a given auction to ~5 minutes

	auction = Auction.objects(name=auctionId).modify(name=auctionId, upsert=True, new=True)
	minute_delay = 10
	last_scraped = auction.last_scraped if auction.last_scraped else datetime.utcfromtimestamp(0) 
	if (datetime.utcnow() - last_scraped) < timedelta(minutes=minute_delay):
		print("Auction {0} already updated within the last {1} minutes".format(auctionId, minute_delay))
		return None
	else:
		auction.last_scraped = datetime.utcnow
	res = requests.get("%s/mndetails.cgi?%s" % (SERVER, auctionId))
	soup = BeautifulSoup(res.text)
	if soup.title.get_text() != "Data Missing":
		tds = soup.find_all(lambda x: x.name == 'td' and not x.has_attr('align'))
		#auction.date_time = auction_time_parse(tds[0].get_text())
		if begin != None:
			start_time = begin
		if end != None:
			end_time = end
		auction.location = tds[1].get_text()
		auction.highlights = tds[2].get_text()
		auction.items = re.search('(\d+)', tds[3].get_text()).group(0)
		auction.notes = tds[4].get_text()
		# some auctions don't have terms and notes... i don't care right now
		#auction.terms = tds[5].get_text()
		auction.contact = tds[-1].get_text()
		auction.last_modified = datetime.utcnow
		auction.save()
		
		# enumerate item id's
		res = requests.get("%s/mnprint.cgi?%s" % (SERVER, auctionId))
		soup = BeautifulSoup(res.text)
		for i in soup.find_all("td")[2::2]:
			i = i.get_text().strip('.')
			item_scrape.apply_async(args=[auctionId, i])
			
	return { 'id':auctionId }

def parse_field(value):
	v = value.get_text().strip().decode('ascii')
	if len(v) > 0:
		return v
	return None
	

@celery.task(name='tasks.item_scrape')
def item_scrape(auctionId, itemId):
	res = requests.get("%s/mnlist.cgi?%s/%s" % (SERVER, auctionId, itemId))
	soup = BeautifulSoup(res.text)
	if not soup.find_all(text="No data found"):
		print("%s/mnlist.cgi?%s/%s" % (SERVER, auctionId, itemId))
		item, created = Item.objects.get_or_create(item_id=itemId, auction_name=auctionId)
		if not item.photo:
			img = requests.get(soup.img['src'].strip(), stream=True)
			if img.status_code == 200:
				item.photo.put(StringIO(img.content))
		item.description = soup.find_all(lambda x: x.name == 'td' and not x.has_attr('align'))[-1].get_text()

		tds = soup.find_all(lambda x: x.name == 'td' and x.has_attr('align') and x['align'] == 'right')
		try:
			item.bids = parse_field(tds[1]) if parse_field(tds[1]) else 0
			item.high_bidder = parse_field(tds[2]) if parse_field(tds[2]) else 'None' 
			item.price = Decimal(parse_field(tds[3])) if parse_field(tds[3]) else 0
			next_price = '-1'
			if parse_field(tds[4]):
				next_price = parse_field(tds[4])
			if next_price == "ended":
				item.next_price = "-1";
			else:	
				item.next_price = Decimal(next_price)
		except Exception, e:
			print(e)
		item.last_modified = datetime.utcnow
		item.save()
	return item

@celery.task(name='tasks.item_bid')
def item_bid(auctionId, itemId, bidder_number, bidder_password, max_bid=0):
	# http://docs.celeryproject.org/en/latest/tutorials/task-cookbook.html#cookbook-task-serial
	res = requests.get("http://localhost:8080/")
	return {'res':res}

@celery.task(name='tasks.bid_watch', ignore_result=True)
def bid_watch(item_id, bid_id):
	''' 
	watch a bid page starting at auction end until item bidding expires. 
	The closing time of an asset is automatically extended an additional 4 minutes whenever a bid is placed within the last 4 minutes of the asset's closing time
	'''
	bid = Bid.objects(id=bid_id).first()
	original = bid.is_running
	bid.is_running = not bid.is_running
	acquire_lock = lambda: bid.save(save_condition={'is_running':False}).reload().is_running is not original
	release_lock = lambda: Bid.objects(id=bid_id).modify(is_running=False)
	
	if acquire_lock():
		try:
			print("{0} acquired".format(bid.id))
			# if bidding is soon, wait...
			sleep(5)
		finally:
			release_lock()
			print("{0} released".format(bid.id))
		return {}
	

@celery.task(name='tasks.process_bids', ignore_result=True)
def process_bids():
	for bid in Bid.objects:
		# schedule active Bids to start up to 30 seconds before bidding starts
		item = Item.objects(auction_name=bid.auction_name, item_id=bid.item_id).first()
		auction = Auction.objects(name=bid.auction_name).first()
		auction_end = auction.end

		if (datetime.utcnow() - auction_end) > timedelta(seconds = 60):
			task = bid_watch.apply_async(args=["{0}".format(item.id), str(bid.id)])
			print(task)
			#print("Started bid_watch for {0}".format(bid.id))
		else:
			pass
			#print("waiting bid_watch for {0}".format(bid.id))
	return {}
	
## bottle

mylookup = TemplateLookup(directories=['./views'], output_encoding='utf-8',)

def serve_template(templatename, **kwargs):
  mytemplate = mylookup.get_template(templatename)
  return mytemplate.render(**kwargs)

@route('/static/:path#.+#', name='static')
def static(path):
  return static_file(path, root='./static')

@route('/libs/<filepath:path>')
def js(filepath):
	return static_file(filepath, root='./bower_components')

@get('/')
def index():
  return serve_template('index.html')

@get('/auction')
def auction_list():
	return Auction.objects.to_json()

@get('/refresh')
def auction_refresh():
	task = auction_list_scrape.apply_async()
	print(task)
	return { 'task_id': task.id }
		

@get('/auction/:auctionId')
def auction_get(auctionId):
	#return json.dumps(Auction.objects(name=auctionId))
	return Auction.objects(name=auctionId)[0].to_json()

@get('/auction/:auctionId/list')
def auction_items(auctionId):
	page = int(request.query.page) or 0 
	#	pageSize = int(request.query.size) or 20
	pageSize = 20
	offset = page * pageSize
	return Item.objects(auction_name=auctionId).skip(offset).limit(20).to_json()

@get('/auction/:auctionId/refresh')
def auction_refresh(auctionId):
	#app.auction_scrape.apply_async(args=[auctionId])	
	task = auction_scrape.apply_async(args=[auctionId])
	return { 'task_id': task.id }

@get('/auction/:auctionId/:itemId')
def item_get(auctionId, itemId):
	item = Item.objects(auction_name=auctionId,item_id=itemId)[0]
	#item.src = "/auction/%s/%s/image" % (auctionId, itemId)
	return item.to_json()

@get('/auction/:auctionId/:itemId/follow')
def item_follow(auctionId, itemId):
	item = Item.objects(auction_name=auctionId,item_id=itemId)[0]
	item.followed = True
	item.save()
	return item.to_json()
		
@get('/auction/:auctionId/:itemId/unfollow')
def item_follow(auctionId, itemId):
	item = Item.objects(auction_name=auctionId,item_id=itemId)[0]
	item.followed = False
	item.save()
	return item.to_json()

@get('/auction/:auctionId/:itemId/image')
def item_image(auctionId, itemId):
	image = Item.objects(auction_name=auctionId,item_id=itemId)[0].photo 
	print image.thumbnail
	print dir(image.thumbnail)
	response.content_type = "image/%s" % image.format
	return image.read() 

@get('/auction/:auctionId/:itemId/refresh')
def item_refresh(auctionId, itemId):
	#task = item_scrape.apply_async(args=[auctionId,itemId])
	#return { 'task_id': task.id }
	return item_scrape(auctionId, itemId).to_json()

@get('/followed')
def get_followed():
	return Item.objects(followed=True).to_json()

@post('/bid')
def post_bid():
	auction_name = request.json['auction_name']
	item_id = request.json['item_id']
	max_bid = request.json['max_bid']

	bid, created = Bid.objects.get_or_create(auction_name=auction_name, item_id=item_id)
	#Bid.objects(auction_name=auction_name, item_id=item_id).modify(auction_name=auction_name, item_id=item_id, upsert=True, new=True)
	print(auction_name)
	bid.auction_name = auction_name
	bid.item_id = item_id
	try:
		bid.max_bid = Decimal(max_bid)
	except TypeError:
		bid.max_bid = Decimal(0)
	user = request.json['bidder_user'] if 'bidder_user' in request.json else None
	pw = request.json['bidder_password'] if 'bigger_password' in request.json else None
	if user:
		bid.bidder_number = user
	if pw:
		bid.bidder_password = pw
	print bid
	print bid.to_json()
	bid.is_running = False
	bid.save()
	return bid.to_json() #TODO: strip password

@get('/bid/:auctionId/:itemId')
def get_bid(auctionId, itemId):
	return Bid.objects(auction_name=auctionId,item_id=itemId).toJson()

@get('/task/:task_id')
def check_task(task_id):
	task = AsyncResult(task_id)
	message = None
	try:
		return message = task.get(timeout=10)
	except TimeoutError:
		message = 'processing'

	return {'task_id':task_id, 'status':task.state}
		

def signal_handler(signal, frame):
	sys.exit(0)
	

debug(True)
if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	run(host='0.0.0.0', port=8080)
