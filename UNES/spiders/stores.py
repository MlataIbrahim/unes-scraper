import scrapy
import json
from urllib.parse import urlencode

class UnesStoreSpider(scrapy.Spider):
    name = "unes_store"
    stores_url = 'https://storelocator.unes.it/wp-admin/admin-ajax.php'
    headers = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://storelocator.unes.it',
        'Pragma': 'no-cache',
        'Referer': 'https://storelocator.unes.it/?theme=u2-supermercato&services=everli',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
    }
    def start_requests(self):
        data = {
            'action': 'get_all_store',
        }
        yield scrapy.FormRequest(
            url=self.stores_url,
            headers=self.headers,
            formdata=data,
            callback=self.parse_stores
        )

    def parse_stores(self, response):
        stores = json.loads(response.body)
        for store in stores:
            store_id = store.get("id")
            latitude = store.get("lat")
            longitude = store.get("lng")
            city = store.get("localita")

            params = {
                'latitude': str(latitude),
                'longitude': str(longitude),
                'city': city,
            }
            headers = {
                'Accept': '*/*',
                'Content-Type': 'application/json',
                'Origin': 'https://www.spesaonline.unes.it',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            }
            url = f"https://www.spesaonline.unes.it/onboarding/services?{urlencode(params)}"

            yield scrapy.Request(
                url=url,
                headers=headers,
                callback=self.parse_store_details,
                meta={'store_id': store_id, 'basic_data': store},
            )

    def parse_store_details(self, response):
        # Data from the second API response
        additional_data = json.loads(response.text)

        # Data from the first API response (passed through meta)
        store_id = response.meta['store_id']
        basic_data = response.meta['basic_data']

        for service in additional_data.get("services", []):
            if not service.get("active"):
                continue

            for store in service.get("stores", []):
                # Combine data from both sources
                yield {
                    # Data from the first API response
                    "Store ID": store.get("name"),
                    "Store Code": store_id,
                    "Postal Code": basic_data.get("cap"),
                    "Name": store.get("displayName"),
                    "Address": basic_data.get("indirizzo"),
                    "Full Address": store.get("address", {}).get("formattedAddress"),
                    "City": basic_data.get("localita"),
                    "Province": basic_data.get("provincia"),
                    "Store Logo": basic_data.get("logo_negozio"),
                    "Morning Hours": basic_data.get("orario", {}).get("oggi", {}).get("mattina"),
                    "Afternoon Hours": basic_data.get("orario", {}).get("oggi", {}).get("pomeriggio"),
                    "Continuous Hours": basic_data.get("orario", {}).get("oggi", {}).get("continuato"),
                    "Departments": ", ".join(basic_data.get("reparti", [])),
                    "Phone": basic_data.get("telefono"),
                    "Store Type": basic_data.get("tipologia"),
                    "Store Type ID": basic_data.get("tipologia_id"),
                    "Title": basic_data.get("titolo"),
                    # Data from the second API response
                    "Latitude": store.get("geoPoint", {}).get("latitude"),
                    "Longitude": store.get("geoPoint", {}).get("longitude"),
                    "Services": [
                        feature
                        for group in store.get("storeFeatures", [])
                        for feature in group.get("features", [])
                    ],
                    "Flyer": store.get("unesFlyers", [{}])[0].get("file"),
                    "First Free Slot": store.get("firstFreeSlot", {}),
                    "Holiday Time": store.get("holidayTime"),
                    "Distance (Formatted)": store.get("formattedDistance"),
                    "Distance (KM)": store.get("distanceKm"),
                    "Additional Features": ", ".join(
                        feature.get("featureGroup") + ": " + ", ".join(feature.get("features", []))
                        for feature in store.get("storeFeatures", [])
                    ),
                }