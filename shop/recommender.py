import redis
from django.conf import settings

from shop.models import Product

r = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB)


class Recommender(object):

    def get_product_key(self, prod_id):
        return f'product:{prod_id}:purchased_with'

    def products_bought(self, products):
        product_ids = [p.id for p in products]
        for product_id in product_ids:
            for with_id in product_ids:
                if product_id != with_id:
                    # increment score for product purchased together
                    r.zincrby(self.get_product_key(product_id), 1, with_id)

    def suggest_products_for(self, products, max_results=6):
        product_ids = [p.id for p in products]
        if len(products) == 1:
            suggestions = r.zrange(self.get_product_key(product_ids[0]),
                                   0, -1, desc=True)[:max_results]
        else:
            flat_ids = ''.join([str(prod_id) for prod_id in product_ids])
            tmp_key = f'tmp_{flat_ids}'
            keys = [self.get_product_key(prod_id) for prod_id in product_ids]
            r.zunionstore(tmp_key, keys)
            r.zrem(tmp_key, *product_ids)
            suggestions = r.zrange(tmp_key, 0, -1, desc=True)[:max_results]
            r.delete(tmp_key)
        suggested_product_ids = [int(prod_id) for prod_id in suggestions]
        suggested_products = list(Product.objects.filter(id__in=suggested_product_ids))
        suggested_products.sort(key=lambda x: suggested_product_ids.index(x.id))
        return suggested_products

    def clear_purchases(self):
        for prod_id in Product.objects.values_list('id', flat=True):
            r.delete(self.get_product_key(prod_id))
