from scrapy import Spider,Request
from scrapy.shell import inspect_response
import json
from urllib.parse import urlencode
from urllib.parse import urljoin
import nest_asyncio
nest_asyncio.apply()


class UnesCategorySpider(Spider):
    name = "unes_category"
    home_url = 'https://www.spesaonline.unes.it/'
    headers = {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Origin': 'https://www.spesaonline.unes.it',
            'Pragma': 'no-cache',
            'Referer': 'https://www.spesaonline.unes.it/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'content-type': 'application/x-www-form-urlencoded',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
        }

    def start_requests(self):
        cookies = {
            'ROUTE': '.accstorefront-7cc9965994-l9xm4',
            '_ALGOLIA': 'anonymous-e86c89e5-38f8-4b4f-961b-55d1bfdcf2e7',
            'JSESSIONID': 'Y9-7803072d-0902-412b-b51f-d62ffc0cf1c8.accstorefront-7cc9965994-l9xm4',
        }
        yield Request(
            url=self.home_url,
            headers=self.headers,
            cookies=cookies,
            callback=self.parse,
        )

    def parse(self, response):
        # Categories without sub
        categories_without_subcategories = response.xpath("//li[contains(@class, 'header__menu-li_1') and not(./div)]//a")
        for category in categories_without_subcategories:
            category_url = category.xpath("@href").get()
            yield {
                'category_name': category.xpath("text()").get(),
                'url': urljoin(self.home_url, category_url) if category_url else None,
                'has_subcategories': False,
                'filter': f"tags:'{category_url.split('/')[-1] if category_url else None}'",

            }

        top_categories = response.xpath("//li[contains(@class, 'header__menu-li_1')]")
        for category in top_categories:
            category_name = category.xpath(".//label/text()").get()
            if not category_name or category_name.strip() == "":
                continue  # Skip empty categories

            category_name = category_name.strip()
            subcategory_container = category.xpath(".//div[contains(@class, 'header__menu-ul_2')]")
            
            if subcategory_container:
                subcategories = self.parse_subcategories(subcategory_container, self.home_url)
            else:
                subcategories = []

            yield {
                'category_name': category_name,
                'has_subcategories': True,
                'subcategories': subcategories
            }


    def parse_subcategories(self, subcategory_container, base_url):
        subcategories = []
        subcategory_elements = subcategory_container.xpath(".//li[contains(@class, 'header__menu-li_2')]")

        for subcategory in subcategory_elements:
            subcategory_name = subcategory.xpath(".//label/a/text()").get()
            subcategory_url = subcategory.xpath(".//label/a/@href").get()
            subcategory_url = urljoin(base_url, subcategory_url) if subcategory_url else None
            
            
            category_filter = None
            if subcategory_url and "c/" in subcategory_url:
                category_filter = f"categories:{subcategory_url.split('/')[-1]}"
            
            
            third_level_container = subcategory.xpath(".//div[contains(@class, 'header__menu-ul_3')]")
            if third_level_container:
                third_level_subcategories = self.parse_third_level(third_level_container, base_url)
            else:
                third_level_subcategories = []

            subcategories.append({
                'subcategory_name': subcategory_name,
                'subcategory_url': subcategory_url,
                'filter': category_filter,
                'third_level': third_level_subcategories
            })

        return subcategories

    def parse_third_level(self, third_level_container, base_url):
        third_level_categories = []
        third_level_elements = third_level_container.xpath(".//li[contains(@class, 'header__menu-li_3')]")

        for third_level in third_level_elements:
            third_level_name = third_level.xpath(".//label/a/text()").get()
            third_level_url = third_level.xpath(".//label/a/@href").get()
            third_level_url = urljoin(base_url, third_level_url) if third_level_url else None
            
            third_level_filter = None
            if third_level_url and "c/" in third_level_url:
                third_level_filter = f"categories:{third_level_url.split('/')[-1]}"
            
            third_level_categories.append({
                'third_level_name': third_level_name,
                'third_level_url': third_level_url,
                'filter': third_level_filter 
            })

        return third_level_categories