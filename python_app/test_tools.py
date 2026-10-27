"""Quick test of the car tools + graph import (no API key needed)."""
import json
import tools
from graph import app_graph

print("tools:", [t.name for t in tools.tools])
suv = tools.search_cars.invoke({"body_type": "SUV", "max_price": 1000000000, "in_stock_only": True, "sort": "price_asc"})
print("SUV duoi 1 ty con xe:", [(c["name"], c["price_text"], c["status"]) for c in suv["cars"]])
print("7 cho:", [c["name"] for c in tools.search_cars.invoke({"min_seats": 7})["cars"]])
print("Dien:", [(c["name"], c["price_text"], c["status"]) for c in tools.search_cars.invoke({"fuel": "Điện"})["cars"]])
print("Khuyen mai:", [(c["name"], c["promotion"]) for c in tools.search_cars.invoke({"has_promotion": True})["cars"]])
d = tools.get_car_details.invoke({"sku": "HON-CRV-L"})
print("Chi tiet HON-CRV-L:", d["name"], d["price_text"], d["status"])
print("Showroom:", json.dumps(tools.list_showroom_overview.invoke({}), ensure_ascii=False)[:300])
print("graph nodes:", list(app_graph.get_graph().nodes.keys()))