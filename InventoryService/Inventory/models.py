from django.db import models

class Inventory(models.Model):
    product_id = models.IntegerField(db_index=True)   # product id from ProductService
    shop_id = models.IntegerField(db_index=True)      # shop id from ShopService
    stock = models.IntegerField(default=0)
    reserved = models.IntegerField(default=0)         # reserved for pending orders
    threshold = models.IntegerField(default=0)       # alert when stock < threshold
    meta = models.JSONField(default=dict, blank=True)  # optional extra metadata
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("product_id", "shop_id")
        ordering = ["-updated_at"]

    def available(self):
        """Return currently available (not reserved) quantity."""
        return max(self.stock - self.reserved, 0)

    def __str__(self):
        return f"Inventory product={self.product_id} shop={self.shop_id} stock={self.stock} reserved={self.reserved}"
