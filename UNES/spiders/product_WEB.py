from scrapy import Spider,Request
from scrapy.shell import inspect_response
import json
from urllib.parse import urlencode
import nest_asyncio
nest_asyncio.apply()


class UnesProductWebSpider(Spider):
    name = "unes_product"
    base_url = 'https://d3gokg1ssu-dsn.algolia.net/1/indexes/*/queries'
    algolia_params = {
        "x-algolia-agent": "Algolia for JavaScript (4.24.0); Browser (lite); instantsearch.js (4.36.0); JS Helper (3.22.5)",
        "x-algolia-api-key": "3d6a1904772a0bc84e423239b8e2672b",
        "x-algolia-application-id": "D3GOKG1SSU"
    }
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
    
    def __init__(self, store_id,**kwargs):
            self.store_id = store_id
            super(UnesProductWebSpider).__init__(**kwargs)

    def load_categories(self):
        with open('categories.json', 'r') as f:
            return json.load(f)
    
    def extract_third_level_filters(self, categories):
        filters = []
        for category in categories:
            if category.get("has_subcategories"):
                for subcategory in category.get("subcategories", []):
                    for third_level in subcategory.get("third_level", []):
                        if third_level.get("filter"):
                            filters.append(third_level["filter"])
        return filters
    
    def get_payload(self,page,filters):
        params_dict = {
            "clickAnalytics": "true",
            "facets": '["brand","categoryNames_it","diets","newsPromo","tags"]',
            "filters": filters,
            "highlightPostTag": "__/ais-highlight__",
            "highlightPreTag": "__ais-highlight__",
            "hitsPerPage": 24,
            "maxValuesPerFacet": 100,
            "page": page, 
            "userToken": "anonymous-e86c89e5-38f8-4b4f-961b-55d1bfdcf2e7",
        }
        payload = {
            "requests": [
                {
                    "indexName": f"production_{self.store_id}-index",
                    "params": urlencode(params_dict),
                }
            ]
        }
        return json.dumps(payload)
    
    def start_requests(self):
        categories = self.load_categories()
        third_level_filters = self.extract_third_level_filters(categories)
        for filter_value in third_level_filters:
            payload = self.get_payload(page=0, filters=filter_value)
            yield Request(
                url=f"{self.base_url}?{urlencode(self.algolia_params)}",
                method="POST",
                headers=self.headers,
                body=payload,
                callback=self.parse,
                meta={"filters": filter_value}
            )


    def parse(self, response):
        # inspect_response(response,self)
        data = json.loads(response.text)
        products = data.get('results', [])[0].get('hits', [])
        filters = response.meta["filters"]
        for product in products:
            promotions = None
            if product.get("promotion"):
                promotions = {
                    "promotion_code": product["promotion"].get("code"),
                    "promotion_description": product["promotion"].get("description"),
                    "promotion_start_date": product["promotion"].get("startDate"),
                    "promotion_end_date": product["promotion"].get("endDate"),
                    "promotion_tag": product["promotion"].get("tag"),
                    "discounted_price": product.get("discountedPrice", {}).get("value"),
                    "discount_currency": product.get("discountedPrice", {}).get("currencyIso"),
                }
            sku = product.get("sku")
            yield {
                "Internal ID": sku,
                "SKU": sku,
                "Name": product.get("name_it"),
                "Brand": product.get("brand"),
                "Type": product.get("type"),
                "Price": product.get("price", {}).get("value"),
                "Currency": product.get("price", {}).get("currencyIso"),
                "Price Per Unit": product.get("pricePerUnit", {}).get("value"),
                "Unit": product.get("pricePerUnit", {}).get("unit"),
                "Promotions": promotions,
                "Weight": {
                    "min_unit_weight": product.get("minUnitWeight"),
                    "max_unit_weight": product.get("maxUnitWeight"),
                    "unit": product.get("unit"),
                },
                "Image URLs": product.get("image").replace('MEDIUM','BIG'),
                # Other relevant details
                "Categories": {
                    "ids": product.get("categories"),
                    "names": product.get("categoryNames_it"),
                    "third_level_ids": product.get("categoriesThirdLevel"),
                    "third_level_names": product.get("categoryThirdLevelName"),
                },
                "Selling Method": product.get("sellingMethod"),
                "Increment Step": product.get("incrementStep"),
                "Bulky": product.get("bulky"),
                "Ranking Brand": product.get("rankingBrand"),
                "Product URL": f"https://www.spesaonline.unes.it/u2/p/{sku}",
            }

        # Pagination
        current_page = data.get('results', [])[0].get('page', 1)
        total_pages = data.get('results', [])[0].get('nbPages', 1)

        if current_page < total_pages - 1:
            yield Request(
                url=f"{self.base_url}?{urlencode(self.algolia_params)}",
                method="POST",
                headers=self.headers,
                body=self.get_payload(page=current_page + 1,filters=filters),
                callback=self.parse,
                meta={"filters": filters}
            )
