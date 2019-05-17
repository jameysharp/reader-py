from scrapy import crawler
from scrapy.core import engine
from scrapy.utils.spider import DefaultSpider
from twisted.internet import defer


class ExecutionEngine(engine.ExecutionEngine):
    def open_spider(self, spider, start_requests=(), close_if_idle=False):
        return super(ExecutionEngine, self).open_spider(spider, start_requests, close_if_idle)


class Crawler(crawler.Crawler):
    def __init__(self, settings=None):
        super(Crawler, self).__init__(DefaultSpider, settings)

    def _create_engine(self):
        return ExecutionEngine(self, lambda _: self.stop())

    def enqueue_request(self, request):
        assert not request.callback and not request.errback
        dfd = defer.Deferred()
        request.callback = dfd.callback
        request.errback = dfd.errback
        self.engine.crawl(request, self.spider)
        return dfd
