#import sys
from datetime import timedelta

#sys.path.append('.') #?

BROKER_URL = 'mongodb://localhost:27017/tasks'
CELERY_RESULT_BACKEND = 'mongodb://localhost:27017/results'

CELERY_IMPORTS = ("server",)

#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'
#CELERY_ACCEPT_CONTENT=['json']
# Time is UTC by default
#CELERY_TIMEZONE = 'Europe/Oslo'

CELERYBEAT_SCHEDULE = {
	'bid_processing': {
		'task': 'tasks.process_bids',
		'schedule': timedelta(seconds=1),
	},
}

CELERY_ANNOTATIONS = {
	'tasks.auction_list_scrape': { 'rate_limit': '1/m'},
}

CELERY_MONGODB_BACKEND_SETTINGS = {
	'taskmeta_collection': 'my_taskmeta_collection',
}
