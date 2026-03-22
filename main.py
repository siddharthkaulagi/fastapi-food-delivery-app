from fastapi import FastAPI, Query, Response, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# -------------------------
# DATA
# -------------------------

menu = [
    {"id": 1, "name": "Pizza", "price": 200, "category": "Food", "is_available": True},
    {"id": 2, "name": "Burger", "price": 150, "category": "Food", "is_available": True},
    {"id": 3, "name": "Coke", "price": 50, "category": "Drink", "is_available": True},
    {"id": 4, "name": "Fries", "price": 100, "category": "Food", "is_available": False},
    {"id": 5, "name": "Ice Cream", "price": 120, "category": "Dessert", "is_available": True},
    {"id": 6, "name": "Sandwich", "price": 130, "category": "Food", "is_available": True}
]

orders = []
cart = []

order_counter = 1
menu_counter = 7

# -------------------------
# HELPERS
# -------------------------

def find_item(item_id):
    for item in menu:
        if item["id"] == item_id:
            return item
    return None

# -------------------------
# MODELS
# -------------------------

class OrderRequest(BaseModel):
    customer_name: str = Field(min_length=2)
    item_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=20)
    delivery_address: str = Field(min_length=10)

class NewMenuItem(BaseModel):
    name: str = Field(min_length=2)
    price: int = Field(gt=0)
    category: str = Field(min_length=2)
    is_available: bool = True

class CheckoutRequest(BaseModel):
    customer_name: str
    delivery_address: str

# -------------------------
# DAY 1
# -------------------------

@app.get("/")
def home():
    return {"message": "Welcome to QuickBite Food Delivery"}

@app.get("/menu")
def get_menu():
    return {"items": menu, "total": len(menu)}

@app.get("/menu/summary")
def summary():
    available = sum(1 for i in menu if i["is_available"])
    return {
        "total": len(menu),
        "available": available,
        "unavailable": len(menu) - available
    }

# -------------------------
# DAY 6 (IMPORTANT ORDER)
# -------------------------

@app.get("/menu/search")
def search(keyword: str):
    result = [
        i for i in menu
        if keyword.lower() in i["name"].lower()
        or keyword.lower() in i["category"].lower()
    ]
    return {"results": result, "total": len(result)}

@app.get("/menu/filter")
def filter_menu(
    category: Optional[str] = None,
    max_price: Optional[int] = None,
    is_available: Optional[bool] = None
):
    result = menu

    if category:
        result = [i for i in result if i["category"].lower() == category.lower()]

    if max_price:
        result = [i for i in result if i["price"] <= max_price]

    if is_available is not None:
        result = [i for i in result if i["is_available"] == is_available]

    return {"items": result, "count": len(result)}

@app.get("/menu/sort")
def sort_items(sort_by: str = "price", order: str = "asc"):
    return {
        "items": sorted(menu, key=lambda x: x[sort_by], reverse=(order == "desc"))
    }

@app.get("/menu/page")
def paginate(page: int = 1, limit: int = 3):
    start = (page - 1) * limit
    return {"items": menu[start:start+limit]}

@app.get("/menu/browse")
def browse(keyword: Optional[str] = None, page: int = 1, limit: int = 3):
    data = menu

    if keyword:
        data = [i for i in data if keyword.lower() in i["name"].lower()]

    start = (page - 1) * limit
    return {"items": data[start:start+limit], "total": len(data)}

# -------------------------
# MUST BE LAST
# -------------------------

@app.get("/menu/{item_id}")
def get_item(item_id: int):
    item = find_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/orders")
def get_orders():
    return {"orders": orders, "total_orders": len(orders)}

# -------------------------
# DAY 4 CRUD
# -------------------------

@app.post("/menu", status_code=201)
def add_item(item: NewMenuItem):
    global menu_counter

    for i in menu:
        if i["name"].lower() == item.name.lower():
            raise HTTPException(status_code=400, detail="Item already exists")

    new_item = item.dict()
    new_item["id"] = menu_counter
    menu.append(new_item)
    menu_counter += 1

    return new_item

@app.put("/menu/{item_id}")
def update_item(item_id: int, price: Optional[int] = None, is_available: Optional[bool] = None):
    item = find_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if price is not None:
        item["price"] = price

    if is_available is not None:
        item["is_available"] = is_available

    return item

@app.delete("/menu/{item_id}")
def delete_item(item_id: int):
    item = find_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    menu.remove(item)
    return {"message": "Deleted"}

# -------------------------
# DAY 5 CART
# -------------------------

@app.post("/cart/add")
def add_to_cart(item_id: int, quantity: int = 1):
    item = find_item(item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if not item["is_available"]:
        raise HTTPException(status_code=400, detail="Out of stock")

    for c in cart:
        if c["item_id"] == item_id:
            c["quantity"] += quantity
            c["subtotal"] = c["quantity"] * item["price"]
            return {"message": "Cart updated", "cart_item": c}

    new_item = {
        "item_id": item_id,
        "name": item["name"],
        "quantity": quantity,
        "subtotal": item["price"] * quantity
    }

    cart.append(new_item)
    return {"message": "Added to cart", "cart_item": new_item}

@app.get("/cart")
def view_cart():
    total = sum(i["subtotal"] for i in cart)
    return {"items": cart, "grand_total": total, "item_count": len(cart)}

@app.delete("/cart/{item_id}")
def remove_cart_item(item_id: int):
    for c in cart:
        if c["item_id"] == item_id:
            cart.remove(c)
            return {"message": "Removed"}
    raise HTTPException(status_code=404, detail="Item not in cart")

@app.post("/cart/checkout")
def checkout(data: CheckoutRequest):
    global order_counter

    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty — add items first")

    created_orders = []
    total = 0

    for c in cart:
        new_order = {
            "order_id": order_counter,
            "customer_name": data.customer_name,
            "item": c["name"],
            "quantity": c["quantity"],
            "total_price": c["subtotal"]
        }
        orders.append(new_order)
        created_orders.append(new_order)
        total += c["subtotal"]
        order_counter += 1

    cart.clear()

    return {"orders": created_orders, "grand_total": total}