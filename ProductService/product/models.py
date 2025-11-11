import string
import random
from django.db import models
from django.utils import timezone

def generate_sku():
    """Generate a random 8-character alphanumeric SKU."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    # Product core fields
    sku = models.CharField(max_length=64, unique=True, db_index=True, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    available = models.BooleanField(default=True)

    # Shop snapshot fields (avoid cross-service calls)
    shop_id = models.IntegerField(db_index=True)
    shop_name = models.CharField(max_length=255)
    shop_lat = models.FloatField(null=True, blank=True)
    shop_lng = models.FloatField(null=True, blank=True)

    # Optional extra metadata for searching
    tags = models.JSONField(default=list, blank=True)  # e.g., ["leather", "sofa"]

    def save(self, *args, **kwargs):
        if not self.sku:
            sku = generate_sku()
            while Product.objects.filter(sku=sku).exists():
                sku = generate_sku()
            self.sku = sku
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} — {self.shop_name}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="product_images/")
    alt_text = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return f"Image for {self.product_id}"
