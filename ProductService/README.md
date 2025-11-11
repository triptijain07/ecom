Nice — this is a great architecture for an e-commerce platform. Below I’ll give a complete, ready-to-use **Django microservice** for the **Product Service** (Django + Django REST Framework). It includes:

* models (products, images, categories, shop snapshot),
* serializers,
* viewsets / endpoints for **customers** and **shop owners**,
* simple auth/permission integration assuming an external Auth microservice (JWT),
* a location/radius search (Haversine) to return products from nearest shops,
* a placeholder for **image-search** integration (call your image search / recognition microservice),
* notes on syncing shop data and production considerations.

I’ll keep the code runnable and explain each endpoint and how it’s used by both websites.

---

# 1 — Assumptions & design notes

* You already have `auth` and `shop` microservices.
* `auth` issues JWT tokens. Tokens contain a `role` claim (`customer` or `shop_owner`) and if `shop_owner`, a `shop_id` or user can manage multiple shops; adapt as needed.
* Product service stores product records and a **snapshot** of shop location (`shop_id`, `shop_name`, `lat`, `lng`). This avoids having to query the shop service for every location search (sync via events or periodic sync API).
* Image search will be implemented by calling an external image-search microservice (or embedding your model). In the code I show a placeholder function `call_image_search_service`.
* For nearest-shop searches we use the Haversine formula in Django ORM annotate (works with floats — no GeoDjango dependency).

---

# 2 — Project skeleton (files)

```
product_service/
├─ product_service/         # django project
│  ├─ settings.py
│  ├─ urls.py
│  └─ ...
├─ products/                # app
│  ├─ models.py
│  ├─ serializers.py
│  ├─ views.py
│  ├─ urls.py
│  └─ permissions.py
├─ requirements.txt
├─ Dockerfile
└─ manage.py
```

---

# 3 — requirements.txt

```text
Django>=4.2
djangorestframework
djangorestframework-simplejwt   # optional if you want local JWT validation
Pillow                           # for image fields
django-filter
psycopg2-binary                  # if using PostgreSQL
```

---

# 4 — models.py (products/models.py)

```python
from django.db import models
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name

class Product(models.Model):
    # product core fields
    sku = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    available = models.BooleanField(default=True)

    # shop snapshot fields (not foreign key to avoid cross-service calls)
    shop_id = models.IntegerField(db_index=True)
    shop_name = models.CharField(max_length=255)
    shop_lat = models.FloatField(null=True, blank=True)
    shop_lng = models.FloatField(null=True, blank=True)

    # optional extra metadata for searching
    tags = models.JSONField(default=list, blank=True)  # e.g. ["leather", "sofa"]

    def __str__(self):
        return f"{self.name} — {self.shop_name}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name="images", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="product_images/")
    alt_text = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Image for {self.product_id}"
```

---

# 5 — permissions.py (products/permissions.py)

```python
from rest_framework import permissions

class IsShopOwner(permissions.BasePermission):
    """
    Allow access only to users with role 'shop_owner' (based on JWT claim or request.user).
    We assume authentication middleware decodes JWT and sets request.user or request.auth payload.
    """

    def has_permission(self, request, view):
        # If you use SimpleJWT and custom claim 'role':
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            # If user has attr 'role' from token
            role = getattr(user, "role", None)
            if role is not None:
                return role == "shop_owner"
        # Fallback: check raw token payload
        payload = getattr(request, "auth", None)
        if payload and isinstance(payload, dict):
            return payload.get("role") == "shop_owner"
        return False

class IsShopOwnerOfProduct(permissions.BasePermission):
    """
    Allow object-level operations only if request.user (or token) corresponds to product.shop_id.
    """

    def has_object_permission(self, request, view, obj):
        # check owner by comparing shop id in token/payload
        payload = getattr(request, "auth", None)
        if payload and isinstance(payload, dict):
            token_shop_ids = payload.get("shop_ids") or []
            # token could carry single shop_id as int
            if isinstance(token_shop_ids, int):
                token_shop_ids = [token_shop_ids]
            return int(obj.shop_id) in [int(s) for s in token_shop_ids]
        # If request.user has attribute shop_id:
        shop_id = getattr(request.user, "shop_id", None)
        if shop_id:
            return int(obj.shop_id) == int(shop_id)
        return False
```

> Note: adapt permission checks to how your auth service exposes user/shop claims in JWT.

---

# 6 — serializers.py (products/serializers.py)

