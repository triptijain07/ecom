from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Product, ProductImage
from .serializers import ProductSerializer, ProductImageSerializer
from .permissions import IsShopOwner, IsShopOwnerOfProduct
from .jwt_utils import verify_access_token
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
import math
import requests

# URL of your ShopService
SHOP_SERVICE_URL = "http://127.0.0.1:8001/api/shops/"  # adjust if deployed

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(available=True).order_by('-updated_at')
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'price', 'sku']
    search_fields = ['name', 'description', 'tags', 'shop_name']
    ordering_fields = ['price', 'updated_at']
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'bulk_create']:
            return [IsShopOwner()]
        return super().get_permissions()

    def get_payload(self):
        """
        Decode JWT token from request.auth and return payload dict.
        """
        token = getattr(self.request, "auth", None)  # JWT string
        if not token:
            return None
        return verify_access_token(token)



    def perform_create(self, serializer):
        payload = self.get_payload()
        if not payload:
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed("Invalid or expired token")

        user_id = payload.get("user_id")
        role = payload.get("role")
        token = getattr(self.request, "auth", None)

        if role != "shop_owner":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only shop owners can create products")

        shops = get_owner_shops(user_id, token)
        if not shops:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("No shop found for this owner")

        shop = shops[0]  # pick first shop for now
        serializer.save(
            shop_id=shop["id"],
            shop_name=shop["name"],
            shop_lat=shop.get("latitude"),
            shop_lng=shop.get("longitude")
        )


    def perform_update(self, serializer):
        obj = self.get_object()
        perm = IsShopOwnerOfProduct()
        if not perm.has_object_permission(self.request, self, obj):
            raise PermissionDenied("You can't modify products of other shops.")
        serializer.save()

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        q = request.query_params.get('q')
        lat = request.query_params.get('lat')
        lng = request.query_params.get('lng')
        radius_km = float(request.query_params.get('radius_km') or 5.0)
        qs = Product.objects.filter(available=True)

        if q:
            qs = qs.filter(name__icontains=q)

        if lat and lng:
            try:
                lat = float(lat)
                lng = float(lng)
                R = 6371.0  # Earth radius in km
                results = []

                for p in qs:
                    if p.shop_lat is None or p.shop_lng is None:
                        continue
                    lat1 = math.radians(lat)
                    lng1 = math.radians(lng)
                    lat2 = math.radians(p.shop_lat)
                    lng2 = math.radians(p.shop_lng)
                    dlat = lat2 - lat1
                    dlng = lng2 - lng1
                    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
                    c = 2 * math.asin(min(1, math.sqrt(a)))
                    distance = R * c
                    if distance <= radius_km:
                        results.append((p, distance))

                results.sort(key=lambda x: x[1])
                serializer = ProductSerializer([r[0] for r in results], many=True, context={'request': request})
                data = serializer.data
                for i, (_, dist) in enumerate(results):
                    data[i]['distance_km'] = round(dist, 3)
                return Response(data)
            except Exception:
                return Response({"detail": "Invalid lat/lng"}, status=status.HTTP_400_BAD_REQUEST)

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = ProductSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = ProductSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='image-search')
    def image_search(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({"detail": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        matches = call_image_search_service(image)
        products = Product.objects.filter(id__in=matches, available=True)
        serializer = ProductSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='upload-image',
            permission_classes=[IsShopOwnerOfProduct])
    def upload_image(self, request, pk=None):
        product = self.get_object()
        image_file = request.FILES.get('image')
        alt_text = request.data.get('alt_text', '')
        if not image_file:
            return Response({"detail": "No image uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        img = ProductImage.objects.create(product=product, image=image_file, alt_text=alt_text)
        serializer = ProductImageSerializer(img, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='upload-images',
            permission_classes=[IsShopOwnerOfProduct])
    def upload_images(self, request, pk=None):
        product = self.get_object()
        images = request.FILES.getlist('images')
        alt_texts = request.data.getlist('alt_texts')
        if not images:
            return Response({"detail": "No images uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        created_images = []
        for i, image_file in enumerate(images):
            alt_text = alt_texts[i] if i < len(alt_texts) else ''
            img = ProductImage.objects.create(product=product, image=image_file, alt_text=alt_text)
            created_images.append(img)
        serializer = ProductImageSerializer(created_images, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def call_image_search_service(image_file):
    """
    Placeholder for image search microservice.
    Returns list of matching product IDs.
    """
    return []

def get_owner_shops(user_id, token):
        """
        Call ShopService to fetch shops for this owner.
        """
        headers = {"Authorization": f"Bearer {token}"}
        try:
            resp = requests.get(f"{SHOP_SERVICE_URL}?owner_id={user_id}", headers=headers)
            if resp.status_code != 200:
                raise PermissionDenied("Could not fetch shops from ShopService")
            data = resp.json()
            if isinstance(data, dict) and "results" in data:
                return data["results"]  # DRF paginated response
            return data  # normal list
        except Exception:
            raise PermissionDenied("ShopService unavailable")