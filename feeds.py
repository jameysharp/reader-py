import feedparser
import io
import itertools
import scrapy
import time
from twisted.internet import defer
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


class FeedError(Exception):
    pass


def format_timestamp(tup):
    if not tup:
        return None
    return time.strftime("%Y-%m-%dT%H:%M:%S+00:00", tup)


def extract_feed(response):
    # headers.setdefault returns a list of bytestrings no matter what you pass it
    url = response.headers.setdefault('Content-Location', response.url)[0].decode('ascii')

    doc = feedparser.parse(
        io.BytesIO(response.body),
        response_headers=response.headers,
    )

    is_archive = is_complete = False
    for short, ns in doc.namespaces.items():
        if ns == "http://purl.org/syndication/history/1.0":
            if (short + "_archive") in doc.feed:
                is_archive = True
            if (short + "_complete") in doc.feed:
                is_complete = True

    links = {}
    for link in doc.feed.get("links", ()):
        links[link["rel"]] = link["href"]

    generator = doc.feed.get("generator_detail", ())
    if generator:
        generator = tuple(generator.values())

    entries = [
        {
            "title": e.get("title", ""),
            "link": e.link,
            "published": format_timestamp(e.get("published_parsed")),
            "id": e.get("id", e.link),
            "source": url,
        }
        for e in doc.entries
        if "link" in e
    ]

    return {
        "etag": doc.get("etag"),
        "modified": doc.get("modified"),
        "title": doc.feed.get("title"),
        "description": doc.feed.get("description"),
        "archive": is_archive,
        "complete": is_complete,
        "links": links,
        "generator": generator,
        "entries": entries,
    }


@defer.inlineCallbacks
def full_history(crawler, url):
    # might need to retry to find the subscription document
    while True:
        response = yield crawler.enqueue_request(scrapy.Request(url))
        base = extract_feed(response)

        self = base["links"].get("self")
        if self and self != url:
            print("document {!r} came from {!r}".format(url, self))
            url = self

        current = base["links"].get("current")
        if current:
            if url != current:
                print("document {!r} is not current, trying again from {!r}".format(url, current))
                url = current
                continue
        elif base["archive"]:
            raise FeedError("document {!r} is an archive and doesn't specify the current document".format(url))

        # found the right subscription document
        break

    if base["complete"]:
        result = base
    elif "prev-archive" in base["links"]:
        result = yield from_rfc5005(crawler, base, url)
    elif wordpress_generated(response.headers.getlist("Link"), base["generator"]):
        result = yield from_wordpress(crawler, url)
    else:
        raise FeedError("document {!r} is not complete but doesn't link to archives".format(url))

    # assume entries with identical or missing timestamps were listed in
    # reverse order
    result["entries"].sort(reverse=True, key=lambda e: e["published"])
    result["entries"].reverse()

    defer.returnValue(result)


@defer.inlineCallbacks
def from_rfc5005(crawler, base, url):
    combined = base

    del combined["archive"]
    del combined["complete"]

    entries = combined["entries"]
    seen = set()

    for entry in entries:
        seen.add(entry["id"])

    while "prev-archive" in base["links"]:
        later_archive = url
        url = base["links"]["prev-archive"]
        response = yield crawler.enqueue_request(scrapy.Request(
            url,
            headers={
                # archive documents should always be taken from the cache
                "Cache-Control": "max-stale",
                "Referer": later_archive,
            },
        ))
        base = extract_feed(response)
        for entry in base["entries"]:
            if entry["id"] not in seen:
                entries.append(entry)
                seen.add(entry["id"])
            else:
                print("discarding duplicate entry {!r}".format(entry["id"]))

    defer.returnValue(combined)


def query_string_replace(url, **kwargs):
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k not in kwargs]
    query.extend(sorted(kwargs.items()))
    return urlunsplit(parts._replace(query=urlencode(query)))


def wordpress_generated(links, generator):
    for link in links:
        if b"api.w.org" in link:
            return True
    for ident in generator:
        ident = ident.lower()
        if "wordpress.com" in ident or "wordpress.org" in ident:
            return True
    return False


@defer.inlineCallbacks
def from_wordpress(crawler, url):
    url = query_string_replace(
        url,
        feed="atom",
        order="ASC",
        orderby="modified",
        paged=1,
    )

    response = yield crawler.enqueue_request(scrapy.Request(url))
    combined = extract_feed(response)
    url = combined["links"].get("self") or response.headers.get("Content-Location") or response.url

    for page in itertools.count(2):
        next_url = query_string_replace(url, paged=page)

        response = yield crawler.enqueue_request(scrapy.Request(
            next_url,
            meta={
                "handle_httpstatus_list": [404],
            },
            headers={
                "Referer": url,
            },
        ))
        if response.status == 404:
            break

        url = next_url
        feed = extract_feed(response)
        combined["entries"].extend(feed["entries"])

    defer.returnValue(combined)