```python
from rest_framework import serializers
from .models import Product, ProductImage, Category

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text")

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    class Meta:
        model = Product
        fields = (
            "id","sku","name","description","price","category",
            "available","shop_id","shop_name","shop_lat","shop_lng",
            "tags","images","created_at","updated_at"
        )
        read_only_fields = ("shop_id","shop_name","shop_lat","shop_lng","created_at","updated_at")
```

---

# 7 — views.py (products/views.py)

Important features:

* `ProductViewSet` provides CRUD for shop owners and read endpoints for customers.
* `search` endpoint supports text search and radius-based location filtering.
* `image_search` endpoint accepts uploaded image and returns matching products (placeholder).

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import F, FloatField
from django.db.models.functions import Cast
from django.db.models import Value as V
from .models import Product, ProductImage, Category
from .serializers import ProductSerializer, ProductImageSerializer, CategorySerializer
from .permissions import IsShopOwner, IsShopOwnerOfProduct
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
import math

class ProductViewSet(viewsets.ModelViewSet):
    """
    ModelViewSet for Product.
    - list / retrieve: available to customers (and owners).
    - create/update/destroy: only shop owners and only for their shop (checked in perform_create/perform_update).
    Extra endpoints:
    - /products/search/?q=...&lat=..&lng=..&radius_km=...
    - /products/image-search/ (POST image file) -> calls image-search microservice
    """
    queryset = Product.objects.filter(available=True).order_by('-updated_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]  # object-level permissions handled below
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'price', 'sku']
    search_fields = ['name','description','tags','shop_name']
    ordering_fields = ['price','updated_at']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'bulk_create']:
            return [IsShopOwner()]
        return super().get_permissions()

    def perform_create(self, serializer):
        # Shop info must come from token (we don't trust client)
        payload = getattr(self.request, "auth", None) or {}
        # payload may have 'shop_id' or 'shop_ids'
        shop_id = payload.get("shop_id") or (payload.get("shop_ids") and payload.get("shop_ids")[0])
        shop_name = payload.get("shop_name")
        shop_lat = payload.get("shop_lat")
        shop_lng = payload.get("shop_lng")
        # fallback: allow client fields only if no token (NOT recommended)
        if not shop_id:
            # optional: raise PermissionDenied
            raise Exception("No shop_id in token; cannot create product")
        serializer.save(shop_id=shop_id, shop_name=shop_name or "Unknown shop",
                        shop_lat=shop_lat, shop_lng=shop_lng)

    def perform_update(self, serializer):
        # ensure owner edits only their product
        obj = self.get_object()
        # check object-level permission
        perm = IsShopOwnerOfProduct()
        if not perm.has_object_permission(self.request, self, obj):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You can't modify products of other shops.")
        serializer.save()

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """
        Query params:
          - q: text query
          - lat, lng: customer location (floats)
          - radius_km: radius in kilometers (int/float)
          - category
        Returns products matching text and within radius, annotated with distance_km.
        """
        q = request.query_params.get('q')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius_km = float(request.query_params.get('radius_km') or 5.0)  # default 5 km

        qs = Product.objects.filter(available=True)

        if q:
            qs = qs.filter(name__icontains=q)  # simple text search; you can replace with full-text

        # If lat/lng provided, annotate with distance using Haversine
        if lat and lng:
            try:
                lat = float(lat); lng = float(lng)
                # Haversine calculation in annotation (approx)
                # formula adapted for DB annotation:
                # distance = 2 * R * ASIN( sqrt( sin^2((lat2-lat1)/2) + cos(lat1)*cos(lat2)*sin^2((lng2-lng1)/2) ) )
                R = 6371.0  # Earth radius in km
                from django.db.models import ExpressionWrapper, F, Func, Value
                # We'll push simple formula into DB using raw SQL function calls via Func
                # For cross-db portability you might compute in Python after filtering bounding box.
                # Simpler approach: compute exact distances in Python (when dataset small) — fallback below.
                # Here do a naive DB annotation using casted floats; if DB doesn't support trig funcs, fallback.
                qs = list(qs)  # fallback compute in python
                def haversine(p):
                    if p.shop_lat is None or p.shop_lng is None:
                        return None
                    lat2 = math.radians(p.shop_lat)
                    lng2 = math.radians(p.shop_lng)
                    lat1 = math.radians(lat)
                    lng1 = math.radians(lng)
                    dlat = lat2 - lat1
                    dlng = lng2 - lng1
                    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*(math.sin(dlng/2)**2)
                    c = 2 * math.asin(min(1, math.sqrt(a)))
                    return R * c
                # compute distances and filter
                results = []
                for p in qs:
                    d = haversine(p)
                    if d is None:
                        continue
                    if d <= radius_km:
                        results.append((p, d))
                # sort by distance
                results.sort(key=lambda x: x[1])
                serializer = ProductSerializer([r[0] for r in results], many=True, context={'request': request})
                data = serializer.data
                # annotate distance into response:
                for i, (_, dist) in enumerate(results):
                    data[i]['distance_km'] = round(dist, 3)
                return Response(data)
            except Exception as e:
                return Response({"detail": "Invalid lat/lng"}, status=status.HTTP_400_BAD_REQUEST)

        # otherwise just normal filtered list
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ProductSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = ProductSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='image-search')
    def image_search(self, request):
        """
        Accepts multipart/form-data with 'image' file.
        Calls external image-retrieval microservice that returns product identifiers or tags.
        We'll call a placeholder function here - replace with your model/service call.
        """
        image = request.FILES.get('image')
        if not image:
            return Response({"detail":"No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        # Placeholder: call your image search/vision microservice:
        matches = call_image_search_service(image)  # returns list of product ids or tags

        if not matches:
            return Response({"results": []})

        # If matches are product ids:
        products = Product.objects.filter(id__in=matches, available=True)
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

def call_image_search_service(image_file):
    """
    Placeholder - integrate with your image search microservice.
    Example:
      - POST image to /vision/search -> returns list of product ids or tags.
      - Or run feature extractor + query vector DB (faiss/milvus) and return product ids.
    For now, return [] to indicate no matches.
    """
    # TODO: replace with real call (requests.post to your microservice)
    return []
```

---

# 8 — urls.py (products/urls.py and project urls)

`products/urls.py`:

```python
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = router.urls
```

`product_service/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('products.urls')),
]
```

---

# 9 — Authentication integration

Two approaches:

1. **JWT validation locally:** Use `djangorestframework-simplejwt` with the same secret/public key as auth service to decode tokens in this microservice. Token claims will contain `role`, `shop_id`, etc. Then `request.user` or `request.auth` carries those claims.

2. **Introspect tokens with auth service:** On each request call auth service's `/token/verify` or `/userinfo` to validate and obtain roles. This adds network latency but centralizes auth.

**Example (simple):** set DRF `DEFAULT_AUTHENTICATION_CLASSES` to a custom `JWTAuthentication` that decodes token and attaches a simple `user` object with `role` and `shop_id` claims.

---

# 10 — How each endpoint will be used (customer vs shop owner website)

I'll list endpoints and explain expected clients & auth:

## Public / Customer endpoints

(All customers can use these — no special role required.)

1. `GET /api/v1/products/`

   * Purpose: browse all available products (global listing).
   * Query params: `page`, `ordering=price`, `search` (via `?search=shirt`).
   * Response: paginated products with images and shop snapshot.

2. `GET /api/v1/products/{id}/`

   * Purpose: product details page. Shows product attributes and merchant (shop snapshot). Customers can click `shop_lat/lng` to view the shop on map.

3. `GET /api/v1/products/search/?q=...&lat=...&lng=...&radius_km=...`

   * Purpose: **search by text + location radius**. Use when customer searches text or image — returns products from shops within the radius sorted by distance.
   * Example: `?q=red%20sofa&lat=19.0760&lng=72.8777&radius_km=10`

4. `POST /api/v1/products/image-search/`

   * Purpose: customer uploads image to search visually similar products.
   * Flow: frontend uploads image -> product service sends image to vision microservice -> receives matched product ids or tags -> returns product list.
   * Output: list of matching products (product ids + shop snapshot). Use to show nearest matches.

## Shop owner endpoints (require shop\_owner role / JWT)

1. `POST /api/v1/products/`

   * Purpose: create a product for the shop of the logged-in owner.
   * Behavior: server reads `shop_id` from token claims and sets `shop_id`,`shop_name`,`shop_lat`,`shop_lng`. Owners cannot create products for other shops.

2. `PUT/PATCH /api/v1/products/{id}/`

   * Purpose: update product (only allowed for products that belong to the shop owner). Object-level permission checks compare product.shop\_id to shop\_id in the token.

3. `DELETE /api/v1/products/{id}/`

   * Purpose: remove product (soft-delete recommended, here we can set `available=False`).

4. `POST /api/v1/products/{id}/images/` (you can add a nested view for images)

   * Purpose: upload product images (only owner).

5. Bulk endpoints (optional): `POST /api/v1/products/bulk_create/` to create many products (CSV/JSON) — helpful for onboarding shop owners.

---

# 11 — Syncing shop data (important)

Because shop location matters for radius search, keep a shop snapshot stored in Product rows. To keep snapshots fresh:

* Option A: **Event-driven** — when shop updates location/name, Shop microservice emits an event (Kafka/RabbitMQ) to Product service; Product service updates all relevant product rows' `shop_lat` and `shop_lng`.
* Option B: **On-demand** — store only `shop_id` and when search occurs, query Shop service for locations for shops in candidate set (adds network calls).
* Option C: **Periodic sync** — cron job fetches shop list and updates product snapshots.

Event-driven is recommended for near-real-time consistency.

---

# 12 — Image search integration (high-level)

* Option A: Run a feature extractor (ResNet, EfficientNet, CLIP) to get image embeddings for product images; store them in a vector DB (FAISS, Milvus, Pinecone). Query with customer image to return top K product ids.
* Option B: If you already have an ML microservice, call it: `POST /vision/search` with the image file → returns list of product ids → query products table for these ids and return product+shop snapshot sorted by proximity.

In the provided code `call_image_search_service` is a placeholder; implement actual HTTP call or internal python call.

---

# 13 — Example usage flows

### Customer flow — text search then view nearest shops:

1. Customer types "leather chair".
2. Frontend calls: `GET /api/v1/products/search/?q=leather%20chair&lat=19.07&lng=72.87&radius_km=10`
3. Product service returns a list of products with `distance_km` per product. Frontend shows product cards and map pins using `shop_lat/shop_lng`. Clicking pin opens the shop page on your frontend which can call Shop microservice for full shop details.

### Customer flow — image search:

1. Customer uploads product image in frontend.
2. Frontend `POST /api/v1/products/image-search/` with the image file.
3. Product service calls vision microservice; receives product ids; returns product objects for nearest shops. Frontend displays matches and map pins.

### Shop owner flow — manage products:

1. Shop owner signs in using Auth service; obtains JWT (role `shop_owner`, `shop_id`).
2. Owner goes to dashboard, sends `POST /api/v1/products/` with product details and images. Product service reads `shop_id` from token and assigns ownership.
3. Owner can `PUT/PATCH` or `DELETE` their products. Object-level permission prevents editing others' products.

---

# 14 — Recommendations / production considerations

* Use vector DB for fast image similarity search (Milvus/FAISS/Pinecone).
* Use full-text search (Postgres `tsvector` or ElasticSearch) for better text search.
* Use Geo indexing (PostGIS) for efficient radius queries if you expect many shops/products.
* Soft delete instead of hard delete.
* Rate-limit image-search endpoint (expensive).
* Use event-driven sync for shop snapshots.
* CDN for images and S3-compatible storage (use `django-storages`).

---

# 15 — Quick Dockerfile (optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["gunicorn", "product_service.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
```

