# gateway/utils.py
import requests
from rest_framework.response import Response
from rest_framework import status

def forward_request(service_url, path, method="GET", data=None, headers=None):
    url = f"{service_url}{path}"
    try:
        response = requests.request(method, url, json=data, headers=headers)
        return Response(response.json(), status=response.status_code)
    except requests.exceptions.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
