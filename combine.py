import base64
from collections import defaultdict
import feedparser
from hashlib import sha256
import html
from io import BytesIO
import os
import os.path
import scrapy
import shutil
import time
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


def make_filename(url):
    digest = sha256(url.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest[:15])


@defer.inlineCallbacks
def export_archive(crawler, outdir, entries):
    try:
        os.mkdir(outdir)
    except FileExistsError:
        pass

    by_source = yield expand_by_source(crawler, entries)

    title = ""
    expanded_entries = {}
    for source_title, source_entries in by_source:
        # I dunno, pick the longest title I guess?
        if len(source_title) > len(title):
            title = source_title

        expanded_entries.update(source_entries)

    for entry_id, entry in expanded_entries.items():
        if "link" in entry:
            continue

        link = make_filename(entry_id) + b".html"

        with open(os.path.join(outdir, link), "w") as f:
            f.write("<!-- feed {} id {} -->\n".format(entry["source"], entry_id))
            f.write(entry["content"])

        entry["link"] = link.decode("ascii")

    with open(os.path.join(outdir, b"index.xml"), "w") as f:
        write_index(f, entries, "reader.xsl", title, expanded_entries)

    shutil.copy(b"reader.xsl", outdir)
    return outdir


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
