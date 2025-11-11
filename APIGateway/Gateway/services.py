# gateway/services.py

AUTH_SERVICE_URL = "http://localhost:8001"      # Auth microservice
SHOP_SERVICE_URL = "http://localhost:8002"      # ShopService
PRODUCT_SERVICE_URL = "http://localhost:8003"   # ProductService
INVENTORY_SERVICE_URL = "http://localhost:8004" # InventoryService
ORDER_SERVICE_URL = "http://localhost:8005"     # OrderService
PAYMENT_SERVICE_URL = "http://localhost:8006"

MICROSERVICES = {
    "auth": AUTH_SERVICE_URL,
    "shop": SHOP_SERVICE_URL,
    "product": PRODUCT_SERVICE_URL,
    "inventory": INVENTORY_SERVICE_URL,  # Added InventoryService
    "order": ORDER_SERVICE_URL,
    "payment": PAYMENT_SERVICE_URL,
}
