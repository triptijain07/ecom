# gateway/urls.py
from django.urls import path, re_path
from .views import GatewayView

urlpatterns = [
    # Matches /api/<service>/<any_path>/
    re_path(r'^api/(?P<service_name>\w+)/(?P<path>.*)$', GatewayView.as_view(), name='gateway')
]
