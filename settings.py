import os

LOG_LEVEL = os.environ.get("LOG_LEVEL", "DEBUG")

BOT_NAME = 'feeds'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
USER_AGENT = 'experimental RSS fetcher (+https://jamey.thesharps.us/)'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS = 32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
DOWNLOAD_DELAY = 5
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN = 16
CONCURRENT_REQUESTS_PER_IP = 1

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
HTTPCACHE_ENABLED = True
HTTPCACHE_POLICY = 'scrapy.extensions.httpcache.RFC2616Policy'
HTTPCACHE_ALWAYS_STORE = True
HTTPCACHE_IGNORE_RESPONSE_CACHE_CONTROLS = ["no-store", "no-cache", "must-revalidate", "private"]
#HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES = []
#HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# don't filter duplicates
DUPEFILTER_CLASS = 'scrapy.dupefilters.BaseDupeFilter'

# disable some built-in Scrapy extensions
EXTENSIONS = {
    # not really meaningful when crawls are triggered by incoming requests:
    'scrapy.extensions.logstats.LogStats': None,
}
