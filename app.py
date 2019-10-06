"""
IMAP flagged items webservice
"""

import imaplib
import logging
import os
import time

from dotenv import load_dotenv

from flask import Flask, request
from prometheus_client import (
    REGISTRY,
    Counter,
    Gauge,
    Histogram,
    Summary,
    generate_latest,
)
from werkzeug.contrib.cache import SimpleCache

APP = Flask(__name__)  # Standard Flask app
CACHE = SimpleCache()

FLASK_REQUEST_LATENCY = Histogram(
    "flask_request_latency_seconds", "Flask Request Latency", ["method", "endpoint"]
)

FLASK_REQUEST_COUNT = Counter(
    "flask_request_count", "Flask Request Count", ["method", "endpoint", "http_status"]
)

FLASK_REQUEST_SIZE = Gauge(
    "flask_request_size_bytes",
    "Flask Response Size",
    ["method", "endpoint", "http_status"],
)

UPDATE_TIME = Summary("update_seconds", "Time spent loading data upstream")

FLAGGED_ITEMS = Gauge("imap_flagged", "number of flagged items in IMAP mailbox")

LOGFORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOGFORMAT)


@APP.route("/metrics")
def metrics():
    """
    Route returning metrics to prometheus
    """
    return generate_latest(REGISTRY)


@APP.route("/")
def index():
    """
    Return the cached number of items
    """
    items = CACHE.get("flagged-items")
    if items is None:
        items = get_flagged_items()
        CACHE.set("flagged-items", items, timeout=os.environ.get("cachetime", 5 * 60))
    return items


@UPDATE_TIME.time()
def get_flagged_items():
    """
    Get the number of flagged items from the imap server
    """
    imap = imaplib.IMAP4_SSL(os.environ.get("host"))
    imap.login(os.environ.get("username"), os.environ.get("password"))
    imap.select('"{0}"'.format(os.environ.get("folder", "INBOX")), readonly=True)
    _, result = imap.search(
        None, "(FLAGGED)"
    )  # noqa pylint: disable=invalid-name,unused-variable
    flagged = len(result[0].split())
    return str(flagged)


def before_request():
    """
    annotate the processing start time to each flask request
    """
    request.start_time = time.time()


def after_request(response):
    """
    after returning the request calculate metrics about this request
    """
    # time can go backwards...
    request_latency = max(time.time() - request.start_time, 0)
    # pylint: disable-msg=no-member
    FLASK_REQUEST_LATENCY.labels(request.method, request.path).observe(request_latency)
    FLASK_REQUEST_SIZE.labels(request.method, request.path, response.status_code).set(
        len(response.data)
    )
    FLASK_REQUEST_COUNT.labels(request.method, request.path, response.status_code).inc()
    return response


if __name__ == "__main__":
    # load settings from .env for development
    load_dotenv()
    # wire the prometheus metric to the index() function above
    FLAGGED_ITEMS.set_function(index)

    APP.before_request(before_request)
    APP.after_request(after_request)
    APP.run(host="0.0.0.0", port=os.environ.get("listenport", 8080))
