import sys

#sys.path.append('.') #?

BROKER_URL = 'mongodb://localhost:27017/tasks'

CELERY_IMPORTS = ("server",)

#CELERY_TASK_SERIALIZER = 'json'
#CELERY_RESULT_SERIALIZER = 'json'
#CELERY_ACCEPT_CONTENT=['json']
#CELERY_TIMEZONE = 'Europe/Oslo'
