Full-history RSS feed reader
============================

This is a prototype feed reader that is designed for reading webcomics,
serial stories, and other serialized creative works.

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

If you think you can do better: please do!


Limitations
===========

This implementation currently:

- can fetch full history from most WordPress feeds, as well as from the
  very small number of feeds which implement the RFC5005 standard.
  (Details on that below.) Any other RSS or Atom feed won't work at all.

- caches extremely aggressively. Once it has fetched a feed from an
  upstream site, it will never fetch that feed again. This makes it
  pretty useless as an actual feed reader for day-to-day use.

- may overwhelm your web browser if you access a feed with a
  particularly large number of posts. It will send you summary data
  about all of them at once, and worse, your browser may try to preload
  many or all of the entries, especially if you have JavaScript
  disabled. (But it should at least _work_ without JavaScript!)

- provides no feedback about what it is doing. When you ask to read a
  feed that it doesn't have cached, it will sit there for however long
  it takes the server to fetch the complete history. Making that more
  painful: to be polite, I've set a five-second delay between requests
  to the same upstream IP address

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
