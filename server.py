from bottle import route, run, template, get, debug, static_file, response, request
from mako.template import Template
from mako.lookup import TemplateLookup
from models import *
from celery import Celery
import requests, re, logging
from bs4 import BeautifulSoup
from decimal import Decimal
import json
import datetime, time
from StringIO import StringIO
from PIL import Image
import signal, sys

BROKER_URL = 'mongodb://localhost:27017/tasks'

SERVER = 'http://server2.maxanet.com/cgi-bin'
## celery

celery = Celery('server', broker=BROKER_URL)

celery.conf.update(
	CELERY_ANNOTATIONS = {
		#'tasks.auction_scrape': { 'rate_limit': '10/m'}
	}
)

def auction_time_parse(timestr):
	now = datetime.datetime.now()	
	timestr = timestr[:-2] + timestr[-2:].upper()
	timestr = timestr.lstrip("Bids Close on").lstrip("Bid closing on ")
	timestr = "%s:%s" % (now.year, timestr)
	timefmt = time.strptime(timestr, "%Y:%A, %B %dth, Bids Start Closing at %I %p")
	utctimetuple = time.gmtime(time.mktime(timefmt))
	return datetime.datetime(*utctimetuple[0:6])

def auction_list_time_parse(timestr):
	timefmt = time.strptime(timestr, "%A, %B %d, %Y at %I:%M %p %Z")
	utctimetuple = time.gmtime(time.mktime(timefmt))
	return datetime.datetime(*utctimetuple[0:6])
	
@celery.task
def auction_list_scrape():
	res = requests.get('http://rlspear.com/auction_list.php')
	soup = BeautifulSoup(res.text)
	titles = soup.find_all('h1', 'ui-widget ui-widget-header ui-corner-all')
	auctions = soup.find_all('div', 'auctionListingMiddle')
	for title, auction in zip(titles, auctions):
		text = map(lambda x: x.strip(), auction.find_all('div')[1].get_text().strip().split('\n'))
		auction = auction.find_all('div')[1].a['href'].split('?')[-1]
		begin = auction_list_time_parse(text[2])
		end = auction_list_time_parse(text[5])
		if datetime.datetime.utcnow() < end: # if it hasn't ended yet...
			auction, created = Auction.objects.get_or_create(name=auction)
			auction.title = title.text.strip()
			auction.begin = begin
			auction.end = end
			auction.last_modified = datetime.datetime.utcnow
			auction.save()

@celery.task
def auction_scrape(auctionId, begin=None, end=None):
	res = requests.get("%s/mndetails.cgi?%s" % (SERVER, auctionId))
	soup = BeautifulSoup(res.text)
	if soup.title.get_text() != "Data Missing":
		tds = soup.find_all(lambda x: x.name == 'td' and not x.has_attr('align'))
		auction, created = Auction.objects.get_or_create(name=auctionId)
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
		auction.last_modified = datetime.datetime.utcnow
		auction.save()
		
		# enumerate item id's
		res = requests.get("%s/mnprint.cgi?%s" % (SERVER, auctionId))
		soup = BeautifulSoup(res.text)
		for i in soup.find_all("td")[2::2]:
			i = i.get_text().strip('.')
			item_scrape.apply_async(args=[auctionId, i])
			
	return { 'id':auctionId }

@celery.task
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
			item.bids = tds[1].get_text().decode('ascii').strip()
			item.high_bidder = tds[2].get_text().decode('ascii').strip()
			item.price = Decimal(tds[3].get_text().decode('ascii').strip())
			next_price = tds[4].get_text().strip()
			if next_price == "ended":
				item.next_price = "-1";
			else:	
				item.next_price = Decimal(next_price)
		except Exception, e:
			print(e)
		item.last_modified = datetime.datetime.utcnow
		item.save()
		
	return item

@celery.task
def item_bid(auctionId, itemId, bidder_number, bidder_password, max_bid=0):
	#res = requests.post("")
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

@get('/bid')
def post_bid():
	bid = Bid()
	#bid.save()

@get('/bid/:auctionId/:itemId')
def get_bid(auctionId, itemId):
	return Bid.objects(auction_name=auctionId,item_id=itemId).toJson()

def signal_handler(signal, frame):
	sys.exit(0)
	

debug(True)
if __name__ == '__main__':
	signal.signal(signal.SIGINT, signal_handler)
	run(host='0.0.0.0', port=8080)
