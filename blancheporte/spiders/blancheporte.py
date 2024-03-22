import json

from scrapy import Request
import scrapy


class BlancheporteSpider(scrapy.Spider):
    name = "blancheporte"
    allowed_domains = ["www.blancheporte.fr"]
    start_urls = ["https://www.blancheporte.fr/"]

    def parse(self, response):
        categories = response.xpath('//*[@class = "layer-menu-link"]/@href').extract()
        for category in categories:
            if "https://www.blancheporte.fr/" in category:
                yield Request(url=category, callback=self.parse_categories, meta={'category_url': category})
            else:
                category = response.urljoin(category)
                yield Request(url=category, callback=self.parse_categories, meta={'category_url': category})

    def parse_categories(self, response):
        category_url = response.meta['category_url']
        items = response.xpath('//*[contains(@class, "tile-link")]/@href').extract()
        for item in items:
            yield Request(url=response.urljoin(item), callback=self.parse_item, meta={"category_url": category_url})

    def parse_item(self, response):
        item = {}
        item['url'] = response.url
        item['category'] = response.meta['category_url']
        main_title = response.xpath("//*[@class = 'product-name']//text()").extract_first()
        item['main_title'] = main_title
        full_path = response.xpath("//*[@class = 'breadcrumb']//text()").extract()
        full_path = [index.strip() for index in full_path if index.strip()]
        item['full_path'] = full_path
        ref = response.xpath("//*[@type = 'application/ld+json']//text()").extract_first()
        ref = json.loads(ref)
        item['ref'] = ref['sku']
        item['description'] = ref['description']
        material = response.xpath('//*[@class = "pdp-modalDescription pdp-modalDescription--paddinged"]//text()').extract()
        material = [index for index in material if '%' in index]
        item['material'] = material
        colors = response.xpath('//*[@class = "color-attribute "]/@data-url').extract()
        for index in colors:
            yield Request(url=index, callback=self.parse_sizes,
                          meta={'item': item})

    def parse_sizes(self, response):
        item = {}
        data = response.json()['product']
        #data = json.loads(response)
        data = data['variationAttributes']
        color = []
        image = []
        for index in data:
            if index['attributeId'] == "sizeCode":
                data = index
            if index['attributeId'] == "colorCode":
                color = index
        data = data['values']
        color = color['values']
        for index in data:
            yield Request(url=index['url'], callback=self.parse_prices)
        available_sizes = []
        unavailable_sizes = []
        for index in data:
            if index['availability']['displayValue'] == 'En stock':
                available_sizes.append(index['value'])
            if index['availability']['displayValue'] == 'Epuisé':
                unavailable_sizes.append(index['value'])
        item['available'] = available_sizes
        item['unavailable'] = unavailable_sizes
        color_list = []
        for index in color:
            color_list.append(index['displayValue'])
        item['all_colors'] = color_list

    def parse_prices(self, response):
        data = response.json()['product']['salesInfos']['price']['sales']['value']
