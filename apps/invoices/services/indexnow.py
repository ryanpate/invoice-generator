import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger(__name__)

INDEXNOW_KEY = "a7f3c9d2e1b5480f9c3a7d6e2b4f8c1a"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
SITE_HOST = "www.invoicekits.com"
SITE_URL = "https://www.invoicekits.com"


def notify_indexnow(urls):
    """
    Notify Bing/IndexNow of new or updated URLs.
    Accepts a single URL string or a list of URL strings.
    """
    if isinstance(urls, str):
        urls = [urls]

    payload = {
        "host": SITE_HOST,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(
            INDEXNOW_ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urlopen(req, timeout=10) as response:
            if response.status == 200:
                logger.info("IndexNow: notified %d URL(s) successfully", len(urls))
            else:
                logger.warning(
                    "IndexNow: received status %s for URLs: %s",
                    response.status,
                    urls,
                )
    except URLError as exc:
        logger.error("IndexNow: request failed — %s", exc)
