from scrapy import Spider,Request
import json
from urllib.parse import urlencode

class UnesMobileSpider(Spider):
    name = "unes_product_mobile"
