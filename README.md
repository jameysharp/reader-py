Full-history RSS feed reader
============================

This is a prototype feed reader that is designed for reading webcomics,
serial stories, and other serialized creative works.

Check out the demo: <http://reader.minilop.net/>

Here are a couple of examples you could try:

- <http://reader.minilop.net/read/https://jamey.thesharps.us/feed.xml>
  (my blog feed, which implements RFC5005)
- <http://reader.minilop.net/read/https://beesbuzz.biz/comics/lewi/feed>
  (a webcomic which also implements RFC5005)
- <http://reader.minilop.net/read/https://mythcreants.com/feed/%3Fpost_type=story>
  (a collection of short sci-fi/fantasy stories on a WordPress blog)

This reader differs from every other feed reader that I've seen in two
significant ways:

1. It always shows the complete history of the feed, instead of just the
   most recent 10 posts or the posts from the last two weeks. If there
   have been 2,000 pages in the webcomic you're interested in, it will
   let you browse all of them.

2. Its UI emphasizes the content of the post you're currently looking
   at, getting everything else out of your way as much as possible. You
   can pull open a sidebar to browse through other posts in the current
   feed, and there's a small navigation bar to put the current post in
   some context, but otherwise you focus entirely on what the publisher
   wanted to share with you.

The current implementation has plenty of rough edges and limitations. My
primary goal is to inspire other people to build better versions of what
I'm demonstrating here.

If you think you can do better... you probably can. Please do!


Limitations
===========

This implementation currently:

- can fetch full history from most WordPress feeds, as well as from the
  very small number of feeds which implement the RFC5005 standard.
  (Details on that below.) Any other RSS or Atom feed won't work at all.

- may overwhelm your web browser if you access a feed with a
  particularly large number of posts. It will send you summary data
  about all of them at once, and worse, your browser may try to preload
  many or all of the entries, especially if you have JavaScript
  disabled. (But it should at least _work_ without JavaScript!)

Also, feed readers usually help you remember what you're reading, but
this one doesn't retain anything outside of basic access logs and the
contents of its HTTP cache. So it can't keep track of where you left off
and it doesn't even let you maintain a list of feeds you're subscribed
to. This is another way that this prototype is pretty useless for
day-to-day use.


How it works
============

Since this is a prototype and technology demo, I've thrown in quite a
few unusual tricks. I hope you'll find inspiration from some of them
even when you're working on unrelated projects.

Full history
------------

There's an IETF RFC dating back to 2007 that describes how RSS/Atom
feeds can efficiently publish complete archives. So I implemented
support for RFC5005 section 2, "[Complete Feeds][]", and section 4,
"[Archived Feeds][]".

[Complete Feeds]: https://tools.ietf.org/html/rfc5005#section-2
[Archived Feeds]: https://tools.ietf.org/html/rfc5005#section-4

Unfortunately, hardly anyone has ever implemented that RFC, so this
wouldn't be a very interesting demo with just that.

Due to what I think may have been an accident, WordPress happens to also
provide access to all posts through its RSS and Atom feeds. The same
query parameters which it uses for paged access to its HTML views also
work when it generates feeds.

Using the WordPress interface reliably is a little tricky, but
fortunately this is only a prototype: I don't need it to be reliable. So
I implemented support for that too.

API to simplify other feed readers
----------------------------------

Today a lot of feed reader software tries to save old entries that
they've seen in order to simulate having more history available, but
I've been told by two different developers that the storage costs of
keeping all these old entries around in full can get prohibitive.

If publishers provide full-history feeds, then feed reader software can
always reload any old entry straight from the publisher. Any entry
contents that it does save can be treated as just a cache, and discarded
as needed.

The challenge with that though is that in most scenarios that I can
think of, you need to at least know what order all the old entries
should be in. There are several good reasons why the publisher may serve
their archived feeds in a different order than than the one in which
they should be read (but that's a topic for another time).

As an alternative to the `/read/` endpoint's human-targeted UI, there's
a `/history/` endpoint demonstrating what I think might be a helpful
service to provide to other people's feed readers. If you fetch, say,
<http://reader.minilop.net/history/https://jamey.thesharps.us/feed.xml>,
then it will return the list of entry IDs from that feed, in publication
order, along with the URL of the feed document where that entry can be
found.

I think this is the minimum amount of information necessary to lazily
show a feed's history. You can immediately compute basic statistics like
how many entries there are, how many unread entries are left, etc. But
you can delay fetching any additional details until the person browsing
the feed scrolls to that part of the history. And if you need to free up
some storage, you can throw away everything except this list and lazily
reconstruct the rest again later.

No JavaScript required
----------------------

The UI for this comes from another demo I did, in my [css-feed-reader][]
repository. It is fully functional even if you have JavaScript disabled,
but it has a level of client-side interactivity that's usually only seen
in JavaScript-heavy sites. I was able to implement all the buttons using
only CSS.

[css-feed-reader]: https://github.com/jameysharp/css-feed-reader

It isn't quite practical, though, because I couldn't find a way to make
browsers load only the current-visible entry. For a large feed, loading
all the entries at once would be really bad. So there's a bit of
JavaScript which, if it gets a chance to run, _disables_ loading all the
not-currently-visible entries until you go to actually read them. That
means that in practice you probably don't want to try this with
JavaScript disabled, so perhaps I should have just required JavaScript
in the first place. But it was a neat experiment and anyway, this is
only a prototype.

Client-side templating with XSLT
--------------------------------

As far as I can tell, all the common browsers support XSLT stylesheets.
So I chose to serve up more-or-less valid Atom feeds, with a stylesheet
processing instruction pointing to the template that generates the full
reading UI.

This is a huge reduction in data transfer sizes, because the HTML that
implements my demo UI expands information from every feed entry in five
different places. Also, the template is cacheable, so on subsequent
loads the only thing the server has to send is the unique parts of the
feed you're currently interested in. (And then of course everything is
gzip'd as well.)

I'm not sure what trade-offs this approach has (maybe slower
time-to-first-render?) but I'd love to see more sites try it.

Integrated web crawler and web server
-------------------------------------

I wanted to use [Scrapy][] to send HTTP requests to origin servers, for
two reasons: first, it can be configured to throttle requests sent to
any single server while still sending as many requests in parallel as
possible; and second, because it has a reasonably standards-compliant
HTTP cache built in.

[Scrapy]: https://scrapy.org/

But I don't really want anything else that Scrapy provides, so there's a
bit of trickery to let me set up a trivial instance of one of each of
Scrapy's crawler, engine, and spider components, and then submit
requests into the pipeline any time I want. I especially wanted to be
able to use [Twisted][]'s `Deferred` helpers to manage parallel requests
and complex control flow. (These days, the standard Python `asyncio`
library is preferred for this, but Scrapy still uses Twisted's event
loop and I didn't want to think very hard about that.)

[Twisted]: https://twistedmatrix.com/

Then I needed some way to push crawl requests into the program. I
decided to do so using HTTP, but that meant I needed an HTTP server that
can run along side Scrapy's HTTP client. I settled on [Tornado][], but I
had to go back to version 4.5 to get one that could share the Twisted
event loop with Scrapy. The interface I'm using was deprecated in
Tornado version 5 (and didn't work there for reasons I didn't
understand), and removed entirely in version 6. So I have clearly chosen
poorly, somewhere along the way; but again, this is only a prototype.

[Tornado]: https://www.tornadoweb.org/
