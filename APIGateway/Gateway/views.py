# gateway/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .services import MICROSERVICES
from .utils import forward_request

class GatewayView(APIView):
    """
    Generic API Gateway view
    """

    def get_service_url(self, service_name):
        return MICROSERVICES.get(service_name)

    def get(self, request, service_name, path):
        service_url = self.get_service_url(service_name)
        if not service_url:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        return forward_request(service_url, f"/{path}", method="GET", headers=request.headers)

    def post(self, request, service_name, path):
        service_url = self.get_service_url(service_name)
        if not service_url:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        return forward_request(service_url, f"/{path}", method="POST", data=request.data, headers=request.headers)

    def put(self, request, service_name, path):
        service_url = self.get_service_url(service_name)
        if not service_url:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        return forward_request(service_url, f"/{path}", method="PUT", data=request.data, headers=request.headers)

    def delete(self, request, service_name, path):
        service_url = self.get_service_url(service_name)
        if not service_url:
            return Response({"error": "Service not found"}, status=status.HTTP_404_NOT_FOUND)
        return forward_request(service_url, f"/{path}", method="DELETE", headers=request.headers)
