from mongoengine import *
import datetime

connect('easyspear')

class Auction(Document):
	name = StringField(unique=True)
	title = StringField()
	start_time = DateTimeField()
	end_time = DateTimeField()
	location = StringField()
	highlights = StringField()
	items = IntField()
	notes = StringField()
	terms = StringField()
	contact = StringField()
	#last_modified = DateTimeField(default=datetime.datetime.utcnow)
	last_modified = DateTimeField()
	begin = DateTimeField()
	end = DateTimeField()


class Item(Document):
	item_id = StringField()
	auction_name = StringField()
	photo = ImageField()
	description = StringField()
	bids = IntField()
	high_bidder = StringField()
	price = DecimalField()
	next_price = DecimalField()
	followed = BooleanField(default=False)
	#last_modified = DateTimeField(default=datetime.datetime.utcnow)
	last_modified = DateTimeField()

class Bid(Document):
	auction_name = StringField()
	item_id = StringField()
	max_bid = DecimalField()
	#Bidder Information
	bidder_number = StringField()
	bidder_password = StringField()
	last_modified = DateTimeField()

