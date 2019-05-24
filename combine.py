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
<?xml-stylesheet href="reader.xsl" type="text/xsl"?>
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

    title, expanded_entries = yield expand_by_source(crawler, outdir, entries)

    with open(os.path.join(outdir, b"index.xml"), "w") as f:
        f.write(feed_header.format(title=html.escape(title)))
        for entry in entries:
            f.write(feed_entry.format(
                id=html.escape(entry["id"]),
                **{
                    k: html.escape(v)
                    for k, v in expanded_entries[entry["id"]].items()
                },
            ))
        f.write(feed_footer)

    shutil.copy(b"reader.xsl", outdir)
    return outdir


def expand_by_source(crawler, outdir, entries):
    by_source = defaultdict(list)
    for entry in entries:
        by_source[entry["source"]].append(entry["id"])

    # In this demo where we share an HTTP cache between the two parts, I don't
    # think expand_source will wind up blocking, so these deferreds will all
    # run sequentially. But this demonstrates opportunities in principle for
    # parallelism, subject to any crawler policies which limit concurrent
    # requests to the same server.
    return defer.gatherResults([
        expand_source(crawler, outdir, source, frozenset(ids))
        for source, ids in by_source.items()
    ], consumeErrors=True).addCallback(merge_by_source)


@defer.inlineCallbacks
def expand_source(crawler, outdir, source, ids):
    response = yield crawler.enqueue_request(scrapy.Request(
        source,
        headers={
            "Cache-Control": "max-stale",
        },
    ))

    response.headers.setdefault('Content-Location', response.url)
    doc = feedparser.parse(
        BytesIO(response.body),
        response_headers=response.headers,
    )

    entries = {}
    for entry in doc.entries:
        if entry.id not in ids:
            continue

        if entry.get("content"):
            link = make_filename(entry.id) + b".html"

            with open(os.path.join(outdir, link), "w") as f:
                f.write("<!-- feed {} id {} -->\n".format(source, entry.id))
                f.write(entry.content[0].value)

            link = link.decode("ascii")
        else:
            link = next(l.href for l in entry.links if l.rel == "alternate")

        entries[entry.id] = {
            "published": time.strftime("%Y-%m-%dT%H:%M:%SZ", entry.published_parsed),
            "title": entry.title,
            "link": link,
        }

    return doc.feed.title, entries


def merge_by_source(by_source):
    merged_title = ""
    merged_entries = {}
    for title, entries in by_source:
        # I dunno, pick the longest title I guess?
        if len(title) > len(merged_title):
            merged_title = title

        merged_entries.update(entries)
    return merged_title, merged_entries
