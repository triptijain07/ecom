from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from math import radians, cos, sin, asin, sqrt

from shops.authentication import JWTAuthentication
from .models import Shop
from .serializers import ShopSerializer

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates in kilometers.
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    R = 6371  # Earth radius in km
    return R * c

class ShopViewSet(viewsets.ModelViewSet):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Save owner_id from authenticated user
        serializer.save(owner_id=self.request.user.id)

    @action(detail=False, methods=['get'], url_path='nearby')
    def nearby(self, request):
        lat = request.query_params.get('lat')
        lon = request.query_params.get('long')
        radius_km = request.query_params.get('radius', 10)

        if not lat or not lon:
            return Response({"error": "lat and long query parameters are required"}, status=400)

        try:
            lat = float(lat)
            lon = float(lon)
            radius_km = float(radius_km)
        except ValueError:
            return Response({"error": "Invalid lat, long, or radius values"}, status=400)

        shops_in_radius = []
        for shop in Shop.objects.exclude(latitude__isnull=True, longitude__isnull=True):
            distance = haversine(lat, lon, float(shop.latitude), float(shop.longitude))
            if distance <= radius_km:
                shop.distance_km = round(distance, 2)
                shops_in_radius.append(shop)

        serializer = self.get_serializer(shops_in_radius, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        qs = super().get_queryset()
        owner_id = self.request.query_params.get("owner_id")
        if owner_id:
            qs = qs.filter(owner_id=owner_id)
        return qs