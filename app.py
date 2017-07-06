import imaplib
import os
import time
from flask import Flask, request
app = Flask(__name__)
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()
from prometheus_client import Histogram, Counter, Summary, Gauge, REGISTRY, generate_latest
flagged_items = Gauge('imap_flagged', 'Number of flagged items in IMAP mailbox')
imap_time = Summary('imap_processing_seconds', 'Time spent processing imap request')
FLASK_REQUEST_LATENCY = Histogram('flask_request_latency_seconds', 'Flask Request Latency', ['method', 'endpoint'])
FLASK_REQUEST_COUNT = Counter('flask_request_count', 'Flask Request Count', ['method', 'endpoint', 'http_status'])

def before_request():
    request.start_time = time.time()

def after_request(response):
    request_latency = max(time.time() - request.start_time, 0) # time can go backwards...
    FLASK_REQUEST_LATENCY.labels(request.method, request.path).observe(request_latency)
    FLASK_REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response

@app.route('/')
def index():
    items = cache.get('flagged-items')
    if items is None:
        items = get_flagged_items()
        cache.set('flagged-items', items, timeout=os.environ.get('cachetime',5*60))
    return items

@imap_time.time()
def get_flagged_items():
    imap=imaplib.IMAP4_SSL(os.environ.get('host'))
    imap.login(os.environ.get('username'), os.environ.get('password'))
    imap.select('"{0}"'.format(os.environ.get('folder','INBOX')), readonly=True)
    x,y=imap.search(None,'(FLAGGED)')
    flagged = len(y[0].split())
    return str(flagged)

@app.route('/metrics')
def metrics():
    return generate_latest(REGISTRY)

# use the cached item count for the prometheus metric
flagged_items.set_function(index)

if __name__ == '__main__':
    #print(os.environ)
    app.before_request(before_request)
    app.after_request(after_request)
    app.run(host='0.0.0.0',port=8080)

