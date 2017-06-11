import imaplib
import os
from flask import Flask
app = Flask(__name__)
from werkzeug.contrib.cache import SimpleCache
cache = SimpleCache()

@app.route('/')
def index():
    items = cache.get('flagged-items')
    if items is None:
        items = get_flagged_items()
        cache.set('flagged-items', items, timeout=os.environ.get('cachetime',5*60))
    return items

def get_flagged_items():
    imap=imaplib.IMAP4_SSL(os.environ.get('host'))
    imap.login(os.environ.get('username'), os.environ.get('password'))
    imap.select('"{0}"'.format(os.environ.get('folder','INBOX')), readonly=True)
    x,y=imap.search(None,'(FLAGGED)')
    return str(len(y[0].split()))

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080)
