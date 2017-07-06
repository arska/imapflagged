import imaplib
import os
from flask import Flask
app = Flask(__name__)
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()
from prometheus_client import Summary, Gauge, REGISTRY, generate_latest
request_time = Summary('request_processing_seconds', 'Time spent processing http request')
metrics_time = Summary('metrics_processing_seconds', 'Time spent processing metrics request')
imap_time = Summary('imap_processing_seconds', 'Time spent processing imap request')
flagged_items = Gauge('imap_flagged', 'Number of flagged items in IMAP mailbox')

@app.route('/')
@request_time.time()
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
@metrics_time.time()
def metrics():
    return generate_latest(REGISTRY)

# use the cached item count
flagged_items.set_function(index)

if __name__ == '__main__':
    #print(os.environ)
    app.run(host='0.0.0.0',port=8080)
