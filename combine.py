import base64
from collections import defaultdict
import datetime
import feedparser
import feeds
from hashlib import sha256
import html
from io import BytesIO
import logging
import os
import os.path
import scrapy
import shutil
import time
from tornado.locks import Event
import tornado.web
from twisted.internet import defer
from twisted.python.failure import Failure


in_progress = {}
finished = {}


def record_finished(result, feed):
    finished[feed] = result
    event, progress = in_progress.pop(feed)
    event.set()


class Progress(object):
    def __init__(self, logger=None):
        self.events = []
        self.logger = logger

    def log(self, lvl, msg):
        self.events.append(msg)
        if self.logger:
            self.logger.log(lvl, "%s", msg)

    def debug(self, msg):
        self.log(logging.DEBUG, msg)

    def info(self, msg):
        self.log(logging.INFO, msg)

    def warning(self, msg):
        self.log(logging.WARNING, msg)


class ExportHandler(tornado.web.RequestHandler):
    def initialize(self, crawler):
        self.crawler = crawler

    @tornado.gen.coroutine
    def get(self, feed):
        if feed not in finished:
            if feed not in in_progress:
                progress = Progress(self.crawler.engine.spider.logger)
                in_progress[feed] = (Event(), progress)
                get_history(
                    feed=feed,
                    progress=progress,
                    crawler=self.crawler,
                    base_url="{}://{}".format(self.request.protocol, self.request.host),
                    reverse_url=self.application.reverse_url,
                ).addBoth(record_finished, feed)

            try:
                event, progress = in_progress[feed]
                yield event.wait(datetime.timedelta(seconds=1))
            except tornado.gen.TimeoutError:
                self.render("in-progress.html", feed=feed, progress=progress)
                return

        entries = finished[feed]

        if isinstance(entries, Failure):
            self.set_status(400)
            self.render("feed-error.html", feed=feed, message=repr(entries.value))
            return

        title = (yield fetch_feed_doc(self.crawler, feed, {
            "Cache-Control": "max-stale",
        })).feed.title

        self.set_header("Cache-Control", "max-age=60, stale-while-revalidate=600, stale-if-error=3600")
        self.render("all-pages.html", title=title, feed=feed, entries=entries, hash_entry_id=hash_entry_id)


class PageHandler(tornado.web.RequestHandler):
    def initialize(self, crawler):
        self.crawler = crawler

    @tornado.gen.coroutine
    def get(self, entry_hash, feed):
        entries = finished.get(feed)

        if entries is not None and not isinstance(entries, Failure):
            title = (yield fetch_feed_doc(self.crawler, feed, {
                "Cache-Control": "max-stale",
            })).feed.title

            for idx, entry in enumerate(entries):
                if hash_entry_id(entry['id']) != entry_hash: continue

                prev_entry = None
                if idx > 0:
                    prev_entry = self.reverse_url('page', hash_entry_id(entries[idx - 1]['id']), feed)

                next_entry = None
                if idx < len(entries) - 1:
                    next_entry = self.reverse_url('page', hash_entry_id(entries[idx + 1]['id']), feed)

                self.render(
                    "view-page.html",
                    title=title,
                    feed=feed,
                    entry=entry,
                    prev_entry=prev_entry,
                    next_entry=next_entry,
                )
                return

        self.redirect(self.reverse_url('read', feed))


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
    return base64.urlsafe_b64encode(sha256(entry_id.encode()).digest()).decode("ascii").rstrip('=')


def group_by_source(entries):
    by_source = defaultdict(list)
    for entry in entries:
        by_source[entry["source"]].append(entry["id"])
    return by_source.items()


@defer.inlineCallbacks
def get_history(crawler, feed, progress, base_url, reverse_url):
    entries = yield feeds.full_history(crawler, feed, progress)

    # In this demo where we share an HTTP cache between the two parts, I don't
    # think expand_source will wind up blocking, so these deferreds will all
    # run sequentially. But this demonstrates opportunities in principle for
    # parallelism, subject to any crawler policies which limit concurrent
    # requests to the same server.
    by_source = yield defer.gatherResults([
        expand_source(crawler, source, frozenset(ids), progress)
        for source, ids in group_by_source(entries)
    ], consumeErrors=True)

    expanded_entries = {}
    for source_entries in by_source:
        pick_distinct_hashes(source_entries)
        expanded_entries.update(source_entries)

    for entry in entries:
        entry.update(expanded_entries.pop(entry["id"]))
        if "link" not in entry:
            entry["link"] = base_url + reverse_url("entry", entry["hash"], entry["source"])

    # expanded_entries better have exactly the IDs from entries
    assert not expanded_entries

    return entries


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
def expand_source(crawler, source, ids, progress):
    doc = yield fetch_feed_doc(crawler, source, {
        "Cache-Control": "max-stale",
    })

    entries = {}
    for idx, entry in enumerate(doc.entries):
        if not entry.get('id'):
            progress.warning("missing id for entry #{} of {!r}".format(idx, source))
            continue

        if entry.id not in ids:
            continue

        d = {
            "source": source,
            "published": time.strftime("%Y-%m-%dT%H:%M:%SZ", entry.published_parsed),
            "title": entry.title,
        }

        if not entry.get("content"):
            d["link"] = next(l.href for l in entry.links if l.rel == "alternate")

        entries[entry.id] = d

    return entries