---

# 16 — Example curl requests

Create product (owner):

```bash
curl -X POST https://products.example.com/api/v1/products/ \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Classic Leather Sofa",
    "description":"3-seater leather sofa",
    "price":"24999.00",
    "category": 3,
    "tags":["leather","sofa","livingroom"]
  }'
```

Search by text & location (customer):

```bash
curl "https://products.example.com/api/v1/products/search/?q=sofa&lat=19.0760&lng=72.8777&radius_km=10"
```

Image search:

```bash
curl -X POST "https://products.example.com/api/v1/products/image-search/" \
  -F "image=@/path/to/photo.jpg"
```

---

# 17 — What I didn't implement here (and quick next steps you might want)

* Full JWT decoding middleware — adapt to your auth tokens.
* Image-upload nested route for adding images to products (you can add a `ProductImageViewSet`).
* Vector DB and image-embedding pipeline.
* Robust Haversine in DB (for production use PostGIS instead of Python list convert).
* Tests, serializers for create with nested images.

---

If you want, I can:

* provide the full file contents in a GitHub-ready repo (models, views, settings).
* implement JWT authentication middleware that decodes your auth JWT structure (give me one sample token or token claims).
* add a `ProductImageViewSet` to handle image uploads and S3 integration.
* convert the radius search to use PostGIS for production scale.

Which of those should I generate next?
