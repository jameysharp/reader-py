import base64
from collections import defaultdict
import feedparser
import feeds
from hashlib import sha256
import html
from io import BytesIO
import os
import os.path
import scrapy
import shutil
import time
import tornado.web
from twisted.internet import defer


feed_header = """
<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet href="{stylesheet}" type="text/xsl"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title type="text">{title}</title>
""".lstrip()

feed_entry = (
    '<entry>'
    '<published>{published}</published>'
    '<link rel="alternate" type="text/html" href="{link}"/>'
    '<title type="text">{title}</title>'
    '<id>{id}</id>'
    '</entry>\n'
)

feed_footer = "</feed>\n"


class ExportHandler(tornado.web.RequestHandler):
    def initialize(self, crawler):
        self.crawler = crawler

    @tornado.gen.coroutine
    def get(self, feed):
        entries = yield feeds.full_history(self.crawler, feed)
        by_source = yield expand_by_source(self.crawler, entries)

        title = (yield fetch_feed_doc(self.crawler, feed, {
            "Cache-Control": "max-stale",
        })).feed.title

        expanded_entries = {}
        for source_title, source_entries in by_source:
            pick_distinct_hashes(source_entries)
            expanded_entries.update(source_entries)

        for entry in expanded_entries.values():
            if "link" not in entry:
                entry["link"] = self.reverse_url("entry", entry["hash"], entry["source"])

        stylesheet = self.static_url("reader.xsl")
        self.set_header("Content-Type", "application/xml")
        write_index(self, entries, stylesheet, title, expanded_entries)
        self.finish()


class EntryHandler(tornado.web.RequestHandler):
    def initialize(self, crawler):
        self.crawler = crawler

    @tornado.gen.coroutine
    def get(self, entry_hash, source):
        doc = yield fetch_feed_doc(self.crawler, source, {
            "Cache-Control": "max-stale",
        })

        for entry in doc.entries:
            if hash_entry_id(entry.id).startswith(entry_hash):
                self.write(entry.content[0].value)
                self.finish()
                return

        self.send_error(400)


def pick_distinct_hashes(entries):
    """
    Update entries to have a new "hash" key derived from the entry's unique ID,
    but the shortest possible string that distinguishes this entry from the
    others in `entries`.
    """

    # Initially set "hash" to a SHA256 hash, so it's _really_ unlikely to have
    # collisions, which would lead to duplicates. Encode it using the URL-safe
    # variant of base64 so it can be used as a path segment in a URL without
    # confusion.
    for entry_id, entry in entries.items():
        entry["hash"] = hash_entry_id(entry_id)

    # Now we just need to truncate all the hashes to the shortest prefix which
    # distinguishes between all of them. If we sort them lexicographically,
    # then the longest common prefix for an entry must be its immediate
    # neighbor, either one before or one after.
    entries = sorted(entries.values(), key=lambda entry: entry["hash"])
    lcps = [
        len(os.path.commonprefix((a["hash"], b["hash"])))
        for (a, b) in zip(entries, entries[1:])
    ]

    # We need to keep the shortest prefix of each hash which is still longer
    # than the longest prefix it shares with any other hash in the set.
    for l, entry in zip(map(max, lcps + [0], [0] + lcps), entries):
        entry["hash"] = entry["hash"][:l+1]


def hash_entry_id(entry_id):
    return base64.urlsafe_b64encode(sha256(entry_id.encode()).digest()).decode("ascii")


def write_index(f, entries, stylesheet, title, expanded_entries):
    f.write(feed_header.format(
        stylesheet=html.escape(stylesheet),
        title=html.escape(title),
    ))
    for entry in entries:
        f.write(feed_entry.format(
            id=html.escape(entry["id"]),
            **{
                k: html.escape(v)
                for k, v in expanded_entries[entry["id"]].items()
            },
        ))
    f.write(feed_footer)


def expand_by_source(crawler, entries):
    by_source = defaultdict(list)
    for entry in entries:
        by_source[entry["source"]].append(entry["id"])

    # In this demo where we share an HTTP cache between the two parts, I don't
    # think expand_source will wind up blocking, so these deferreds will all
    # run sequentially. But this demonstrates opportunities in principle for
    # parallelism, subject to any crawler policies which limit concurrent
    # requests to the same server.
    return defer.gatherResults([
        expand_source(crawler, source, frozenset(ids))
        for source, ids in by_source.items()
    ], consumeErrors=True)


@defer.inlineCallbacks
def fetch_feed_doc(crawler, feed, headers=None):
    response = yield crawler.enqueue_request(scrapy.Request(
        feed,
        headers=headers or {},
    ))

    response.headers.setdefault('Content-Location', response.url)
    return feedparser.parse(
        BytesIO(response.body),
        response_headers=response.headers,
    )


@defer.inlineCallbacks
def expand_source(crawler, source, ids):
    doc = yield fetch_feed_doc(crawler, source, {
        "Cache-Control": "max-stale",
    })

    entries = {}
    for entry in doc.entries:
        if entry.id not in ids:
            continue

        d = {
            "source": source,
            "published": time.strftime("%Y-%m-%dT%H:%M:%SZ", entry.published_parsed),
            "title": entry.title,
        }

        if entry.get("content"):
            d["content"] = entry.content[0].value
        else:
            d["link"] = next(l.href for l in entry.links if l.rel == "alternate")

        entries[entry.id] = d

    return doc.feed.title, entries
