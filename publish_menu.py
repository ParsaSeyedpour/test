import ast
import logging
import mimetypes
import os
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Dict, List, Literal, Optional, Tuple, Union

from fastapi import APIRouter, Depends, HTTPException
from kavenegar import APIException, KavenegarAPI
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import FileResponse

from image_compress.image_compress import ImageProcessor, UploadConfig
from menu.schemas import MenuResponse

sys.path.append("..")
import json
import random
import string
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from fastapi import (APIRouter, Depends, File, Form, HTTPException, Query,
                     UploadFile, status)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_pagination import Page, paginate
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, exc, selectinload
from sqlalchemy.orm.attributes import flag_modified

# import tempfile, os, xlsxwriter
# import openpyxl
import models
from database import SessionLocal, engine
from members import members

models.Base.metadata.create_all(bind=engine)

SECRET_KEY = "test"
ALGORITHM = "HS256"

bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(
    prefix="/menu", tags=["Menu"], responses={400: {"description": "Not found"}}
)


class MultiLanguage(BaseModel):
    language_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None


class Category(BaseModel):
    type: Literal["category"] = (
        "category"  # Required for MenuItemResponse discriminator
    )
    id: Optional[str] = None
    title: str
    cat_image: str  # Changed to str to match CreateCategory
    description: str  # Changed to str (non-optional) to match CreateCategory
    parent_id: Optional[int] = None  # Added from CreateCategory
    parent_is_menu: bool  # Added from CreateCategory
    menu_id: int  # Added from CreateCategory
    enabled: Optional[int] = None  # Added from CreateCategory
    multi_language_data: Optional[List[MultiLanguage]] = None
    children: List[Union["Category", "Food"]] = []


class SizeItem(BaseModel):
    id: str
    name: str
    size: Optional[str] = None
    price: Optional[float] = None
    status: Optional[str] = None
    url: Optional[str] = None


class LanguageData(BaseModel):
    language_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None


# Response Models
class Menu(BaseModel):
    type: Literal["menu"]
    id: str
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    is_primary: Optional[bool] = None
    currency: Optional[str] = None
    show_price: Optional[bool] = None
    show_store_info: Optional[bool] = None
    template_name: Optional[str] = None
    theme_url: Optional[str] = None
    customizable_background: bool = False
    smart_template: Optional[bool] = None
    background_image: Optional[Union[List[str], str]] = []
    position: Optional[int] = None
    children: List["Category"] = []
    multi_language_data: Optional[List[LanguageData]] = None
    template_color: Optional[str] = None


class Food(BaseModel):
    type: Literal["food"] = "food"
    id: Optional[str] = None
    menu_id: int
    category_id: int
    title: str
    englishTitle: str
    price: int
    food_image: List[str] = []
    food_video: str
    description: str
    discount: Optional[int] = None
    ready_by_time: Optional[int] = None
    available: Optional[int] = None
    sizes: Optional[List[Any]] = []
    multi_language_data: Optional[List[MultiLanguage]] = None


class SizeEnum(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class CartItem(BaseModel):
    id: int
    quantity: int
    size: Optional[SizeEnum] = None


class CustomerInfo(BaseModel):
    name: str
    mobile: str
    description: Optional[str] = None
    payment_method: Optional[int] = None
    address: Optional[str] = None
    room_number: Optional[str] = None
    table_number: Optional[str] = None


class CartOrderRequest(BaseModel):
    cart: List[CartItem]
    info: CustomerInfo


class CartOrderResponse(BaseModel):
    success: bool
    order_id: int
    unique_address: str
    total_price: float
    message: str


# Update forward references
Menu.update_forward_refs()
Category.update_forward_refs()
Food.update_forward_refs()

# Define the union response model with discriminator
MenuItemResponse = Annotated[Union[Menu, Category, Food], Field(discriminator="type")]


class MultiLanguageMenu(BaseModel):
    language_id: str
    description: str

    class Config:
        json_encoders = {"MultiLanguageMenu": lambda v: v.dict()}


class MenuItemType(str, Enum):
    MENU = "menu"
    CATEGORY = "category"
    FOOD = "food"


class Size(BaseModel):
    url: Optional[str] = None
    size: Optional[str] = None
    price: Optional[str] = None
    title: Optional[str] = None
    status: Optional[int] = None


class FoodDetail(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    food_image: Optional[List[str]] = None
    sizes: Optional[List[Size]] = None
    englishTitle: Optional[str] = None
    available: Optional[int] = None
    cat_id: Optional[int] = None
    store_id: Optional[int] = None
    price: Optional[str] = None
    food_video: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    position: Optional[int] = None


class OrderItem(BaseModel):
    quantity: Optional[int] = None
    id: Optional[int] = None
    price: Optional[int] = None
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    product_type: Optional[str] = None
    unit_price: Optional[int] = None
    food_detail: Optional[FoodDetail] = None


class PaymentMethod(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    merchant_id: Optional[str] = None


class StoreInfos(BaseModel):
    zip_code: Optional[str] = None
    default_url: Optional[str] = None
    onboarding_option: Optional[int] = None
    verification_code: Optional[str] = None
    tax_value: Optional[int] = None
    payment_gateway: Optional[bool] = None
    province: Optional[str] = None
    payment_methods: Optional[List[PaymentMethod]] = None
    brand_logo: Optional[str] = None
    brand_name: Optional[str] = None
    online_order: Optional[bool] = None


class OrderDetails(BaseModel):
    form_type: Optional[int] = None
    tax_value: Optional[int] = None
    id: Optional[int] = None
    customer_name: Optional[str] = None
    address: Optional[str] = None
    room_number: Optional[str] = None
    discount: Optional[int] = None
    store_id: Optional[int] = None
    unique_address: Optional[str] = None
    shop_id: Optional[int] = None
    cellphone: Optional[str] = None
    description: Optional[str] = None
    table_number: Optional[str] = None
    payment_status: Optional[str] = None
    store_info: Optional[StoreInfos] = None
    items: Optional[List[OrderItem]] = None


class OrderResponse(BaseModel):
    success: Optional[bool] = None
    order_detail: Optional[OrderDetails] = None


class CreateMenu(BaseModel):
    title: str
    description: str
    theme_url: str
    currency: str
    show_price: bool
    show_store_info: bool
    is_primary: bool
    menu_background: Optional[str] = None
    smart_template: Optional[bool] = None
    template_name: str = None
    shop_id: Optional[int] = None
    multi_language_data: Optional[List[MultiLanguageMenu]] = None

    class Config:
        json_encoders = {"MultiLanguageMenu": lambda v: v.dict()}


class EditMenu(CreateMenu):
    new_title: Optional[str] = None
    template_color: Optional[str] = None


class MultiSize(BaseModel):
    url: str | None = None
    title: str | None = None
    size: Optional[str] = None
    id: Optional[str] = None


class ProductDetails(BaseModel):
    id: int
    title: str
    food_image: List[str]
    sizes: List[str] | List[MultiSize] | None = None
    englishTitle: str | None = None
    available: int
    cat_id: int | None = None
    store_id: int | None = None
    price: str
    food_video: str
    description: str
    enabled: int
    position: int


class OrderItems(BaseModel):
    id: int
    order_id: int
    quantity: Optional[int] = None
    price: int
    product_id: int
    product_type: str | None = None
    unit_price: int
    product_detail: ProductDetails | None = None


class OrdersResponseDetail(BaseModel):
    id: int
    form_type: int
    shop_id: int
    cellphone: str | None = None
    description: str | None = None
    table_number: str | None = None
    payment_status: Optional[str] = None
    unique_address: str | None = None
    store_id: int
    discount_code: Optional[str] = None
    discount: Optional[int] = None
    order_time: datetime
    customer_name: str | None = None
    address: str | None = None
    room_number: str | None = None
    payment_method_id: Optional[int] = None
    order_status: int
    order_items: List[OrderItems]
    couriers_id: Optional[int] = None
    couriers_fee: Optional[float] = None


class PaginatedOrdersResponse(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int
    items: List[OrdersResponseDetail]


class ChangeOrderStatus(BaseModel):
    order_id: int
    status: int
    payment_status: Optional[str] = None
    also_inform_customer: Optional[bool] = None
    payment_method_id: Optional[int] = None
    couriers_id: Optional[int] = None
    couriers_fee: Optional[float] = None


class DragMenu(BaseModel):
    menu_id: List[int] = []


class PriceManager(BaseModel):
    menu_id: int
    fix_price: Optional[int] = None
    percent_price: Optional[int] = None
    categories: List[int] = []


class CreateOrderStepTwo(BaseModel):
    customer_name: str
    address: str
    cellphone: str
    description: str
    unique_address: str
    discount_code: Optional[str] = None
    discount_value: Optional[str] = None
    form_type: int
    payment_method_id: Optional[int] = None
    room_number: str | None = None
    table_number: str | None = None
    location: Optional[str] = None


class CreateOrder(BaseModel):
    product_id: List[int]
    quantity: List[int] = None
    unit_price: List[int] = None
    product_type: List[str] | None = None
    discount: int
    customer_name: str
    cellphone: str
    address: str
    description: str
    place_number: str
    store_id: int | None = None
    shop_id: int | None = None


class PaymentMethods(BaseModel):
    id: int
    title: Optional[str] = None
    description: Optional[str] = None
    merchant_id: Optional[str] = None


class StoreInfo(BaseModel):
    brand_logo: Optional[str] = None
    online_order: bool
    brand_name: str
    tax_value: int
    default_url: str
    payment_methods: Optional[List[PaymentMethods]]
    payment_gateway: bool


class OrderDetail(BaseModel):
    id: int
    form_type: int
    order_time: datetime
    customer_name: Optional[str] = None
    address: Optional[str] = None
    room_number: Optional[int] = None
    discount: int
    order_status: int
    store_id: int
    unique_address: str
    shop_id: int
    cellphone: Optional[str] = None
    description: Optional[str] = None
    table_number: Optional[str] = None
    payment_status: Optional[str] = None
    store_info: StoreInfo


class GetOrderResponse(BaseModel):
    success: bool
    order_detail: OrderDetail
    items: List[Any]


class PublishMenu(BaseModel):
    backgroundColor: str | None = None
    secondColor: str | None = None


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_password_hashed(password):
    return bcrypt_context.hash(password)


def verify_password(password, hashed_password):
    return bcrypt_context.verify(password, hashed_password)


@router.get("/menu/show/{store_url}")
async def show_menu_restaurant(store_url: str):
    if FileResponse(f"./templates/{store_url}"):
        return FileResponse(f"./templates/{store_url}")
    else:
        raise HTTPException(status_code=404, detail="menu not found")


@router.get("/images/{image_address}/{image_name}")
async def read_member_profile(image_address: str, image_name: str):
    if FileResponse(f"./store_assets/{image_address}/{image_name}"):
        return FileResponse(f"./store_assets/{image_address}/{image_name}")
    else:
        raise HTTPException(status_code=404, detail="not found")


async def get_current_user(token: str = Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        username: str = payload.get("sub")
        user_id: str = payload.get("id")
        if user_id is None or username is None:
            raise get_user_exception()
        return {"id": user_id, "username": username}
    except JWTError:
        raise get_user_exception()


@router.put("/orders/{order_id}")
def update_order(order_id: int, order_data: Dict, db: Session = Depends(get_db)):
    # Find the existing order
    order = (
        db.query(models.OnlineOrders).filter(models.OnlineOrders.id == order_id).first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Process added items
    added_items = order_data.get("added_items", [])
    for item in added_items:
        new_order_item = models.OrderItem()
        new_order_item.order_id = (order_id,)
        new_order_item.product_id = (item.get("product_id"),)
        new_order_item.product_type = (item.get("product_type", ""),)
        new_order_item.quantity = (item.get("quantity", 1),)
        new_order_item.unit_price = (item.get("unit_price"),)
        new_order_item.price = item.get("price")

        db.add(new_order_item)

    # Process removed items
    removed_items = order_data.get("removed_items", [])
    for item in removed_items:
        # Find and delete the specific order item
        db.query(models.OrderItem).filter(
            and_(
                models.OrderItem.order_id == order_id,
                models.OrderItem.product_id == item.get("product_id"),
            )
        ).delete()

    # Process changed items
    changed_items = order_data.get("changed_items", [])
    for item in changed_items:
        # Find the existing order item and update it
        existing_item = (
            db.query(models.OrderItem)
            .filter(
                and_(
                    models.OrderItem.order_id == order_id,
                    models.OrderItem.product_id == item.get("product_id"),
                )
            )
            .first()
        )

        if existing_item:
            # Update all possible fields
            existing_item.quantity = item.get("quantity", existing_item.quantity)
            existing_item.unit_price = item.get("unit_price", existing_item.unit_price)
            existing_item.price = item.get("price", existing_item.price)
            existing_item.product_type = item.get(
                "product_type", existing_item.product_type
            )

    # Update order-level discount
    order.discount = order_data.get("discount_amount", order.discount)

    try:
        db.commit()
        db.refresh(order)
        return {
            "success": True,
            "order_id": order_id,
            "added_items_count": len(added_items),
            "removed_items_count": len(removed_items),
            "changed_items_count": len(changed_items),
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def parse_product_id(combined_id: str) -> Tuple[int, Optional[str]]:
    """Parse the combined ID (e.g., '12-a' or '12') into food ID and size identifier"""
    try:
        combined_id = str(combined_id)
        if "-" in combined_id:
            food_id, size_identifier = combined_id.split("-")
            return int(food_id), size_identifier
        return int(combined_id), None
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid product ID format")


def get_food_price_by_size(food: models.Foods, size: Optional[str] = None) -> float:
    """Get the price for a food item, considering size if provided"""
    if not size or not food.sizes:
        return float(food.price or 0)

    sizes = json.loads(food.sizes) if isinstance(food.sizes, str) else food.sizes
    for size_option in sizes:
        if size_option.get("size") == size:
            return float(size_option.get("price", 0))
    return 0.0


@router.put("/v2/orders/{order_id}")
def update_order_version2(
    order_id: int, order_data: Dict, db: Session = Depends(get_db)
):

    order = (
        db.query(models.OnlineOrders).filter(models.OnlineOrders.id == order_id).first()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:

        added_items = order_data.get("added_items", [])
        for item in added_items:
            # Parse the combined ID to get food_id and size
            product_id = item.get("id", "")
            if not product_id:
                raise HTTPException(status_code=400, detail="Product ID is required")

            food_id, size_identifier = parse_product_id(product_id)

            # Get the food item from database
            food = db.query(models.Foods).filter(models.Foods.id == food_id).first()
            if not food:
                raise HTTPException(
                    status_code=404, detail=f"Food item {food_id} not found"
                )

            # Get the price based on whether size is specified
            size = item.get("size") if size_identifier else None
            unit_price = get_food_price_by_size(food, size)
            total_price = unit_price * item.get("quantity", 1)

            new_order_item = models.OrderItem(
                order_id=order_id,
                product_id=food_id,
                product_type="food",
                quantity=item.get("quantity", 1),
                unit_price=unit_price,
                price=total_price,
                size=size,  # Will be None for items without size
            )
            db.add(new_order_item)

        # Process removed items
        removed_items = order_data.get("removed_items", [])
        for item in removed_items:
            product_id = item.get("id", "")
            if not product_id:
                continue

            food_id, size_identifier = parse_product_id(product_id)

            query = db.query(models.OrderItem).filter(
                and_(
                    models.OrderItem.order_id == order_id,
                    models.OrderItem.product_id == food_id,
                )
            )

            if item.get("size"):
                query = query.filter(models.OrderItem.size == item.get("size"))

            query.delete()

        # Process changed items
        changed_items = order_data.get("changed_items", [])
        for item in changed_items:
            product_id = item.get("id", "")
            if not product_id:
                continue  # Skip items without ID

            food_id, size_identifier = parse_product_id(product_id)

            query = db.query(models.OrderItem).filter(
                and_(
                    models.OrderItem.order_id == order_id,
                    models.OrderItem.product_id == food_id,
                )
            )

            # Add size filter only if size is specified
            if item.get("size"):
                query = query.filter(models.OrderItem.size == item.get("size"))

            existing_item = query.first()
            if existing_item:
                # Get the food item for price calculation
                food = db.query(models.Foods).filter(models.Foods.id == food_id).first()
                if food:
                    unit_price = get_food_price_by_size(food, item.get("size"))
                    quantity = item.get("quantity", existing_item.quantity)
                    existing_item.quantity = quantity
                    existing_item.unit_price = unit_price
                    existing_item.price = unit_price * quantity
                    if "size" in item:
                        existing_item.size = item["size"]

        # Update order-level discount
        order.discount = order_data.get("discount_amount", order.discount)

        db.commit()
        db.refresh(order)

        return {
            "success": True,
            "order_id": order_id,
            "added_items_count": len(added_items),
            "removed_items_count": len(removed_items),
            "changed_items_count": len(changed_items),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"Unexpected error in update_order_version2: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/create_order")
def create_order(create_order_info: CreateOrder, db: Session = Depends(get_db)):
    user_info = (
        db.query(models.Members)
        .filter(models.Members.id == create_order_info.store_id)
        .first()
    )
    if user_info.online_order:
        new_order = models.OnlineOrders()
        random_address = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
        )
        new_order.unique_address = random_address
        new_order.order_time = datetime.utcnow()
        new_order.payment_method_id = 0
        new_order.unit_price = create_order_info.unit_price
        new_order.payment_status = "pending"
        new_order.store_id = user_info.id
        if create_order_info.shop_id is not None:
            shop_detail = (
                db.query(models.Shops)
                .filter(models.Shops.id == create_order_info.shop_id)
                .first()
            )
            new_order.form_type = shop_detail.form_type
            new_order.shop_id = create_order_info.shop_id
        else:
            new_order.form_type = user_info.form_type

        db.add(new_order)
        db.commit()
        total_price = 0
        for index, item in enumerate(create_order_info.product_id):
            order_item = models.OrderItem()
            order_item.product_id = item
            order_item.quantity = create_order_info.quantity[index]
            order_item.unit_price = create_order_info.unit_price[index]
            order_item.price = (
                create_order_info.unit_price[index] * create_order_info.quantity[index]
            )
            order_item.order_id = new_order.id
            total_price += order_item.price
            db.add(order_item)

        new_order.total_price = total_price
        try:
            db.commit()
            return {
                "success": True,
                "order_id": new_order.id,
                "address": new_order.unique_address,
            }
        except Exception as ex:
            if isinstance(ex, HTTPException):
                raise ex
            raise HTTPException(status_code=403, detail=str(ex))
    raise HTTPException(
        status_code=403, detail="You don't have access to use this feature"
    )


async def send_sms_array(receptor: List[str], sender: str, message: str):
    all_phones = ""
    for phone in receptor:
        all_phones = all_phones + phone + ","
    try:
        api = KavenegarAPI(
            "33754B555A565749536550413342704F6E3042657A4D65496A4F7A38316D48764F7A5551354E6E315674553D"
        )
        params = {"sender": sender, "receptor": all_phones, "message": message}

        response = api.sms_send(params)
        return response
    except APIException as e:
        return str(e)
    except HTTPException as e:
        return str(e)


@router.post("/create_step_two")
async def create_order_step_two(
    next_step: CreateOrderStepTwo, db: Session = Depends(get_db)
):
    # Find the order
    find_order = (
        db.query(models.OnlineOrders)
        .filter(models.OnlineOrders.unique_address == next_step.unique_address)
        .first()
    )
    if not find_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Find the store
    check_order = (
        db.query(models.Members)
        .filter(models.Members.id == find_order.store_id)
        .first()
    )
    if not check_order:
        raise HTTPException(status_code=404, detail="Store not found")
    if not check_order.online_order:
        raise HTTPException(
            status_code=403, detail="You don't have access to use this feature"
        )

    try:
        # Track if customer is new
        is_new_customer = False
        customer = None
        if next_step.cellphone:
            customer = (
                db.query(models.Customer)
                .filter(models.Customer.cellphone == next_step.cellphone)
                .first()
            )
            if not customer:
                customer = models.Customer(
                    fname=next_step.customer_name,
                    cellphone=next_step.cellphone,
                    address=next_step.address,
                    register_date=datetime.utcnow(),
                )
                db.add(customer)
                db.flush()  # Get customer ID before commit
                is_new_customer = True

        # Update order with customer_id and location
        if customer:
            find_order.customer_id = customer.id
        find_order.location = next_step.location  # <--- your requested line

        # Update order details
        find_order.description = next_step.description
        if next_step.payment_method_id is not None:
            find_order.payment_method_id = next_step.payment_method_id
        find_order.address = next_step.address
        find_order.customer_name = next_step.customer_name
        find_order.cellphone = next_step.cellphone
        if next_step.room_number:
            find_order.room_number = next_step.room_number
        if next_step.table_number:
            find_order.table_number = next_step.table_number
        find_order.order_status = 1

        # Handle discount
        if next_step.discount_code:
            find_discount = (
                db.query(models.DiscountCode)
                .filter(
                    and_(
                        models.DiscountCode.code == next_step.discount_code,
                        models.DiscountCode.store_id == find_order.store_id,
                    )
                )
                .first()
            )
            if find_discount:
                total_price = find_order.total_price
                discount_amount = total_price * (find_discount.percent / 100)
                find_order.discount = discount_amount
                find_discount.used_count += 1
                find_order.discount_code = next_step.discount_code

        # Handle contact creation/updating
        if next_step.cellphone:
            find_tag = (
                db.query(models.Tag)
                .filter(
                    models.Tag.title == "سفارش آنلاین",
                    models.Tag.store_id == check_order.id,
                )
                .first()
            )

            if not find_tag:
                find_tag = models.Tag(
                    title="سفارش آنلاین", enabled=True, store_id=check_order.id
                )
                db.add(find_tag)
                db.flush()

            existing_contact = (
                db.query(models.Contact)
                .filter(
                    models.Contact.store_id == check_order.id,
                    models.Contact.phone == find_order.cellphone,
                )
                .first()
            )

            if not existing_contact:
                contact = models.Contact(
                    store_id=check_order.id,
                    name=next_step.customer_name,
                    family_name="",
                    phone=next_step.cellphone,
                    tag_name=find_tag.title,
                    tag_id=find_tag.id,
                    customer_id=customer.id if customer else None,
                )
                db.add(contact)
            elif customer:
                existing_contact.customer_id = customer.id

        # SMS handling (with order number in customer SMS)
        if check_order.remaining_sms > 4:
            sum_sms_count = 0
            base_url = (
                check_order.default_url
                if "https://" in check_order.default_url
                else f"{os.getenv('MENU_BASE_URL')}{check_order.default_url}"
            )
            url_suffix = ".html" if ".html" not in base_url else ""

            # Customer SMS (order number included)
            customer_sms = (
                f"{next_step.customer_name} عزیز\n"
                f"سفارش شما به شماره پیگیری {find_order.id} با موفقیت ثبت شد.\n"
                f"{base_url}{url_suffix}\n"
                f"{check_order.brand_name}\nلغو11"
            )
            response_receipt = await send_sms_array(
                [find_order.cellphone], "200004044", customer_sms
            )
            sum_sms_count += int(len(customer_sms) / 70) + 2

            # Store owner SMS
            owner_sms = (
                f"یک سفارش برای مجموعه {check_order.brand_name} ثبت شده است.\n"
                f'{base_url.split("/")[-2]}\nلغو11'
            )
            response_customer = await send_sms_array(
                [check_order.cellphone], "200004044", owner_sms
            )
            sum_sms_count += int(len(owner_sms) / 70) + 2

            # Additional notification number
            if check_order.online_order_sms:
                second_number = await send_sms_array(
                    [check_order.online_order_sms], "200004044", owner_sms
                )
                sum_sms_count += int(len(owner_sms) / 70) + 2

            check_order.remaining_sms -= sum_sms_count

        db.commit()
        return {
            "success": True,
            "is_new_customer": is_new_customer,
            "customer_id": customer.id if customer else None,
        }

    except Exception as ex:
        db.rollback()
        if isinstance(ex, HTTPException):
            raise ex
        raise HTTPException(status_code=403, detail=str(ex))


@router.get("/get_order_detail/{unique_address}")
def get_order_detail(unique_address: str, db: Session = Depends(get_db)):
    order_detail = (
        db.query(models.OnlineOrders)
        .filter(models.OnlineOrders.unique_address == unique_address)
        .first()
    )
    if order_detail is not None:
        if order_detail.shop_id > 0:
            shop_id = (
                db.query(models.Shops)
                .filter(models.Shops.id == order_detail.shop_id)
                .first()
            )
            order_detail.shop_info = shop_id
        else:
            store_info = (
                db.query(models.Members)
                .filter(models.Members.id == order_detail.store_id)
                .first()
            )
            order_detail.store_info = store_info
        oder_items = (
            db.query(models.OrderItem)
            .filter(models.OrderItem.order_id == order_detail.id)
            .all()
        )
        for food in oder_items:
            food_detail = (
                db.query(models.Foods)
                .filter(models.Foods.id == food.product_id)
                .first()
            )
            food.food_detail = food_detail
        order_detail.items = oder_items
        return {"success": True, "order_detail": order_detail}
    raise HTTPException(status_code=404, detail="Order not found")


@router.get("/get_order_detail_2/{unique_address}")
def get_order_detail_2(unique_address: str, db: Session = Depends(get_db)):
    order_detail = (
        db.query(models.OnlineOrders)
        .filter(models.OnlineOrders.unique_address == unique_address)
        .first()
    )
    if order_detail is not None:
        if order_detail.shop_id > 0:
            shop_id = (
                db.query(models.Shops)
                .filter(models.Shops.id == order_detail.shop_id)
                .first()
            )
            order_detail.tax_value = shop_id.tax_value
            order_detail.shop_info = shop_id
        else:
            store_info = (
                db.query(models.Members)
                .filter(models.Members.id == order_detail.store_id)
                .first()
            )
            order_detail.tax_value = store_info.tax_value
            order_detail.store_info = store_info
        oder_items = (
            db.query(models.OrderItem)
            .filter(models.OrderItem.order_id == order_detail.id)
            .all()
        )
        for food in oder_items:
            food_detail = (
                db.query(models.Foods)
                .filter(models.Foods.id == food.product_id)
                .first()
            )
            food.food_detail = food_detail
        order_detail.items = oder_items
        return {"success": True, "order_detail": order_detail}
    raise HTTPException(status_code=404, detail="Order not found")


@router.get("/check_order_feature")
def check_order_feature(store_id: int, db: Session = Depends(get_db)):
    user_info = db.query(models.Members).filter(models.Members.id == store_id).first()
    return {"online_order_feature": user_info.online_order}


@router.post("/change_order_status")
async def change_order_status(
    order_status: ChangeOrderStatus, db: Session = Depends(get_db)
):
    find_order = (
        db.query(models.OnlineOrders)
        .filter(models.OnlineOrders.id == order_status.order_id)
        .first()
    )
    if order_status.payment_method_id is not None:
        find_order.payment_method_id = order_status.payment_method_id
    find_order.order_status = order_status.status
    if order_status.payment_status:
        find_order.payment_status = order_status.payment_status
    if order_status.couriers_id is not None:
        find_order.couriers_id = order_status.couriers_id
    if order_status.couriers_fee is not None:
        find_order.couriers_fee = order_status.couriers_fee

    status = "در حال پردازش"
    if order_status.status == 2:
        status = "تایید شده و در حال پردازش "
    elif order_status.status == 3:
        status = "آماده شده و در حال ارسال "
    elif order_status.status == 4:
        status = "انجام شده "
    elif order_status.status == 5:
        status = "لغو شده"
    sum_sms_count = 0

    if find_order.shop_id > 0:
        find_shop = (
            db.query(models.Shops).filter(models.Shops.id == find_order.shop_id).first()
        )
        find_store = (
            db.query(models.Members)
            .filter(models.Members.id == find_order.store_id)
            .first()
        )
        if order_status.status != 4:
            if (
                order_status.also_inform_customer
                and order_status.also_inform_customer == True
            ):
                if find_store.remaining_sms > 4:
                    response_receipt = await send_sms_array(
                        [find_order.cellphone],
                        "200004044",
                        f"{find_order.customer_name} عزیز\nسفارش شما به شماره پیگیری {find_order.id}  {status} است.\n\n{find_shop.brand_name}"
                        + "\nلغو11",
                    )
                    sum_sms_count += (
                        int(
                            len(
                                f"{find_order.customer_name} عزیز\nسفارش شما به شماره پیگیری {find_order.id}  {status} است.\n\n{find_shop.brand_name}"
                                + "\nلغو11"
                            )
                            / 70
                        )
                        + 2
                    )
                    find_store.remaining_sms = find_store.remaining_sms - sum_sms_count

    else:
        find_store = (
            db.query(models.Members)
            .filter(models.Members.id == find_order.store_id)
            .first()
        )
        if order_status.status != 4:
            if (
                order_status.also_inform_customer
                and order_status.also_inform_customer == True
            ):
                if find_store.remaining_sms > 4:
                    response_receipt = await send_sms_array(
                        [find_order.cellphone],
                        "200004044",
                        f"{find_order.customer_name} عزیز\nسفارش شما به شماره پیگیری {find_order.id}  {status} است.\n\n{find_store.brand_name}"
                        + "\nلغو11",
                    )
                    sum_sms_count += (
                        int(
                            len(
                                f"{find_order.customer_name} عزیز\nسفارش شما به شماره پیگیری {find_order.id}  {status} است.\n\n{find_store.brand_name}"
                                + "\nلغو11"
                            )
                            / 70
                        )
                        + 2
                    )
                    find_store.remaining_sms = find_store.remaining_sms - sum_sms_count
    db.add(find_order)
    db.add(find_store)
    try:
        db.commit()
        return {"success": True}

    except Exception as ex:
        if isinstance(ex, HTTPException):
            raise ex
        raise HTTPException(status_code=403, detail=str(ex))


@router.get("/new_order_count")
def get_new_order_count(
    store_id: int | None = None,
    shop_id: int | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if store_id is None and shop_id is None:
        raise HTTPException(
            status_code=400, detail="store_id or shop_id must be provided"
        )

    query = db.query(models.OnlineOrders).filter(models.OnlineOrders.order_status == 1)

    if store_id is not None:
        query = query.filter(models.OnlineOrders.store_id == store_id)
    elif shop_id is not None:
        query = query.filter(models.OnlineOrders.shop_id == shop_id)

    all_orders = query.all()
    new_order_count = len(all_orders)

    last_order = query.order_by(models.OnlineOrders.order_time.desc()).first()
    last_order_detail = None

    if last_order:
        order_items = (
            db.query(models.OrderItem)
            .filter(models.OrderItem.order_id == last_order.id)
            .all()
        )
        last_order_detail = {"order": last_order, "items": order_items}

    return {"new_order_count": new_order_count, "last_order_detail": last_order_detail}


@router.get("/store_order", response_model=PaginatedOrdersResponse)
async def get_store_orders_main(
    store_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    order_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_info = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    if user_info.online_order or user_info.waiter_panel:
        # if order_status:
        #     service_ty_items = order_status.split(',')
        #     query = db.query(models.OnlineOrders).filter(models.OnlineOrders.order_status).in_(service_ty_items)
        if order_status is not None:
            query = db.query(models.OnlineOrders)
            order_status_list = [int(status) for status in order_status.split(",")]
            query = query.filter(
                models.OnlineOrders.order_status.in_(order_status_list)
            )

        else:
            query = db.query(models.OnlineOrders).filter(
                models.OnlineOrders.order_status != 0
            )
        if store_id is not None:
            query = query.filter(models.OnlineOrders.store_id == store_id)
        elif shop_id is not None:
            query = query.filter(models.OnlineOrders.shop_id == shop_id)

        total_orders = query.count()
        orders = (
            query.order_by(models.OnlineOrders.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        for item in orders:
            order_items = (
                db.query(models.OrderItem)
                .filter(models.OrderItem.order_id == item.id)
                .all()
            )
            for order_item in order_items:
                find_food = (
                    db.query(models.Foods)
                    .filter(models.Foods.id == order_item.product_id)
                    .first()
                )
                order_item.product_detail = find_food
            item.order_items = order_items

        return {
            "total": total_orders,
            "page": page,
            "page_size": page_size,
            "pages": int(total_orders / page_size) + 1,
            "items": orders,
        }
    raise HTTPException(status_code=403, detail="You don't have access to this feature")


def build_category_trees(
    categories: List[models.FoodCategory], parent_id: int = None, menu_id: int = 0
) -> List[Category]:
    """
    Recursively build the category tree structure
    """
    tree = []

    for category in categories:
        if (category.parent_id == menu_id) or (category.parent_id == parent_id):
            cat_data = Category(
                id=category.id,
                title=category.title,
                description=category.description,
                cat_image=category.cat_image,
                enabled=category.enabled,
                position=category.position,
            )
            # Recursively get children
            cat_data.children = build_category_trees(categories, category.id, menu_id)
            tree.append(cat_data)

    return sorted(tree, key=lambda x: x.position)  # Sort by position


@router.get("/v2/store_order", response_model=PaginatedOrdersResponse)
async def get_store_orders_version2(
    store_id: Optional[int] = None,
    shop_id: Optional[int] = None,
    order_status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_info = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    if user_info.online_order:
        query = db.query(models.OnlineOrders)

        # Handle order statuses
        if order_status is not None:
            order_status_list = [int(status) for status in order_status.split(",")]
            query = query.filter(
                models.OnlineOrders.order_status.in_(order_status_list)
            )
        else:
            query = query.filter(models.OnlineOrders.order_status != 0)

        # Filter by store or shop
        if store_id is not None:
            query = query.filter(models.OnlineOrders.store_id == store_id)
        elif shop_id is not None:
            query = query.filter(models.OnlineOrders.shop_id == shop_id)

        total_orders = query.count()
        orders = (
            query.order_by(models.OnlineOrders.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        items_response = []
        for item in orders:
            order_items = (
                db.query(models.OrderItem)
                .filter(models.OrderItem.order_id == item.id)
                .all()
            )

            for idx, order_item in enumerate(order_items):
                find_food = (
                    db.query(models.Foods)
                    .filter(models.Foods.id == order_item.product_id)
                    .first()
                )
                order_item.product_detail = find_food

                # Populate the size IDs if sizes exist
                if find_food and find_food.sizes:
                    for size_idx, size in enumerate(find_food.sizes):
                        if isinstance(size, dict) and "id" not in size:
                            size["id"] = f"{find_food.id}-{size_idx + 1}"

                # Assign the modified food item back to order item.
                if find_food:
                    order_item.product_detail.sizes = (
                        find_food.sizes
                    )  # Make sure to assign the modified sizes

            item_dict = jsonable_encoder(item)
            item_dict["order_items"] = order_items
            item_dict["couriers_id"] = getattr(item, "couriers_id", None)
            item_dict["couriers_fee"] = getattr(item, "couriers_fee", None)
            items_response.append(item_dict)
            # item.order_items = order_items

        return {
            "total": total_orders,
            "page": page,
            "page_size": page_size,
            "pages": (total_orders // page_size)
            + (1 if total_orders % page_size > 0 else 0),
            "items": items_response,
        }

    raise HTTPException(status_code=403, detail="You don't have access to this feature")


@router.get("/v2/get_foods")
async def get_all_foods_menu_version2(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user:
        raise get_user_exception()

    menu = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"), models.Menu.is_primary == True)
        .order_by(models.Menu.position.asc())
        .first()
    )

    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    categories = (
        db.query(models.FoodCategory)
        .filter(models.FoodCategory.menu_id == menu.id)
        .order_by(models.FoodCategory.position.asc())
        .all()
    )

    if menu.multi_language_data:
        menu.multi_language_data = json.loads(menu.multi_language_data)

    menu.category = categories

    for category in categories:
        foods = (
            db.query(models.Foods)
            .filter(models.Foods.available == 1, models.Foods.enabled == True)
            .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
            .filter(
                models.MenuIDS.menu_id == menu.id, models.MenuIDS.cat_id == category.id
            )
            .order_by(models.Foods.position.asc())
            .all()
        )

        if category.multi_language_data:
            category.multi_language_data = json.loads(category.multi_language_data)

        for food in foods:
            if food.multi_language_data:
                food.multi_language_data = json.loads(food.multi_language_data)

            # Handle foods with sizes
            if food.sizes and isinstance(food.sizes, (str, list, dict)):
                sizes = (
                    json.loads(food.sizes)
                    if isinstance(food.sizes, str)
                    else food.sizes
                )
                if sizes:  # Only process if sizes is not empty
                    # Add ID to each size using food ID and letter
                    for idx, size in enumerate(sizes):
                        size["id"] = f"{food.id}-{string.ascii_lowercase[idx]}"
                    food.sizes = sizes

        category.foods = foods

    return {"menu": menu}


@router.get("/v2/{menu_id}", response_model=MenuResponse)
async def get_menu_structure(menu_id: int, db: Session = Depends(get_db)):
    """
    Get menu with nested categories and subcategories by menu_id
    """
    # Get the menu
    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    # Get all categories for this menu
    categories = (
        db.query(models.FoodCategory)
        .filter(models.FoodCategory.menu_id == menu_id)
        .all()
    )

    # Build the nested structure
    category_tree = build_category_trees(categories, parent_id=None, menu_id=menu_id)

    # Create response
    response = MenuResponse(
        id=menu.id,
        title=menu.title,
        theme_url=menu.theme_url,
        currency=menu.currency,
        description=menu.description,
        children=category_tree,
        background_image=menu.background_image,
    )

    return response


@router.get("/store_order_test")
def get_store_orders(
    store_id: int | None = None,
    shop_id: int | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_info = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    if user_info.online_order:
        if store_id is not None:
            orders = (
                db.query(models.OnlineOrders)
                .join(
                    models.OrderItem,
                    models.OrderItem.order_id == models.OnlineOrders.id,
                )
                .filter(models.OnlineOrders.store_id == user_info.id)
                .limit(100)
                .all()
            )
            orderss = (
                db.query(models.OnlineOrders, models.OrderItem)
                .join(
                    models.OrderItem,
                    models.OrderItem.order_id == models.OnlineOrders.id,
                )
                .filter(models.OnlineOrders.store_id == user_info.id)
                .all()
            )
            final_res = []
            for test in orderss:
                res_obj = test[0]
                if len(final_res) == 0:
                    res_obj.product_detail = test[1]
                    final_res.append(res_obj)
                else:
                    for itw in final_res:
                        if res_obj.id == itw.id:
                            prd_detail = itw.product_detail
                            prd_detail.append(test[1])
                            itw.product_detail = prd_detail
                        else:
                            res_obj.product_detail = test[1]
                            final_res.append(res_obj)

            return final_res
            for item in orders:
                order_items = (
                    db.query(models.OrderItem)
                    .filter(models.OrderItem.order_id == item.id)
                    .all()
                )
                for order_item in order_items:
                    prd_detail = (
                        db.query(models.Foods)
                        .filter(models.Foods.id == order_item.product_id)
                        .first()
                    )
                    order_item.product_detail = prd_detail

                item.order_items = order_items
            return {"orders": orders}
        elif shop_id is not None:
            orders = (
                db.query(models.OnlineOrders)
                .filter(models.OnlineOrders.shop_id == shop_id)
                .limit(100)
                .all()
            )
            for item in orders:
                order_items = (
                    db.query(models.OrderItem)
                    .filter(models.OrderItem.order_id == item.id)
                    .all()
                )
                for order_item in order_items:
                    prd_detail = (
                        db.query(models.Foods)
                        .filter(models.Foods.id == order_item.product_id)
                        .first()
                    )
                    order_item.product_detail = prd_detail
                item.order_items = order_items
            return {"orders": orders}
    raise HTTPException(status_code=403, detail="You don't have access to this feature")


@router.get("/temp_preview/{temp_address}")
async def show_template_preview(temp_address: str):
    if os.path.exists(f"./assets/temp_preview/{temp_address}"):
        return FileResponse(f"./assets/temp_preview/{temp_address}")
    elif os.path.exists(f"./assets/temp_preview/{temp_address.lower()}"):
        return FileResponse(f"./assets/temp_preview/{temp_address.lower()}")
    else:
        raise HTTPException(status_code=404, detail="not found")


@router.get("/get_all_templates")
async def get_all_templates_preview(user: dict = Depends(get_current_user)):
    if not user:
        raise get_user_exception()
    res = []
    for temp_preview in os.walk("./assets/temp_preview"):
        for item in temp_preview[2]:
            if "_v" not in item:
                if ".m4v" not in item:
                    res.append(item)

        return {"all_templates": res}


def format_language_currencies(store_data):
    if not store_data.multi_language_currency:
        return None

    # Get the language_currencies data
    raw_data = (
        store_data.language_currencies
        if isinstance(store_data.language_currencies, list)
        else json.loads(store_data.language_currencies)
    )

    # Transform into desired format
    formatted_pairs = {}
    for item in raw_data:
        if isinstance(item, dict) and "language" in item and "currency" in item:
            formatted_pairs[item["language"]] = item["currency"]

    return formatted_pairs


@router.post("/upload_menu_template/")
async def upload_menu_temp(
    uploaded_file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(6))
    user_info = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    if not os.path.isdir(f"./store_assets/{user_info.unique_name}"):
        os.mkdir(f"./store_assets/{user_info.unique_name}")
    file_location = f"./store_assets/{user_info.unique_name}/{result_str}.png"
    with open(file_location, "wb+") as file_object:
        file_object.write(uploaded_file.file.read())
    return {"image_address": f"{user_info.unique_name}/{result_str}.png"}


@router.post("/menu_background/")
async def upload_menu_background(
    uploaded_file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Validate user
    user_info = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate random filename
    random_name = "".join(random.choices(string.ascii_lowercase, k=6))
    original_ext = ImageProcessor.get_file_extension(uploaded_file.filename) or ".png"
    filename = f"{random_name}{original_ext}"

    # Create target directory
    user_folder = f"./store_assets/{user_info.unique_name}"
    os.makedirs(user_folder, exist_ok=True)

    # Output path
    output_path = os.path.join(user_folder, filename)

    # Load upload configuration
    config = UploadConfig.get_config(
        "menu_background"
    )  # 3MB max, high quality, 1920x1080

    # Process image
    ImageProcessor.process_uploaded_image(
        uploaded_file=uploaded_file,
        output_path=output_path,
        max_size_kb=config["max_size_kb"],
        quality=config["quality"],
        max_dimensions=config["max_dimensions"],
    )

    # Calculate final image size
    final_size_kb = round(ImageProcessor.get_file_size_kb(output_path), 2)

    return {
        "success": True,
        "image_address": f"{user_info.unique_name}/{filename}",
        "final_size_kb": final_size_kb,
        "message": f"Image uploaded and optimized successfully (size: {final_size_kb} KB)",
    }


@router.put("/create_menu")
async def create_menu(
    menuInfo: CreateMenu,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()
    menu_exist = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"))
        .filter(models.Menu.title == menuInfo.title)
        .first()
    )
    if menu_exist:
        raise HTTPException(status_code=403, detail="Duplicate entry")

    userInfo = (
        db.query(models.Members, models.AccessType)
        .join(models.AccessType, models.Members.access_type == models.AccessType.id)
        .filter(models.Members.id == user.get("id"))
        .first()
    )
    access_menu = False
    templates_access = ""
    for index, item in enumerate(userInfo):
        if index == 1:
            access_menu = item.access_menu_maker
            templates_access = item.templates_access
    if access_menu:
        menu = models.Menu()
        menu.title = menuInfo.title
        if menuInfo.multi_language_data is not None:
            menu.multi_language_data = json.dumps(
                [item.model_dump() for item in menuInfo.multi_language_data]
            )
        menu.description = menuInfo.description
        if menuInfo.smart_template:
            menu.smart_template = menuInfo.smart_template
        if menuInfo.menu_background is not None:
            menu.background_image = menuInfo.menu_background
        if menuInfo.shop_id:
            menu.is_sub_shop = True
            menu.shop_id = menuInfo.shop_id
        menu.show_store_info = menuInfo.show_store_info
        menu.show_price = menuInfo.show_price
        menu.currency = menuInfo.currency
        menu.is_primary = menuInfo.is_primary
        menu.theme_url = menuInfo.theme_url
        menu.store_id = user.get("id")
        json_temps = json.dumps(templates_access)
        if "*" in json_temps:
            menu.template_name = menuInfo.template_name
        elif menuInfo.template_name in json_temps:
            menu.template_name = menuInfo.template_name
        else:
            raise HTTPException(
                status_code=403, detail="You can't select this template"
            )
        menu.date_creation = datetime.utcnow()
        db.add(menu)
        try:
            db.commit()
            return {"success": True}

        except Exception as ex:
            if isinstance(ex, HTTPException):
                raise ex
            raise HTTPException(status_code=403, detail=str(ex))
    raise HTTPException(
        status_code=402, detail="You don't have access to create a menu"
    )


@router.post("/edit_menu/{menu_id}")
async def edit_menu(
    menuInfo: EditMenu,
    menu_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()
    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    menu_exist = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"))
        .filter(models.Menu.title == menuInfo.new_title)
        .first()
    )
    if menu_exist:
        raise HTTPException(status_code=403, detail="Duplicate entry")
    menu.title = menuInfo.title
    if menuInfo.template_color:
        menu.template_color = menuInfo.template_color
    menu.description = menuInfo.description
    if menuInfo.multi_language_data is not None:
        menu.multi_language_data = json.dumps(
            [item.model_dump() for item in menuInfo.multi_language_data]
        )
    if menuInfo.menu_background is not None:
        menu.background_image = menuInfo.menu_background
    if menuInfo.smart_template:
        menu.smart_template = menuInfo.smart_template
    menu.show_store_info = menuInfo.show_store_info
    menu.show_price = menuInfo.show_price
    menu.currency = menuInfo.currency
    menu.is_primary = menuInfo.is_primary
    if menuInfo.shop_id:
        menu.is_sub_shop = True
        menu.shop_id = menuInfo.shop_id
    menu.theme_url = menuInfo.theme_url
    menu.template_name = menuInfo.template_name
    menu.store_id = user.get("id")
    db.add(menu)
    try:
        db.commit()
        return {"success": True}

    except Exception as ex:
        if isinstance(ex, HTTPException):
            raise ex
        raise HTTPException(status_code=403, detail=str(ex))


def remove_leading_zero(phone_number: str) -> str:
    if phone_number.startswith("0"):
        return phone_number[1:]
    return phone_number


@router.get("/primary_menu_template_name")
def get_menu_primary_template(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    find_template_name = (
        db.query(models.Menu)
        .filter(
            and_(models.Menu.store_id == user.get("id"), models.Menu.is_primary == True)
        )
        .first()
    )
    if find_template_name:
        return {"template_name": find_template_name.template_name}
    raise HTTPException(status_code=404, detail=" منویی با این مشخصات یافت نشد.")



def as_json(x: Any) -> Any:
    """
    Return dict/list if JSON string; pass through dict/list/None; keep other types as-is.
    Prevents json.loads() on dict/list (TypeError) and tolerates legacy string JSON.
    """
    if x is None or isinstance(x, (dict, list)):
        return x
    if isinstance(x, (bytes, bytearray)):
        try:
            x = x.decode("utf-8", errors="ignore")
        except Exception:
            return x
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return None
        try:
            import json
            return json.loads(s)
        except json.JSONDecodeError:
            return x
    return x


@router.get("/all_menus")
async def get_user_all_menus_v2(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    shop_id: Optional[int] = Query(None),
):
    if not user:
        raise get_user_exception()

    user_info = (
        db.query(models.Members)
        .filter(models.Members.id == user.get("id"))
        .first()
    )
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    # Menus for this store, filtered by shop_id rule
    query = db.query(models.Menu).filter(models.Menu.store_id == user.get("id"))
    if shop_id is not None:
        query = query.filter(models.Menu.shop_id == shop_id)
    else:
        query = query.filter(models.Menu.shop_id.is_(None))

    all_menus: List[models.Menu] = query.order_by(models.Menu.position.asc()).all()
    if not all_menus:
        raise HTTPException(status_code=404, detail="Menus not found")

    menu_response: List[Dict[str, Any]] = []

    for menu in all_menus:
        parsed_menu_mld = as_json(getattr(menu, "multi_language_data", None))
        menu_data: Dict[str, Any] = {
            "id": str(menu.id),
            "title": menu.title,
            "smart_template": bool(menu.smart_template),
            "type": "menu",
            "shop_id": menu.shop_id,
            "children": [],
            "active": bool(menu.is_primary),
        }
        if parsed_menu_mld is not None:
            menu_data["multi_language_data"] = parsed_menu_mld

        # Categories for this menu (ordered)
        all_categories: List[models.FoodCategory] = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.menu_id == menu.id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )

        # Build category map with conditional multi_language_data
        category_dict: Dict[int, Dict[str, Any]] = {}
        for category in all_categories:
            if category.parent_is_menu and category.parent_id == menu.id:
                item_type = "subcategory"
            elif category.parent_is_menu and (category.parent_id == 0 or category.parent_id is None):
                item_type = "category"
            else:
                item_type = "subcategory"

            parsed_cat_mld = as_json(getattr(category, "multi_language_data", None))
            entry: Dict[str, Any] = {
                "id": str(category.id),
                "title": category.title,
                "type": item_type,
                "children": [],
                "active": True,
            }
            if parsed_cat_mld is not None:
                entry["multi_language_data"] = parsed_cat_mld

            category_dict[category.id] = entry

        
        rows = (
            db.query(models.Foods, models.MenuIDS.cat_id)
            .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
            .filter(models.MenuIDS.menu_id == menu.id)
            .order_by(models.Foods.position.asc())
            .all()
        )
        foods_by_cat: Dict[int, List[models.Foods]] = {}
        for food, cat_id in rows:
            if cat_id not in foods_by_cat:
                foods_by_cat[cat_id] = []
            foods_by_cat[cat_id].append(food)

        # Attach foods to each category
        for category in all_categories:
            category_data = category_dict[category.id]
            foods = foods_by_cat.get(category.id, [])
            for food in foods:
                parsed_food_mld = as_json(getattr(food, "multi_language_data", None))
                food_entry: Dict[str, Any] = {
                    "id": str(food.id),
                    "title": getattr(food, "title", f"Food {food.id}"),
                    "type": "food",
                    "children": [],
                    "active": True,
                }
                if parsed_food_mld is not None:
                    food_entry["multi_language_data"] = parsed_food_mld
                category_data["children"].append(food_entry)

        # Build the final tree under the menu
        for category in all_categories:
            category_data = category_dict[category.id]
            pid = getattr(category, "parent_id", None)

            if not category.parent_is_menu and pid in category_dict:
                # Child-of-category
                category_dict[pid]["children"].append(category_data)
            elif category.parent_is_menu:
                # Top-level at menu
                menu_data["children"].append(category_data)
            elif not category.parent_is_menu and pid == menu.id:
                # Fallback as in your original logic
                menu_data["children"].append(category_data)

        menu_response.append(menu_data)

    return menu_response




# @router.get("/all_menus")
# async def get_user_all_menus_v2(
#     user: dict = Depends(get_current_user),
#     db: Session = Depends(get_db),
#     shop_id: Optional[int] = Query(None),
# ):
#     if not user:
#         raise get_user_exception()

#     # Validate user
#     user_info = (
#         db.query(models.Members).filter(models.Members.id == user.get("id")).first()
#     )
#     if not user_info:
#         raise HTTPException(status_code=404, detail="User not found")

#     # Apply correct filtering logic
#     query = db.query(models.Menu).filter(models.Menu.store_id == user.get("id"))

#     if shop_id is not None:
#         query = query.filter(models.Menu.shop_id == shop_id)
#     else:
#         query = query.filter(models.Menu.shop_id.is_(None))

#     all_menus = query.order_by(models.Menu.position.asc()).all()

#     menu_response = []

#     for menu in all_menus:
#         menu_data = {
#             "id": str(menu.id),
#             "title": menu.title,
#             "smart_template": menu.smart_template,
#             "type": "menu",
#             "shop_id": menu.shop_id,
#             "children": [],
#             "active": menu.is_primary,
#         }

#         all_categories = (
#             db.query(models.FoodCategory)
#             .filter(models.FoodCategory.menu_id == menu.id)
#             .order_by(models.FoodCategory.position.asc())
#             .all()
#         )

#         category_dict = {}
#         for category in all_categories:
#             if category.parent_is_menu and category.parent_id == menu.id:
#                 item_type = "subcategory"
#             elif category.parent_is_menu and category.parent_id == 0:
#                 item_type = "category"
#             else:
#                 item_type = "subcategory"

#             category_data = {
#                 "id": str(category.id),
#                 "title": category.title,
#                 "type": item_type,
#                 "children": [],
#                 "active": True,
#             }
#             category_dict[category.id] = category_data

#         for category in all_categories:
#             category_data = category_dict[category.id]

#             foods = (
#                 db.query(models.Foods)
#                 .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
#                 .filter(
#                     models.MenuIDS.menu_id == menu.id,
#                     models.MenuIDS.cat_id == category.id,
#                 )
#                 .order_by(models.Foods.position.asc())
#                 .all()
#             )

#             for food in foods:
#                 food_data = {
#                     "id": str(food.id),
#                     "title": (
#                         food.title if hasattr(food, "title") else f"Food {food.id}"
#                     ),
#                     "type": "food",
#                     "children": [],
#                     "active": True,
#                 }
#                 category_data["children"].append(food_data)

#             if not category.parent_is_menu and category.parent_id in category_dict:
#                 category_dict[category.parent_id]["children"].append(category_data)
#             elif category.parent_is_menu:
#                 menu_data["children"].append(category_data)
#             elif not category.parent_is_menu and category.parent_id == menu.id:
#                 menu_data["children"].append(category_data)

#         menu_response.append(menu_data)

#     return menu_response


# Helper function to build nested category structure
def build_nested_categories(categories, db: Session, menu_id: int):
    # Map of category IDs to their raw dictionary data
    category_map = {cat.id: cat.__dict__.copy() for cat in categories}
    nested = []

    for category in categories:
        # Identify top-level categories (directly under menu)
        if (
            category.parent_id == 0 or category.parent_id == menu_id
        ) and category.parent_is_menu:
            category_data = category_map[category.id]
            category_data["children"] = []
            category_data["foods"] = []

            # Fetch foods for this category
            foods = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == menu_id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )
            category_data["foods"] = [food.__dict__ for food in foods]

            # Recursively add all subcategories
            subcategories = [cat for cat in categories if cat.parent_id == category.id]
            if subcategories:
                subcategory_data = build_nested_categories(subcategories, db, menu_id)
                category_data["children"].extend(subcategory_data)

            # Include raw food dictionaries in children
            category_data["children"].extend(category_data["foods"])

            nested.append(category_data)

    return nested


@router.get("/get_foods")
async def get_all_foods_menu(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    final_res = []
    if not user:
        raise get_user_exception()
    else:
        menu = (
            db.query(models.Menu)
            .filter(
                models.Menu.store_id == user.get("id"), models.Menu.is_primary == True
            )
            .order_by(models.Menu.position.asc())
            .first()
        )
        if not menu:
            raise HTTPException(status_code=404, detail="Menu not found")

        categories = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.menu_id == menu.id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        if menu.multi_language_data:
            menu.multi_language_data = json.loads(menu.multi_language_data)
        menu.category = categories
        for category in categories:
            food = (
                db.query(models.Foods)
                .filter(models.Foods.available == 1, models.Foods.enabled == True)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == menu.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )
            if category.multi_language_data:
                category.multi_language_data = json.loads(category.multi_language_data)
            for foo in food:
                if foo.multi_language_data:
                    foo.multi_language_data = json.loads(foo.multi_language_data)
            category.foods = food

        return {"menu": menu}


@router.get("/v2/get_foods")
async def get_all_foods_menu_version2(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user:
        raise get_user_exception()

    menu = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"), models.Menu.is_primary == True)
        .order_by(models.Menu.position.asc())
        .first()
    )

    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    categories = (
        db.query(models.FoodCategory)
        .filter(models.FoodCategory.menu_id == menu.id)
        .order_by(models.FoodCategory.position.asc())
        .all()
    )

    if menu.multi_language_data:
        menu.multi_language_data = json.loads(menu.multi_language_data)

    menu.category = categories

    for category in categories:
        foods = (
            db.query(models.Foods)
            .filter(models.Foods.available == 1, models.Foods.enabled == True)
            .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
            .filter(
                models.MenuIDS.menu_id == menu.id, models.MenuIDS.cat_id == category.id
            )
            .order_by(models.Foods.position.asc())
            .all()
        )

        if category.multi_language_data:
            category.multi_language_data = json.loads(category.multi_language_data)

        for food in foods:
            if food.multi_language_data:
                food.multi_language_data = json.loads(food.multi_language_data)

            # Handle foods with sizes
            if food.sizes and isinstance(food.sizes, (str, list, dict)):
                sizes = (
                    json.loads(food.sizes)
                    if isinstance(food.sizes, str)
                    else food.sizes
                )
                if sizes:  # Only process if sizes is not empty
                    # Add ID to each size using food ID and letter
                    for idx, size in enumerate(sizes):
                        size["id"] = f"{food.id}-{string.ascii_lowercase[idx]}"
                    food.sizes = sizes

        category.foods = foods

    return {"menu": menu}


def find_template_file(menu_folder_name: str, template_name: str) -> str:
    """
    Find template file with fallback logic.
    First tries to find the template in the repository path,
    then falls back to the menu folder if not found.

    Special handling for Atlas and Sayeh templates - they use smart_template.html
    """
    import os
    from pathlib import Path

    # Special handling for Atlas and Sayeh templates
    if template_name.lower() in ["atlas", "sayeh"]:
        # For Atlas and Sayeh, use smart_template.html instead
        actual_template_name = "smart_template"
    else:
        actual_template_name = template_name.lower()

    # First, try to find the template in the repository path
    repository_template_path = Path(
        f"../../{menu_folder_name}/{actual_template_name}.html"
    )

    # If the repository template exists, use it
    if repository_template_path.exists():
        return str(repository_template_path)

    # If not found in repository, fall back to the menu folder
    menu_folder_template_path = Path(
        f"../{menu_folder_name}/{actual_template_name}.html"
    )

    # Check if the fallback template exists
    if menu_folder_template_path.exists():
        return str(menu_folder_template_path)

    raise FileNotFoundError(
        f"Template file '{actual_template_name}.html' not found in repository at: {repository_template_path} "
        f"or in menu folder at: {menu_folder_template_path}"
        f"{' (Atlas/Sayeh templates use smart_template.html)' if template_name.lower() in ['atlas', 'sayeh'] else ''}"
    )


@router.post("/publish_menu/{menu_id}")
async def publish_a_menu(
    menu_id: int,
    theme: Optional[PublishMenu] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Publish a menu with template rendering.
    
    This function has been updated to work with the refactored models:
    - Uses relational tables instead of JSON fields for multi-language data
    - Uses selectinload for efficient data loading
    - Supports the new FoodLanguage, FoodSize, and FoodCategoryTranslation models
    """
    if not user:
        raise get_user_exception()
    all_menus_primary = (
        db.query(models.Menu)
        .filter(
            models.Menu.store_id == user.get("id"), models.Menu.is_sub_shop == False
        )
        .all()
    )
    store_data = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    real_store_data = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    all_menus = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"))
        .filter(models.Menu.id == menu_id)
        .first()
    )
    selected_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    print("Selected Menu:", selected_menu)

    file_name = ""
    menu_folder_name = os.getenv("MENU_FOLDER_NAME")
    if selected_menu.is_sub_shop:
        shop_info = (
            db.query(models.Shops)
            .filter(models.Shops.id == selected_menu.shop_id)
            .first()
        )
        store_data = shop_info
        all_menus = (
            db.query(models.Menu)
            .filter(models.Menu.shop_id == shop_info.id)
            .filter(models.Menu.id == menu_id)
            .first()
        )
        all_menus_primary = (
            db.query(models.Menu).filter(models.Menu.shop_id == shop_info.id).all()
        )
        if shop_info.default_url is not None:
            if "https://" in shop_info.default_url:
                file_name = shop_info.default_url.split("/")[-1]
                menu_folder_name = shop_info.default_url.split("/")[-2]

            else:
                file_name = shop_info.default_url
        else:
            file_name = members.generate_random_value(7)
            shop_info.default_url = file_name
            db.add(shop_info)
            db.commit()

    else:
        if store_data.default_url is not None:
            if "https://" in store_data.default_url:
                file_name = store_data.default_url.split("/")[-1]
                menu_folder_name = store_data.default_url.split("/")[-2]

            else:
                file_name = store_data.default_url
        else:
            file_name = members.generate_random_value(7)
            store_data.default_url = file_name
            db.add(store_data)
            db.commit()
    menu_name = ""
    if selected_menu is not None:
        menu_name = selected_menu.title
        tmp_name = selected_menu.template_name
        if tmp_name == None or tmp_name == "":
            tmp_name = "custom"

        # Handle custom templates (e.g., shiraz_custom)
        base_template_name = tmp_name
        if "custom" in tmp_name and "_custom" in tmp_name:
            # Extract base template name (e.g., "shiraz" from "shiraz_custom")
            base_template_name = tmp_name.split("_custom")[0]
            print(
                f"Custom template detected: {tmp_name}, using base template: {base_template_name}"
            )

        # type 1
        categoryObj = []
        foodObject = []
        categories = (
            db.query(models.FoodCategory)
            .options(
                selectinload(models.FoodCategory.translations)
            )
            .filter(models.FoodCategory.parent_id != 0)
            .filter(models.FoodCategory.enabled == True)
            .filter(models.FoodCategory.menu_id == menu_id)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(
                models.FoodCategory.parent_id.asc(), models.FoodCategory.position.asc()
            )
            .all()
        )
        print("Retrieved Categories:", categories)
        print("Number of Categories:", len(categories))
        parent_cats = (
            db.query(models.FoodCategory)
            .options(
                selectinload(models.FoodCategory.translations)
            )
            .filter(models.FoodCategory.parent_id == 0)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        print("Parent Categories:", parent_cats)

        all_menus.categories = categories
        saahel_subs = []
        for index, category in enumerate(categories):
            food = (
                db.query(models.Foods)
                .options(
                    selectinload(models.Foods.translations),
                    selectinload(models.Foods.size_items).selectinload(models.FoodSize.translations)
                )
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == all_menus.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )
            
            # Process food items to add sizes with IDs for templates that need them
            for food_item in food:
                if food_item.size_items:
                    # Add ID to each size using food ID and letter (for backward compatibility)
                    for idx, size_item in enumerate(food_item.size_items):
                        if not hasattr(size_item, 'id') or not size_item.id:
                            size_item.id = f"{food_item.id}-{string.ascii_lowercase[idx]}"
            print(
                f"Foods for category id={category.id} title='{category.title}': {food}"
            )
            if category.enabled > 0:
                if "Dalia" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Dalia_v2" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Shabnam" in base_template_name:
                    if category.parent_id != 0:
                        if category.parent_id != menu_id:
                            head_cat = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == category.parent_id)
                                .first()
                            )
                            categoryObj.append(
                                {
                                    "category": category.title,
                                    "id": category.id,
                                    "parent_id": category.parent_id,
                                    "position": category.position,
                                    "parent_id_position": head_cat.position,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                        else:
                            all_heads = (
                                db.query(models.FoodCategory)
                                .filter(
                                    models.FoodCategory.parent_id == 0,
                                    models.FoodCategory.menu_id == menu_id,
                                )
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            if len(all_heads) > 0:
                                categoryObj.append(
                                    {
                                        "category": category.title,
                                        "id": category.id,
                                        "parent_id": category.parent_id,
                                        "position": category.position,
                                        "parent_id_position": all_heads[-1].position
                                        + 1,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            else:
                                categoryObj.append(
                                    {
                                        "category": category.title,
                                        "id": category.id,
                                        "parent_id": category.parent_id,
                                        "position": category.position,
                                        "parent_id_position": 0,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                elif "Sorme" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            for item in subs:
                                all_sub.append(item.title)
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "subCategory": all_sub,
                                    "parent_id": pr.parent_id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    if category.parent_is_menu:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(
                                models.FoodCategory.parent_id == category.id,
                                models.FoodCategory.menu_id != category.id,
                            )
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        all_sub = []
                        for item in subs:
                            all_sub.append(item.title)
                        categoryObj.append(
                            {
                                "category": category.title,
                                "id": category.id,
                                "subCategory": all_sub,
                                "parent_id": category.parent_id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Yakh" in base_template_name:
                    if category.parent_id != 0:
                        titles = {"fa": category.title}
                        if (
                            hasattr(category, "multi_language_data")
                            and category.multi_language_data
                        ):
                            try:
                                lang_data = json.loads(category.multi_language_data)
                                additional_titles = {
                                    item["language_id"]: item["title"]
                                    for item in lang_data
                                    if item.get("language_id") != "fa"
                                }
                                titles.update(additional_titles)
                            except json.JSONDecodeError:
                                titles = {}
                        categoryObj.append(
                            {
                                "category": titles,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "shiraz" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(
                                    models.FoodCategory.parent_id == pr.id,
                                    models.FoodCategory.store_id == user.get("id"),
                                )
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            for val in subs:
                                cat_ig = val.cat_image
                                if len(cat_ig) == 0:
                                    cat_ig = f'{os.getenv("BASE_URL")}/images/defaults/CatIcon.svg'
                                else:
                                    if "https://" in val.cat_image:
                                        cat_ig = val.cat_image
                                    else:
                                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": pr.title,
                                        "subCategory": val.title,
                                        "icon": cat_ig,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    if subcats:
                        for val in subcats:
                            cat_ig = val.cat_image
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in val.cat_image:
                                    cat_ig = val.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": category.title,
                                    "subCategory": val.title,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    else:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        saahel_subs.append(
                            {
                                "id": category.id,
                                "category": category.title,
                                "subCategory": category.title,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                    # if category.parent_is_menu:
                    if category.parent_is_menu == True:
                        categoryObj.append(
                            {
                                "category": category.title,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "custom" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "parent_is_menu": pr.parent_is_menu,
                                    "parent_id": pr.parent_id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    categoryObj.append(
                        {
                            "category": category.title,
                            "id": category.id,
                            "parent_id": category.parent_id,
                            "parent_is_menu": category.parent_is_menu,
                            **(
                                {"status": category.enabled}
                                if real_store_data.access_type == 3
                                and not category.parent_is_menu
                                else (
                                    {"status": 1}
                                    if real_store_data.access_type == 3
                                    and category.parent_is_menu
                                    else {}
                                )
                            ),
                        }
                    )
                elif "zomorod" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Zomorod" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "gerdoo" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "sepehr" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            find_foods = (
                                db.query(models.Foods)
                                .filter(models.Foods.cat_id == pr.id)
                                .all()
                            )
                            for item in subs:
                                all_sub.append(item.title)
                            if len(all_sub) > 0 or len(find_foods) > 0:
                                titles = {"fa": pr.title}
                                if (
                                    hasattr(pr, "multi_language_data")
                                    and pr.multi_language_data
                                ):
                                    try:
                                        lang_data = json.loads(pr.multi_language_data)
                                        additional_titles = {
                                            item["language_id"]: item["title"]
                                            for item in lang_data
                                            if item.get("language_id") != "fa"
                                        }
                                        titles.update(additional_titles)
                                    except json.JSONDecodeError:
                                        titles = {}
                                categoryObj.append(
                                    {
                                        "category": titles,
                                        "id": pr.id,
                                        "parent_id": pr.parent_id,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )

                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    if subcats:
                        for val in subcats:
                            cat_ig = val.cat_image
                            if category.parent_id == menu_id:
                                cat_val = "سایر"
                                catid = 1
                                sub_val = category.title
                            else:
                                main_cat = (
                                    db.query(models.FoodCategory)
                                    .filter(
                                        models.FoodCategory.id == category.parent_id
                                    )
                                    .first()
                                )
                                cat_val = main_cat.title
                                catid = main_cat.id
                                sub_val = category.title
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in val.cat_image:
                                    cat_ig = val.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                            titles = {"fa": category.title}
                            if (
                                hasattr(category, "multi_language_data")
                                and category.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(category.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                except json.JSONDecodeError:
                                    titles = {}
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": cat_val,
                                    "catid": catid,
                                    "subCategory": titles,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    else:
                        cat_ig = category.cat_image
                        if category.parent_id == menu_id:
                            cat_val = "سایر"
                            catid = 1
                            sub_val = category.title
                        else:
                            main_cat = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == category.parent_id)
                                .first()
                            )
                            cat_val = main_cat.title
                            catid = main_cat.id
                            sub_val = category.title
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        titles = {"fa": category.title}
                        if (
                            hasattr(category, "multi_language_data")
                            and category.multi_language_data
                        ):
                            try:
                                lang_data = json.loads(category.multi_language_data)
                                additional_titles = {
                                    item["language_id"]: item["title"]
                                    for item in lang_data
                                    if item.get("language_id") != "fa"
                                }
                                titles.update(additional_titles)
                            except json.JSONDecodeError:
                                titles = {}
                        saahel_subs.append(
                            {
                                "id": category.id,
                                "category": cat_val,
                                "catid": catid,
                                "subCategory": titles,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                    if category.parent_is_menu:
                        if category.parent_id == menu_id:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(
                                    models.FoodCategory.parent_id == menu_id,
                                    models.FoodCategory.menu_id != category.id,
                                )
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            for item in subs:
                                if item.title not in all_sub:
                                    all_sub.append(item.title)
                            if len(all_sub) > 0:

                                resObj = {
                                    "category": "سایر",
                                    "id": 1,
                                    "parent_id": 0,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                                if resObj not in categoryObj:
                                    categoryObj.append(resObj)

                elif "cookie" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "text": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "ivaan" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            for item in subs:
                                all_sub.append(item.title)
                            if len(all_sub) > 0:
                                titles_sub = {"fa": pr.title}
                                if pr.multi_language_data:
                                    lang_data = json.loads(pr.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles_sub.update(additional_titles)

                            titles = {"fa": pr.title}
                            if pr.multi_language_data:
                                try:
                                    lang_data = json.loads(pr.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    categoryObj.append(
                                        {
                                            "category": titles,
                                            "id": pr.id,
                                            **(
                                                {"status": category.enabled}
                                                if real_store_data.access_type == 3
                                                and not category.parent_is_menu
                                                else (
                                                    {"status": 1}
                                                    if real_store_data.access_type == 3
                                                    and category.parent_is_menu
                                                    else {}
                                                )
                                            ),
                                        }
                                    )
                                except json.JSONDecodeError:
                                    titles = {}
                            else:
                                categoryObj.append(
                                    {
                                        "category": titles,
                                        "id": pr.id,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )

                    for new_sub in parent_cats:
                        subcats = (
                            db.query(models.FoodCategory)
                            .filter(
                                models.FoodCategory.parent_id == new_sub.id,
                                models.FoodCategory.menu_id != new_sub.id,
                            )
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        for val in subcats:
                            titles = {"fa": val.title}
                            if val.multi_language_data:
                                try:
                                    lang_data = json.loads(val.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                except json.JSONDecodeError:
                                    titles = {}
                            if len(saahel_subs) > 0:
                                if any(obj.get("id") != val.id for obj in saahel_subs):
                                    saahel_subs.append(
                                        {
                                            "id": val.id,
                                            "category": new_sub.title,
                                            "catid": new_sub.id,
                                            "subCategory": titles,
                                            **(
                                                {"status": new_sub.enabled}
                                                if real_store_data.access_type == 3
                                                and not new_sub.parent_is_menu
                                                else (
                                                    {"status": 1}
                                                    if real_store_data.access_type == 3
                                                    and new_sub.parent_is_menu
                                                    else {}
                                                )
                                            ),
                                        }
                                    )
                            else:
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": new_sub.title,
                                        "catid": new_sub.id,
                                        "subCategory": titles,
                                        **(
                                            {"status": new_sub.enabled}
                                            if real_store_data.access_type == 3
                                            and not new_sub.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and new_sub.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    all_sub = []
                    for val in subcats:
                        all_sub.append(val.title)

                    category.subCategory = all_sub
                    if category.parent_is_menu:
                        titles = {"fa": category.title}
                        if len(all_sub) > 0:
                            titles_sub = {"fa": pr.title}
                            lang_data = json.loads(pr.multi_language_data)
                            additional_titles = {
                                item["language_id"]: item["title"]
                                for item in lang_data
                                if item.get("language_id") != "fa"
                            }
                            titles_sub.update(additional_titles)
                        if (
                            hasattr(category, "multi_language_data")
                            and category.multi_language_data
                        ):
                            try:
                                lang_data = json.loads(category.multi_language_data)
                                additional_titles = {
                                    item["language_id"]: item["title"]
                                    for item in lang_data
                                    if item.get("language_id") != "fa"
                                }
                                titles.update(additional_titles)
                                categoryObj.append(
                                    {
                                        "category": titles,
                                        "id": category.id,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            except json.JSONDecodeError:
                                titles = {}
                        else:
                            categoryObj.append(
                                {
                                    "category": {"fa": category.title},
                                    "id": category.id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )

                elif "saahel" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            for val in subs:
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": pr.title,
                                        "subCategory": val.title,
                                        "icon": val.cat_image,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            cat_ig = pr.cat_image
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in pr.cat_image:
                                    cat_ig = pr.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{pr.cat_image}'
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "parent_is_menu": val.parent_is_menu,
                                    "parent_id": pr.parent_id,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    for val in subcats:
                        saahel_subs.append(
                            {
                                "id": val.id,
                                "category": category.title,
                                "subCategory": val.title,
                                "icon": val.cat_image,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                    # if category.parent_is_menu:
                    if category.parent_is_menu == True:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "id": category.id,
                                "parent_id": category.parent_id,
                                "parent_is_menu": category.parent_is_menu,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "ghahve" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:

                            subs = (
                                db.query(models.FoodCategory)
                                .filter(
                                    models.FoodCategory.parent_id == pr.id,
                                    models.FoodCategory.menu_id == menu_id,
                                )
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            for val in subs:
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": pr.title,
                                        "subCategory": val.title,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            cat_ig = pr.cat_image
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in pr.cat_image:
                                    cat_ig = pr.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{pr.cat_image}'
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            and_(
                                models.FoodCategory.parent_id == category.id,
                                models.FoodCategory.menu_id != category.id,
                            )
                        )
                        .all()
                    )
                    for val in subcats:
                        if val.menu_id != category.id:
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": category.title,
                                    "subCategory": val.title,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    if category.parent_is_menu:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

        # type2
        categories = (
            db.query(models.FoodCategory)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        all_menus.categories = categories
        for category in categories:
            if category.enabled > 0:
                food = (
                    db.query(models.Foods)
                    .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                    .filter(
                        models.MenuIDS.menu_id == all_menus.id,
                        models.MenuIDS.cat_id == category.id,
                    )
                    .order_by(models.Foods.position.asc())
                    .all()
                )

                category.text = category.title
                category.icon = category.cat_image
                subcats = (
                    db.query(models.FoodCategory)
                    .filter(
                        models.FoodCategory.parent_id == category.id,
                        models.FoodCategory.menu_id != category.id,
                    )
                    .all()
                )
                for foodObj in food:
                    if foodObj.available > 0:
                        all_img = []
                        for food in foodObj.food_image:
                            all_img.append(
                                f'{os.getenv("BASE_URL")}/food/images/{food}'
                            )
                        if len(all_img) == 0:
                            if (
                                store_data.brand_logo != None
                                and len(store_data.brand_logo) > 0
                            ):
                                all_img.append(
                                    f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                                )
                            else:
                                all_img.append(
                                    f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                                )
                        video_url = ""
                        if foodObj.food_video != None and len(foodObj.food_video) > 0:
                            video_url = f'{os.getenv("BASE_URL")}/food/videos/{foodObj.food_video}'
                        if "custom" in base_template_name:
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "category": category.title,
                                "images": all_img,
                                "details": foodObj.description,
                                "price": foodObj.price,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available

                            foodObject.append(food_dict)
                        elif "Dalia" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "category": category.title,
                                "images": all_img,
                                "details": foodObj.description,
                                "price": final_price,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "Dalia_v2" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "category": category.title,
                                "images": all_img,
                                "details": foodObj.description,
                                "price": final_price,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "Shabnam" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "price": final_price,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "Sorme" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "price": final_price,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                                "subCategoryFood": cat_name.title,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)

                        elif "Yakh" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            titles = {"fa": foodObj.title}
                            prces = {"fa": foodObj.price}
                            descs = {"fa": foodObj.description}
                            cat_multii = {"fa": category.title}
                            cat_id = category.id
                            if (
                                hasattr(foodObj, "multi_language_data")
                                and foodObj.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(
                                        str(foodObj.multi_language_data)
                                    )
                                    add_prices = {
                                        item["language_id"]: item["price"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    add_desc = {
                                        item["language_id"]: item["description"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    prces.update(add_prices)
                                    descs.update(add_desc)
                                except json.JSONDecodeError:
                                    titles = {}
                                    prces = {}
                                    descs = {}
                                if (
                                    hasattr(category, "multi_language_data")
                                    and category.multi_language_data
                                ):
                                    cat_lang_data = json.loads(
                                        category.multi_language_data
                                    )
                                    try:
                                        cat_multi = {
                                            item["language_id"]: item["title"]
                                            for item in cat_lang_data
                                            if item.get("language_id") != "fa"
                                        }
                                        cat_multii.update(cat_multi)
                                    except json.JSONDecodeError:
                                        cat_multii = {}
                            food_dict = {
                                "id": foodObj.id,
                                "title": titles,
                                "englishTitle": foodObj.englishTitle,
                                "price": prces,
                                "category": cat_multii,
                                "images": all_img,
                                "category_id": cat_id,
                                "details": descs,
                                "videoUrl": video_url,
                            }

                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "zomorod" in base_template_name:
                            food_image = ""
                            if len(foodObj.food_image) > 0:
                                food_image = f'{os.getenv("BASE_URL")}/food/images/{foodObj.food_image[0]}'
                            elif (
                                store_data.brand_logo != None
                                and len(store_data.brand_logo) > 0
                            ):
                                food_image = f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'

                            else:
                                food_image = f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                            if foodObj.sizes is not None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available

                                    food_dict = {
                                        "id": foodObj.id,
                                        "name": foodObj.title,
                                        "sizes": foodObj.sizes,
                                        "category": category.title,
                                        "image": food_image,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                    }
                                    if real_store_data.access_type == 3:
                                        food_dict["status"] = foodObj.available
                                    foodObject.append(food_dict)
                                else:
                                    food_dict = {
                                        "id": foodObj.id,
                                        "name": foodObj.title,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "category": category.title,
                                        "image": food_image,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                    }
                                    if real_store_data.access_type == 3:
                                        food_dict["status"] = foodObj.available
                                    foodObject.append(food_dict)
                            else:
                                food_dict = {
                                    "id": foodObj.id,
                                    "name": foodObj.title,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "category": category.title,
                                    "image": food_image,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                                if real_store_data.access_type == 3:
                                    food_dict["status"] = foodObj.available
                                foodObject.append(food_dict)
                        elif "ivaan" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            titles = {"fa": foodObj.title}
                            prces = {"fa": foodObj.price}
                            descs = {"fa": foodObj.description}
                            if (
                                hasattr(foodObj, "multi_language_data")
                                and foodObj.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(
                                        str(foodObj.multi_language_data)
                                    )
                                    add_prices = {
                                        item["language_id"]: item["price"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    add_desc = {
                                        item["language_id"]: item["description"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    prces.update(add_prices)
                                    descs.update(add_desc)
                                except json.JSONDecodeError:
                                    titles = {}
                                    prces = {}
                                    descs = {}
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                        find_datas = it.get("size")
                                        if (
                                            hasattr(foodObj, "multi_language_data")
                                            and foodObj.multi_language_data
                                            and store_data.multi_language_currency
                                        ):
                                            multi = ast.literal_eval(
                                                str(foodObj.multi_language_data)
                                            )
                                            new_titles = {}
                                            new_prices = {}

                                            for item in multi:
                                                if (
                                                    item.get("sizes")
                                                    and len(item.get("sizes")) > 0
                                                ):
                                                    for in_size in item.get("sizes"):
                                                        if (
                                                            in_size.get("size")
                                                            == find_datas
                                                        ):
                                                            new_titles[
                                                                item.get("language_id")
                                                            ] = in_size.get("title")
                                                            new_prices[
                                                                item.get("language_id")
                                                            ] = str(
                                                                in_size.get("price")
                                                            )
                                                else:
                                                    new_titles[
                                                        item.get("language_id")
                                                    ] = ""
                                                    new_prices[
                                                        item.get("language_id")
                                                    ] = "0.0"
                                            it["title"] = new_titles
                                            it["price"] = new_prices

                                        else:
                                            if find_datas:
                                                it["title"] = {"fa": it.get("title")}
                                                it["price"] = {"fa": it.get("price")}
                                            else:
                                                it["title"] = {"fa": None}
                                                it["price"] = {"fa": None}

                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": titles,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory_id": cat_name.id,
                                            "category_id": category.id,
                                            "images": all_img,
                                            "description": descs,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )

                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": titles,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": prces,
                                            "sizes": None,
                                            "subCategory_id": cat_name.id,
                                            "category_id": category.id,
                                            "images": all_img,
                                            "description": descs,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )

                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": titles,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": prces,
                                        "sizes": None,
                                        "subCategory_id": cat_name.id,
                                        "category_id": category.id,
                                        "images": all_img,
                                        "description": descs,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )

                        elif "ghahve" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "subCategory": cat_name.title,
                                            "sizes": None,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "subCategory": cat_name.title,
                                        "sizes": None,
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "shiraz" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "subCategory": cat_name.title,
                                            "sizes": [],
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "subCategory": cat_name.title,
                                        "sizes": [],
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "gerdoo" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "sizes": None,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "subCategory": cat_name.title,
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "sepehr" in base_template_name:
                            englishTitle = foodObj.englishTitle
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.englishTitle == None:
                                englishTitle = ""
                            if category.parent_id == menu_id:
                                cat_val = "سایر"
                                cat_id = 1
                                sub_id = cat_name.id
                                sub_val = cat_name.title
                            else:
                                main_cat = (
                                    db.query(models.FoodCategory)
                                    .filter(
                                        models.FoodCategory.id == cat_name.parent_id
                                    )
                                    .first()
                                )
                                cat_val = main_cat.title
                                sub_val = cat_name.title
                                cat_id = main_cat.id
                                sub_id = cat_name.id
                            titles = {"fa": foodObj.title}
                            prces = {"fa": foodObj.price}
                            descs = {"fa": foodObj.description}
                            if (
                                hasattr(foodObj, "multi_language_data")
                                and foodObj.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(
                                        str(foodObj.multi_language_data)
                                    )
                                    add_prices = {
                                        item["language_id"]: item["price"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    add_desc = {
                                        item["language_id"]: item["description"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    prces.update(add_prices)
                                    descs.update(add_desc)
                                except json.JSONDecodeError:
                                    titles = {}
                                    prces = {}
                                    descs = {}
                            if foodObj.sizes != None:

                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for new_item in foodObj.sizes:
                                        find_datas = new_item.get("size")

                                        if (
                                            hasattr(foodObj, "multi_language_data")
                                            and foodObj.multi_language_data
                                        ):
                                            multi = json.loads(
                                                str(foodObj.multi_language_data)
                                            )
                                            new_titles = {}
                                            new_prices = {}

                                            for item in multi:
                                                if (
                                                    item.get("sizes")
                                                    and len(item.get("sizes")) > 0
                                                ):
                                                    for in_size in item.get("sizes"):

                                                        if (
                                                            in_size.get("size")
                                                            == find_datas
                                                        ):
                                                            new_titles[
                                                                item.get("language_id")
                                                            ] = in_size.get("title")
                                                            new_prices[
                                                                item.get("language_id")
                                                            ] = str(
                                                                in_size.get("price")
                                                            )
                                                else:
                                                    new_titles[
                                                        item.get("language_id")
                                                    ] = ""
                                                    new_prices[
                                                        item.get("language_id")
                                                    ] = "0.0"
                                            new_item["title"] = new_titles
                                            new_item["price"] = new_prices
                                        else:
                                            if find_datas:
                                                new_item["title"] = {
                                                    "fa": new_item.get("title")
                                                }
                                                new_item["price"] = {
                                                    "fa": new_item.get("price")
                                                }
                                            else:
                                                new_item["title"] = {"fa": None}
                                                new_item["price"] = {"fa": None}

                                        foodObject.append(
                                            {
                                                "id": foodObj.id,
                                                "title": titles,
                                                "englishTitle": englishTitle,
                                                "sizes": foodObj.sizes,
                                                "category_id": cat_id,
                                                "subCategory_id": sub_id,
                                                "images": all_img,
                                                "description": descs,
                                                "videoUrl": video_url,
                                                **(
                                                    {"status": foodObj.available}
                                                    if real_store_data.access_type == 3
                                                    else {}
                                                ),
                                            }
                                        )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": titles,
                                            "englishTitle": englishTitle,
                                            "MainPrice": prces,
                                            "sizes": None,
                                            "category_id": cat_id,
                                            "subCategory_id": sub_id,
                                            "images": all_img,
                                            "description": descs,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": titles,
                                        "englishTitle": englishTitle,
                                        "MainPrice": prces,
                                        "sizes": None,
                                        "category_id": cat_id,
                                        "subCategory_id": sub_id,
                                        "images": all_img,
                                        "description": descs,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "cookie" in base_template_name:
                            popup = None
                            all_imgs = None
                            if len(all_img) > 0:
                                all_imgs = all_img[0]
                                if len(all_img) > 1:
                                    popup = all_img[1]
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "category": category.title,
                                            "image": all_imgs,
                                            "popupBackground": popup,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "sizes": None,
                                            "category": category.title,
                                            "image": all_imgs,
                                            "popupBackground": popup,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "category": category.title,
                                        "image": all_imgs,
                                        "popupBackground": popup,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "saahel" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "MainPrice": foodObj.price,
                                            "sizes": None,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "subCategory": cat_name.title,
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )

    else:
        raise HTTPException(
            status_code=403, detail="You should select a template from the list"
        )
    if "Shabnam" in base_template_name:
        categoryObj.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )
    elif "ivaan" in base_template_name:
        categoryObj.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )
        saahel_subs.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )
    store_info = []
    find_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    menu_description = {"fa": find_menu.description}

    if hasattr(find_menu, "multi_language_data") and find_menu.multi_language_data:
        for lang_data in json.loads(find_menu.multi_language_data):
            if lang_data.get("language_id") != "fa":
                menu_description[lang_data.get("language_id")] = lang_data.get(
                    "description"
                )

    if selected_menu.is_sub_shop:
        store = (
            db.query(models.Members).filter(models.Members.id == user.get("id")).first()
        )

        store_info.append(
            {
                "store_id": store.id,
                "shop_id": store_data.id,
                "online_access": store.online_order,
                "menu_id": menu_id,
                "is_restaurant": bool(getattr(store_data, "IsShop", 0)),
                "multiLanguage": shop_info.multi_language_currency,
                "currencies": (
                    (
                        {
                            item["language"]: item["currency"]
                            for item in (
                                store_data.language_currencies
                                if isinstance(store_data.language_currencies, list)
                                else json.loads(store_data.language_currencies)
                            )
                            if isinstance(item, dict)
                            and "language" in item
                            and "currency" in item
                        }
                    )
                    if store_data.multi_language_currency
                    and store_data.language_currencies
                    else None
                ),
                "callorder": store.call_order,
                "payment_gateway": store.payment_gateway,
                "payment_methods": store.payment_methods,
                "city": store.city,
                "address": store_data.address,
            }
        )

    else:
        store_info.append(
            {
                "store_id": store_data.id,
                "shop_id": None,
                "online_access": store_data.online_order,
                "menu_id": menu_id,
                "is_restaurant": bool(getattr(store_data, "IsShop", 0)),
                "multiLanguage": store_data.multi_language_currency,
                "currencies": (
                    (
                        {
                            item["language"]: item["currency"]
                            for item in (
                                store_data.language_currencies
                                if isinstance(store_data.language_currencies, list)
                                else json.loads(store_data.language_currencies)
                            )
                            if isinstance(item, dict)
                            and "language" in item
                            and "currency" in item
                        }
                    )
                    if store_data.multi_language_currency
                    and store_data.language_currencies
                    else None
                ),
                "callorder": store_data.call_order,
                "payment_gateway": store_data.payment_gateway,
                "payment_methods": store_data.payment_methods,
                "city": store_data.city,
                "address": store_data.address,
            }
        )

    if "sepehr" in base_template_name:
        foodObject = list({obj["id"]: obj for obj in foodObject}.values())

    json_object = json.dumps(categoryObj, indent=4, ensure_ascii=False)
    food_object = json.dumps(foodObject, indent=4, ensure_ascii=False)
    shop_object = json.dumps(store_info, indent=4, ensure_ascii=False)
    desc_object = json.dumps(menu_description, indent=4, ensure_ascii=False)
    # # Writing to js file
    if "saahel" in base_template_name:
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods,subCategories,store_info};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "sepehr" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + f"const menu_description={desc_object}\n"
                f'const background="{backg}"\n'
                + "export {"
                + "categories,foods,subCategories,background,store_info,menu_description};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "ghahve" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                + f'const background="{backg}"\n'
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods,subCategories , background,store_info};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "shiraz" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            if theme is not None and (
                theme.backgroundColor or theme.secondColor is not None
            ):
                back_obj = json.dumps(
                    {
                        "bodyColor": theme.backgroundColor,
                        "secondaryColor": theme.secondColor,
                    },
                    indent=4,
                    ensure_ascii=False,
                )
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                    + f'const background="{backg}"\n'
                    + f"const theme = {back_obj}\n"
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme, store_info};"
                )
            else:
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                                const foods={food_object}\n"
                    + f'const background="{backg}"\n const theme = null;\n'
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme,store_info};"
                )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "gerdoo" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            if theme is not None and (
                theme.backgroundColor or theme.secondColor is not None
            ):
                back_obj = json.dumps(
                    {
                        "bodyColor": theme.backgroundColor,
                        "secondaryColor": theme.secondColor,
                    },
                    indent=4,
                    ensure_ascii=False,
                )
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                    + f'const background="{backg}"\n'
                    + f"const theme = {back_obj}\n"
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme, store_info};"
                )
            else:
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                                const foods={food_object}\n"
                    + f'const background="{backg}"\n const theme = null;\n'
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme,store_info};"
                )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "ivaan" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        saahel_subs = list({item["id"]: item for item in saahel_subs}.values())
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n "
                + f"const subCategories={saahel_subs}\n"
                + f"const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + f"const menu_description={desc_object}\n"
                f'const background="{backg}"\n'
                + "export {"
                + "categories,foods,background,store_info,subCategories,menu_description};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)

    elif "Shabnam" in base_template_name:
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods , store_info};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    else:

        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const foods={food_object}\n"
                + f"const menu_description={desc_object}\n"
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods,store_info,menu_description};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)

    # with open(f"../{menu_folder_name}/{tmp_name.lower()}.html") as html_file:
    template_path = find_template_file(menu_folder_name, base_template_name)
    with open(template_path) as html_file:
        soup = BeautifulSoup(html_file.read(), features="html.parser")
        # if 'Dalia' in tmp_name:
        for tag in soup.find_all(id="change-data"):
            if tag is not None:
                tag.string.replace_with(str(random.randint(10, 99)))

        for tag in soup.find(id="menu_name"):
            tag.string.replace_with(menu_name)
        for tag in soup.find_all(id="restaurant_title"):
            if tag is not None:
                tag.string = store_data.brand_name

        for tag in soup.find_all(id="food_desc"):
            if tag is not None:
                tag.string = selected_menu.description

        for tag in soup.find_all(id="desc"):
            if tag is not None:
                tag.string = selected_menu.description

        for tag in soup.find_all(id="res_logo"):
            if tag is not None:
                if store_data.brand_logo is not None and store_data.brand_logo != "":
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                    )
                else:
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                    )

        for tag in soup.find_all(id="map"):
            if tag is not None:
                if store_data.location_url != None:
                    if "https" not in store_data.location_url:
                        tag["href"] = (
                            f"https://www.google.com/maps/place/{store_data.location_url}"
                        )
                    else:
                        tag["href"] = store_data.location_url

        for tag in soup.find_all(id="instagram"):
            if tag is not None:
                if store_data.instagram_address is not None:
                    if "instagram.com" in store_data.instagram_address:
                        tag["href"] = f"{store_data.instagram_address}"
                    else:
                        tag["href"] = (
                            f"https://instagram.com/{store_data.instagram_address}"
                        )

        for tag in soup.find_all(id="phone"):
            if tag is not None:
                tag["href"] = f"Tel:{store_data.telephone}"
        if "saahel" in base_template_name:
            for tag in soup.find_all(id="telegram"):
                if tag is not None:
                    tag["href"] = (
                        f"https://t.me/+98{remove_leading_zero(store_data.cellphone)}"
                    )
            for tag in soup.find_all(id="eitaa"):
                if tag is not None:
                    tag["href"] = (
                        f"https://eitaa.com/+98{remove_leading_zero(store_data.cellphone)}"
                    )

        # Handle meta tags and redirect URL for smart templates
        for tag in soup.find_all(id="descript"):
            if tag is not None:
                tag["content"] = (
                    selected_menu.description
                    if selected_menu.description
                    else store_data.brand_name
                )

        for tag in soup.find_all(id="canon"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        for tag in soup.find_all(id="redirectUrl"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        new_text = soup.prettify()

    # Write new contents to test.html
    with open(f"../{menu_folder_name}/{file_name}.html", mode="w") as new_html_file:
        new_html_file.write(new_text)
    db.commit()
    return {"success": True}


async def publish_a_menu_after_subscription(
    menu_id: int = 1457,
    store_id: int = 2060,
    theme: Optional[PublishMenu] = None,
    db: Session = Depends(get_db),
):
    # At the start of your publish_a_menu_after_subscription function
    all_menus_primary = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == store_id, models.Menu.is_sub_shop == False)
        .all()
    )
    store_data = db.query(models.Members).filter(models.Members.id == store_id).first()
    real_store_data = (
        db.query(models.Members).filter(models.Members.id == store_id).first()
    )
    all_menus = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == store_id)
        .filter(models.Menu.id == menu_id)
        .first()
    )
    selected_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    print("Selected Menu:", selected_menu)

    file_name = ""
    menu_folder_name = os.getenv("MENU_FOLDER_NAME")
    if selected_menu.is_sub_shop:
        shop_info = (
            db.query(models.Shops)
            .filter(models.Shops.id == selected_menu.shop_id)
            .first()
        )
        store_data = shop_info
        all_menus = (
            db.query(models.Menu)
            .filter(models.Menu.shop_id == shop_info.id)
            .filter(models.Menu.id == menu_id)
            .first()
        )
        all_menus_primary = (
            db.query(models.Menu).filter(models.Menu.shop_id == shop_info.id).all()
        )
        if shop_info.default_url is not None:
            if "https://" in shop_info.default_url:
                file_name = shop_info.default_url.split("/")[-1]
                menu_folder_name = shop_info.default_url.split("/")[-2]

            else:
                file_name = shop_info.default_url
        else:
            file_name = members.generate_random_value(7)
            shop_info.default_url = file_name
            db.add(shop_info)
            db.commit()

    else:
        if store_data.default_url is not None:
            if "https://" in store_data.default_url:
                file_name = store_data.default_url.split("/")[-1]
                menu_folder_name = store_data.default_url.split("/")[-2]

            else:
                file_name = store_data.default_url
        else:
            file_name = members.generate_random_value(7)
            store_data.default_url = file_name
            db.add(store_data)
            db.commit()
    menu_name = ""
    if selected_menu is not None:
        menu_name = selected_menu.title
        tmp_name = selected_menu.template_name
        if tmp_name == None or tmp_name == "":
            tmp_name = "custom"

        # Handle custom templates (e.g., shiraz_custom)
        base_template_name = tmp_name
        if "custom" in tmp_name and "_custom" in tmp_name:
            # Extract base template name (e.g., "shiraz" from "shiraz_custom")
            base_template_name = tmp_name.split("_custom")[0]
            print(
                f"Custom template detected: {tmp_name}, using base template: {base_template_name}"
            )

        # type 1
        categoryObj = []
        foodObject = []
        categories = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.parent_id != 0)
            .filter(models.FoodCategory.enabled == True)
            .filter(models.FoodCategory.menu_id == menu_id)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(
                models.FoodCategory.parent_id.asc(), models.FoodCategory.position.asc()
            )
            .all()
        )
        print("📂 Retrieved Categories:", categories)
        print("📂 Number of Categories:", len(categories))

        parent_cats = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.parent_id == 0)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        print("📁 Parent Categories:", parent_cats)

        all_menus.categories = categories
        saahel_subs = []
        for index, category in enumerate(categories):
            food = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == all_menus.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )
            print(f"Foods for category {category.id} - {category.title}: {food}")
            if category.enabled > 0:
                if "Dalia" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Dalia_v2" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Shabnam" in base_template_name:
                    if category.parent_id != 0:
                        if category.parent_id != menu_id:
                            head_cat = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == category.parent_id)
                                .first()
                            )
                            categoryObj.append(
                                {
                                    "category": category.title,
                                    "id": category.id,
                                    "parent_id": category.parent_id,
                                    "position": category.position,
                                    "parent_id_position": head_cat.position,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                        else:
                            all_heads = (
                                db.query(models.FoodCategory)
                                .filter(
                                    models.FoodCategory.parent_id == 0,
                                    models.FoodCategory.menu_id == menu_id,
                                )
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            if len(all_heads) > 0:
                                categoryObj.append(
                                    {
                                        "category": category.title,
                                        "id": category.id,
                                        "parent_id": category.parent_id,
                                        "position": category.position,
                                        "parent_id_position": all_heads[-1].position
                                        + 1,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            else:
                                categoryObj.append(
                                    {
                                        "category": category.title,
                                        "id": category.id,
                                        "parent_id": category.parent_id,
                                        "position": category.position,
                                        "parent_id_position": 0,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                elif "Sorme" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            for item in subs:
                                all_sub.append(item.title)
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "subCategory": all_sub,
                                    "parent_id": pr.parent_id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    if category.parent_is_menu:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(
                                models.FoodCategory.parent_id == category.id,
                                models.FoodCategory.menu_id != category.id,
                            )
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        all_sub = []
                        for item in subs:
                            all_sub.append(item.title)
                        categoryObj.append(
                            {
                                "category": category.title,
                                "id": category.id,
                                "subCategory": all_sub,
                                "parent_id": category.parent_id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Yakh" in base_template_name:
                    if category.parent_id != 0:
                        titles = {"fa": category.title}
                        if (
                            hasattr(category, "multi_language_data")
                            and category.multi_language_data
                        ):
                            try:
                                lang_data = json.loads(category.multi_language_data)
                                additional_titles = {
                                    item["language_id"]: item["title"]
                                    for item in lang_data
                                    if item.get("language_id") != "fa"
                                }
                                titles.update(additional_titles)
                            except json.JSONDecodeError:
                                titles = {}
                        categoryObj.append(
                            {
                                "category": titles,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "shiraz" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            for val in subs:
                                cat_ig = val.cat_image
                                if len(cat_ig) == 0:
                                    cat_ig = f'{os.getenv("BASE_URL")}/images/defaults/CatIcon.svg'
                                else:
                                    if "https://" in val.cat_image:
                                        cat_ig = val.cat_image
                                    else:
                                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": pr.title,
                                        "subCategory": val.title,
                                        "icon": cat_ig,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    if subcats:
                        for val in subcats:
                            cat_ig = val.cat_image
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in val.cat_image:
                                    cat_ig = val.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": category.title,
                                    "subCategory": val.title,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    else:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        saahel_subs.append(
                            {
                                "id": category.id,
                                "category": category.title,
                                "subCategory": category.title,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                    # if category.parent_is_menu:
                    if category.parent_is_menu == True:
                        categoryObj.append(
                            {
                                "category": category.title,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "custom" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "parent_is_menu": pr.parent_is_menu,
                                    "parent_id": pr.parent_id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    categoryObj.append(
                        {
                            "category": category.title,
                            "id": category.id,
                            "parent_id": category.parent_id,
                            "parent_is_menu": category.parent_is_menu,
                            **(
                                {"status": category.enabled}
                                if real_store_data.access_type == 3
                                and not category.parent_is_menu
                                else (
                                    {"status": 1}
                                    if real_store_data.access_type == 3
                                    and category.parent_is_menu
                                    else {}
                                )
                            ),
                        }
                    )
                elif "zomorod" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "Zomorod" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "gerdoo" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "sepehr" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            find_foods = (
                                db.query(models.Foods)
                                .filter(models.Foods.cat_id == pr.id)
                                .all()
                            )
                            for item in subs:
                                all_sub.append(item.title)
                            if len(all_sub) > 0 or len(find_foods) > 0:
                                titles = {"fa": pr.title}
                                if (
                                    hasattr(pr, "multi_language_data")
                                    and pr.multi_language_data
                                ):
                                    try:
                                        lang_data = json.loads(pr.multi_language_data)
                                        additional_titles = {
                                            item["language_id"]: item["title"]
                                            for item in lang_data
                                            if item.get("language_id") != "fa"
                                        }
                                        titles.update(additional_titles)
                                    except json.JSONDecodeError:
                                        titles = {}
                                categoryObj.append(
                                    {
                                        "category": titles,
                                        "id": pr.id,
                                        "parent_id": pr.parent_id,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )

                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    if subcats:
                        for val in subcats:
                            cat_ig = val.cat_image
                            if category.parent_id == menu_id:
                                cat_val = "سایر"
                                catid = 1
                                sub_val = category.title
                            else:
                                main_cat = (
                                    db.query(models.FoodCategory)
                                    .filter(
                                        models.FoodCategory.id == category.parent_id
                                    )
                                    .first()
                                )
                                cat_val = main_cat.title
                                catid = main_cat.id
                                sub_val = category.title
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in val.cat_image:
                                    cat_ig = val.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                            titles = {"fa": category.title}
                            if (
                                hasattr(category, "multi_language_data")
                                and category.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(category.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                except json.JSONDecodeError:
                                    titles = {}
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": cat_val,
                                    "catid": catid,
                                    "subCategory": titles,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    else:
                        cat_ig = category.cat_image
                        if category.parent_id == menu_id:
                            cat_val = "سایر"
                            catid = 1
                            sub_val = category.title
                        else:
                            main_cat = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == category.parent_id)
                                .first()
                            )
                            cat_val = main_cat.title
                            catid = main_cat.id
                            sub_val = category.title
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        titles = {"fa": category.title}
                        if (
                            hasattr(category, "multi_language_data")
                            and category.multi_language_data
                        ):
                            try:
                                lang_data = json.loads(category.multi_language_data)
                                additional_titles = {
                                    item["language_id"]: item["title"]
                                    for item in lang_data
                                    if item.get("language_id") != "fa"
                                }
                                titles.update(additional_titles)
                            except json.JSONDecodeError:
                                titles = {}
                        saahel_subs.append(
                            {
                                "id": category.id,
                                "category": cat_val,
                                "catid": catid,
                                "subCategory": titles,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                    if category.parent_is_menu:
                        if category.parent_id == menu_id:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(
                                    models.FoodCategory.parent_id == menu_id,
                                    models.FoodCategory.menu_id != category.id,
                                )
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            for item in subs:
                                if item.title not in all_sub:
                                    all_sub.append(item.title)
                            if len(all_sub) > 0:

                                resObj = {
                                    "category": "سایر",
                                    "id": 1,
                                    "parent_id": 0,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                                if resObj not in categoryObj:
                                    categoryObj.append(resObj)

                elif "cookie" in base_template_name:
                    if category.parent_id != 0:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "text": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

                elif "ivaan" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            all_sub = []
                            for item in subs:
                                all_sub.append(item.title)
                            if len(all_sub) > 0:
                                titles_sub = {"fa": pr.title}
                                if pr.multi_language_data:
                                    lang_data = json.loads(pr.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles_sub.update(additional_titles)

                            titles = {"fa": pr.title}
                            if pr.multi_language_data:
                                try:
                                    lang_data = json.loads(pr.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    categoryObj.append(
                                        {
                                            "category": titles,
                                            "id": pr.id,
                                            **(
                                                {"status": category.enabled}
                                                if real_store_data.access_type == 3
                                                and not category.parent_is_menu
                                                else (
                                                    {"status": 1}
                                                    if real_store_data.access_type == 3
                                                    and category.parent_is_menu
                                                    else {}
                                                )
                                            ),
                                        }
                                    )
                                except json.JSONDecodeError:
                                    titles = {}
                            else:
                                categoryObj.append(
                                    {
                                        "category": titles,
                                        "id": pr.id,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )

                    for new_sub in parent_cats:
                        subcats = (
                            db.query(models.FoodCategory)
                            .filter(
                                models.FoodCategory.parent_id == new_sub.id,
                                models.FoodCategory.menu_id != new_sub.id,
                            )
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        for val in subcats:
                            titles = {"fa": val.title}
                            if val.multi_language_data:
                                try:
                                    lang_data = json.loads(val.multi_language_data)
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                except json.JSONDecodeError:
                                    titles = {}
                            if len(saahel_subs) > 0:
                                if any(obj.get("id") != val.id for obj in saahel_subs):
                                    saahel_subs.append(
                                        {
                                            "id": val.id,
                                            "category": new_sub.title,
                                            "catid": new_sub.id,
                                            "subCategory": titles,
                                            **(
                                                {"status": new_sub.enabled}
                                                if real_store_data.access_type == 3
                                                and not new_sub.parent_is_menu
                                                else (
                                                    {"status": 1}
                                                    if real_store_data.access_type == 3
                                                    and new_sub.parent_is_menu
                                                    else {}
                                                )
                                            ),
                                        }
                                    )
                            else:
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": new_sub.title,
                                        "catid": new_sub.id,
                                        "subCategory": titles,
                                        **(
                                            {"status": new_sub.enabled}
                                            if real_store_data.access_type == 3
                                            and not new_sub.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and new_sub.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    all_sub = []
                    for val in subcats:
                        all_sub.append(val.title)

                    category.subCategory = all_sub
                    if category.parent_is_menu:
                        titles = {"fa": category.title}
                        if len(all_sub) > 0:
                            titles_sub = {"fa": pr.title}
                            lang_data = json.loads(pr.multi_language_data)
                            additional_titles = {
                                item["language_id"]: item["title"]
                                for item in lang_data
                                if item.get("language_id") != "fa"
                            }
                            titles_sub.update(additional_titles)
                        if (
                            hasattr(category, "multi_language_data")
                            and category.multi_language_data
                        ):
                            try:
                                lang_data = json.loads(category.multi_language_data)
                                additional_titles = {
                                    item["language_id"]: item["title"]
                                    for item in lang_data
                                    if item.get("language_id") != "fa"
                                }
                                titles.update(additional_titles)
                                categoryObj.append(
                                    {
                                        "category": titles,
                                        "id": category.id,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            except json.JSONDecodeError:
                                titles = {}
                        else:
                            categoryObj.append(
                                {
                                    "category": {"fa": category.title},
                                    "id": category.id,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )

                elif "saahel" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:
                            subs = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.parent_id == pr.id)
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            for val in subs:
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": pr.title,
                                        "subCategory": val.title,
                                        "icon": val.cat_image,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            cat_ig = pr.cat_image
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in pr.cat_image:
                                    cat_ig = pr.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{pr.cat_image}'
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "parent_is_menu": val.parent_is_menu,
                                    "parent_id": pr.parent_id,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .all()
                    )
                    for val in subcats:
                        saahel_subs.append(
                            {
                                "id": val.id,
                                "category": category.title,
                                "subCategory": val.title,
                                "icon": val.cat_image,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                    # if category.parent_is_menu:
                    if category.parent_is_menu == True:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "id": category.id,
                                "parent_id": category.parent_id,
                                "parent_is_menu": category.parent_is_menu,
                                "icon": cat_ig,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )
                elif "ghahve" in base_template_name:
                    if index == 0 and parent_cats:
                        for pr in parent_cats:

                            subs = (
                                db.query(models.FoodCategory)
                                .filter(
                                    models.FoodCategory.parent_id == pr.id,
                                    models.FoodCategory.menu_id == menu_id,
                                )
                                .order_by(models.FoodCategory.position.asc())
                                .all()
                            )
                            for val in subs:
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": pr.title,
                                        "subCategory": val.title,
                                        **(
                                            {"status": category.enabled}
                                            if real_store_data.access_type == 3
                                            and not category.parent_is_menu
                                            else (
                                                {"status": 1}
                                                if real_store_data.access_type == 3
                                                and category.parent_is_menu
                                                else {}
                                            )
                                        ),
                                    }
                                )
                            cat_ig = pr.cat_image
                            if len(cat_ig) == 0:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                            else:
                                if "https://" in pr.cat_image:
                                    cat_ig = pr.cat_image
                                else:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/{pr.cat_image}'
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "icon": cat_ig,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    subcats = (
                        db.query(models.FoodCategory)
                        .filter(
                            and_(
                                models.FoodCategory.parent_id == category.id,
                                models.FoodCategory.menu_id != category.id,
                            )
                        )
                        .all()
                    )
                    for val in subcats:
                        if val.menu_id != category.id:
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": category.title,
                                    "subCategory": val.title,
                                    **(
                                        {"status": category.enabled}
                                        if real_store_data.access_type == 3
                                        and not category.parent_is_menu
                                        else (
                                            {"status": 1}
                                            if real_store_data.access_type == 3
                                            and category.parent_is_menu
                                            else {}
                                        )
                                    ),
                                }
                            )
                    if category.parent_is_menu:
                        cat_ig = category.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        categoryObj.append(
                            {
                                "category": category.title,
                                "icon": cat_ig,
                                "id": category.id,
                                **(
                                    {"status": category.enabled}
                                    if real_store_data.access_type == 3
                                    and not category.parent_is_menu
                                    else (
                                        {"status": 1}
                                        if real_store_data.access_type == 3
                                        and category.parent_is_menu
                                        else {}
                                    )
                                ),
                            }
                        )

        # type2
        categories = (
            db.query(models.FoodCategory)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        all_menus.categories = categories
        for category in categories:
            if category.enabled > 0:
                food = (
                    db.query(models.Foods)
                    .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                    .filter(
                        models.MenuIDS.menu_id == all_menus.id,
                        models.MenuIDS.cat_id == category.id,
                    )
                    .order_by(models.Foods.position.asc())
                    .all()
                )

                category.text = category.title
                category.icon = category.cat_image
                subcats = (
                    db.query(models.FoodCategory)
                    .filter(
                        models.FoodCategory.parent_id == category.id,
                        models.FoodCategory.menu_id != category.id,
                    )
                    .all()
                )
                for foodObj in food:
                    if foodObj.available > 0:
                        all_img = []
                        for food in foodObj.food_image:
                            all_img.append(
                                f'{os.getenv("BASE_URL")}/food/images/{food}'
                            )
                        if len(all_img) == 0:
                            if (
                                store_data.brand_logo != None
                                and len(store_data.brand_logo) > 0
                            ):
                                all_img.append(
                                    f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                                )
                            else:
                                all_img.append(
                                    f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                                )
                        video_url = ""
                        if foodObj.food_video != None and len(foodObj.food_video) > 0:
                            video_url = f'{os.getenv("BASE_URL")}/food/videos/{foodObj.food_video}'
                        if "custom" in base_template_name:
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "category": category.title,
                                "images": all_img,
                                "details": foodObj.description,
                                "price": foodObj.price,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available

                            foodObject.append(food_dict)
                        elif "Dalia" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "category": category.title,
                                "images": all_img,
                                "details": foodObj.description,
                                "price": final_price,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "Dalia_v2" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "category": category.title,
                                "images": all_img,
                                "details": foodObj.description,
                                "price": final_price,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "Shabnam" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "price": final_price,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "Sorme" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            food_dict = {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "price": final_price,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                                "subCategoryFood": cat_name.title,
                            }
                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)

                        elif "Yakh" in base_template_name:
                            final_price = 0
                            if foodObj.price == "0":
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    final_price = list(foodObj.sizes)[0].get("price")
                            else:
                                final_price = foodObj.price
                            titles = {"fa": foodObj.title}
                            prces = {"fa": foodObj.price}
                            descs = {"fa": foodObj.description}
                            cat_multii = {"fa": category.title}
                            cat_id = category.id
                            if (
                                hasattr(foodObj, "multi_language_data")
                                and foodObj.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(
                                        str(foodObj.multi_language_data)
                                    )
                                    add_prices = {
                                        item["language_id"]: item["price"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    add_desc = {
                                        item["language_id"]: item["description"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    prces.update(add_prices)
                                    descs.update(add_desc)
                                except json.JSONDecodeError:
                                    titles = {}
                                    prces = {}
                                    descs = {}
                                if (
                                    hasattr(category, "multi_language_data")
                                    and category.multi_language_data
                                ):
                                    cat_lang_data = json.loads(
                                        category.multi_language_data
                                    )
                                    try:
                                        cat_multi = {
                                            item["language_id"]: item["title"]
                                            for item in cat_lang_data
                                            if item.get("language_id") != "fa"
                                        }
                                        cat_multii.update(cat_multi)
                                    except json.JSONDecodeError:
                                        cat_multii = {}
                            food_dict = {
                                "id": foodObj.id,
                                "title": titles,
                                "englishTitle": foodObj.englishTitle,
                                "price": prces,
                                "category": cat_multii,
                                "images": all_img,
                                "category_id": cat_id,
                                "details": descs,
                                "videoUrl": video_url,
                            }

                            if real_store_data.access_type == 3:
                                food_dict["status"] = foodObj.available
                            foodObject.append(food_dict)
                        elif "zomorod" in base_template_name:
                            food_image = ""
                            if len(foodObj.food_image) > 0:
                                food_image = f'{os.getenv("BASE_URL")}/food/images/{foodObj.food_image[0]}'
                            elif (
                                store_data.brand_logo != None
                                and len(store_data.brand_logo) > 0
                            ):
                                food_image = f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'

                            else:
                                food_image = f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available

                                    food_dict = {
                                        "id": foodObj.id,
                                        "name": foodObj.title,
                                        "sizes": foodObj.sizes,
                                        "category": category.title,
                                        "image": food_image,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                    }
                                    if real_store_data.access_type == 3:
                                        food_dict["status"] = foodObj.available
                                    foodObject.append(food_dict)
                                else:
                                    food_dict = {
                                        "id": foodObj.id,
                                        "name": foodObj.title,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "category": category.title,
                                        "image": food_image,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                    }
                                    if real_store_data.access_type == 3:
                                        food_dict["status"] = foodObj.available
                                    foodObject.append(food_dict)
                            else:
                                food_dict = {
                                    "id": foodObj.id,
                                    "name": foodObj.title,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "category": category.title,
                                    "image": food_image,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                                if real_store_data.access_type == 3:
                                    food_dict["status"] = foodObj.available
                                foodObject.append(food_dict)
                        elif "ivaan" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            titles = {"fa": foodObj.title}
                            prces = {"fa": foodObj.price}
                            descs = {"fa": foodObj.description}
                            if (
                                hasattr(foodObj, "multi_language_data")
                                and foodObj.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(
                                        str(foodObj.multi_language_data)
                                    )
                                    add_prices = {
                                        item["language_id"]: item["price"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    add_desc = {
                                        item["language_id"]: item["description"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    prces.update(add_prices)
                                    descs.update(add_desc)
                                except json.JSONDecodeError:
                                    titles = {}
                                    prces = {}
                                    descs = {}
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                        find_datas = it.get("size")
                                        if (
                                            hasattr(foodObj, "multi_language_data")
                                            and foodObj.multi_language_data
                                        ):
                                            multi = ast.literal_eval(
                                                str(foodObj.multi_language_data)
                                            )
                                            new_titles = {}
                                            new_prices = {}

                                            for item in multi:
                                                if (
                                                    item.get("sizes")
                                                    and len(item.get("sizes")) > 0
                                                ):
                                                    for in_size in item.get("sizes"):

                                                        if (
                                                            in_size.get("size")
                                                            == find_datas
                                                        ):
                                                            new_titles[
                                                                item.get("language_id")
                                                            ] = in_size.get("title")
                                                            new_prices[
                                                                item.get("language_id")
                                                            ] = str(
                                                                in_size.get("price")
                                                            )
                                                else:
                                                    new_titles[
                                                        item.get("language_id")
                                                    ] = ""
                                                    new_prices[
                                                        item.get("language_id")
                                                    ] = "0.0"
                                            it["title"] = new_titles
                                            it["price"] = new_prices
                                        else:
                                            if find_datas:
                                                it["title"] = {"fa": it.get("title")}
                                                it["price"] = {"fa": it.get("price")}
                                            else:
                                                it["title"] = {"fa": None}
                                                it["price"] = {"fa": None}

                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": titles,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory_id": cat_name.id,
                                            "category_id": category.id,
                                            "images": all_img,
                                            "description": descs,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )

                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": titles,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": prces,
                                            "sizes": None,
                                            "subCategory_id": cat_name.id,
                                            "category_id": category.id,
                                            "images": all_img,
                                            "description": descs,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )

                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": titles,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": prces,
                                        "sizes": None,
                                        "subCategory_id": cat_name.id,
                                        "category_id": category.id,
                                        "images": all_img,
                                        "description": descs,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )

                        elif "ghahve" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "subCategory": cat_name.title,
                                            "sizes": None,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "subCategory": cat_name.title,
                                        "sizes": None,
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "shiraz" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "subCategory": cat_name.title,
                                            "sizes": [],
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "subCategory": cat_name.title,
                                        "sizes": [],
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "gerdoo" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "sizes": None,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "subCategory": cat_name.title,
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "sepehr" in base_template_name:
                            englishTitle = foodObj.englishTitle
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.englishTitle == None:
                                englishTitle = ""
                            if category.parent_id == menu_id:
                                cat_val = "سایر"
                                cat_id = 1
                                sub_id = cat_name.id
                                sub_val = cat_name.title
                            else:
                                main_cat = (
                                    db.query(models.FoodCategory)
                                    .filter(
                                        models.FoodCategory.id == cat_name.parent_id
                                    )
                                    .first()
                                )
                                cat_val = main_cat.title
                                sub_val = cat_name.title
                                cat_id = main_cat.id
                                sub_id = cat_name.id
                            titles = {"fa": foodObj.title}
                            prces = {"fa": foodObj.price}
                            descs = {"fa": foodObj.description}
                            if (
                                hasattr(foodObj, "multi_language_data")
                                and foodObj.multi_language_data
                            ):
                                try:
                                    lang_data = json.loads(
                                        str(foodObj.multi_language_data)
                                    )
                                    add_prices = {
                                        item["language_id"]: item["price"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    add_desc = {
                                        item["language_id"]: item["description"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    additional_titles = {
                                        item["language_id"]: item["title"]
                                        for item in lang_data
                                        if item.get("language_id") != "fa"
                                    }
                                    titles.update(additional_titles)
                                    prces.update(add_prices)
                                    descs.update(add_desc)
                                except json.JSONDecodeError:
                                    titles = {}
                                    prces = {}
                                    descs = {}
                            if foodObj.sizes != None:

                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for new_item in foodObj.sizes:
                                        find_datas = new_item.get("size")

                                        if (
                                            hasattr(foodObj, "multi_language_data")
                                            and foodObj.multi_language_data
                                        ):
                                            multi = json.loads(
                                                str(foodObj.multi_language_data)
                                            )
                                            new_titles = {}
                                            new_prices = {}

                                            for item in multi:
                                                if (
                                                    item.get("sizes")
                                                    and len(item.get("sizes")) > 0
                                                ):
                                                    for in_size in item.get("sizes"):

                                                        if (
                                                            in_size.get("size")
                                                            == find_datas
                                                        ):
                                                            new_titles[
                                                                item.get("language_id")
                                                            ] = in_size.get("title")
                                                            new_prices[
                                                                item.get("language_id")
                                                            ] = str(
                                                                in_size.get("price")
                                                            )
                                                else:
                                                    new_titles[
                                                        item.get("language_id")
                                                    ] = ""
                                                    new_prices[
                                                        item.get("language_id")
                                                    ] = "0.0"
                                            new_item["title"] = new_titles
                                            new_item["price"] = new_prices
                                        else:
                                            if find_datas:
                                                it["title"] = {"fa": it.get("title")}
                                                it["price"] = {"fa": it.get("price")}
                                            else:
                                                it["title"] = {"fa": None}
                                                it["price"] = {"fa": None}

                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": titles,
                                            "englishTitle": englishTitle,
                                            "sizes": foodObj.sizes,
                                            "category_id": cat_id,
                                            "subCategory_id": sub_id,
                                            "images": all_img,
                                            "description": descs,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:

                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": titles,
                                            "englishTitle": englishTitle,
                                            "MainPrice": prces,
                                            "sizes": None,
                                            "category_id": cat_id,
                                            "subCategory_id": sub_id,
                                            "images": all_img,
                                            "description": descs,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": titles,
                                        "englishTitle": englishTitle,
                                        "MainPrice": prces,
                                        "sizes": None,
                                        "category_id": cat_id,
                                        "subCategory_id": sub_id,
                                        "images": all_img,
                                        "description": descs,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "cookie" in base_template_name:
                            popup = None
                            all_imgs = None
                            if len(all_img) > 0:
                                all_imgs = all_img[0]
                                if len(all_img) > 1:
                                    popup = all_img[1]
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "sizes": foodObj.sizes,
                                            "category": category.title,
                                            "image": all_imgs,
                                            "popupBackground": popup,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "englishTitle": foodObj.englishTitle,
                                            "MainPrice": foodObj.price,
                                            "sizes": None,
                                            "category": category.title,
                                            "image": all_imgs,
                                            "popupBackground": popup,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "englishTitle": foodObj.englishTitle,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "category": category.title,
                                        "image": all_imgs,
                                        "popupBackground": popup,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )
                        elif "saahel" in base_template_name:
                            cat_name = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == foodObj.cat_id)
                                .first()
                            )
                            if foodObj.sizes != None:
                                if len(foodObj.sizes) > 0:
                                    foodObj.sizes = [
                                        it
                                        for it in foodObj.sizes
                                        if it.get("status", 1) is not None
                                        and it.get("status", 1) != 0
                                    ]
                                    for it in foodObj.sizes:
                                        if "status" not in it:
                                            it["status"] = foodObj.available
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "sizes": foodObj.sizes,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                                else:
                                    foodObject.append(
                                        {
                                            "id": foodObj.id,
                                            "title": foodObj.title,
                                            "MainPrice": foodObj.price,
                                            "sizes": None,
                                            "subCategory": cat_name.title,
                                            "category": category.title,
                                            "images": all_img,
                                            "description": foodObj.description,
                                            "videoUrl": video_url,
                                            **(
                                                {"status": foodObj.available}
                                                if real_store_data.access_type == 3
                                                else {}
                                            ),
                                        }
                                    )
                            else:
                                foodObject.append(
                                    {
                                        "id": foodObj.id,
                                        "title": foodObj.title,
                                        "MainPrice": foodObj.price,
                                        "sizes": None,
                                        "subCategory": cat_name.title,
                                        "category": category.title,
                                        "images": all_img,
                                        "description": foodObj.description,
                                        "videoUrl": video_url,
                                        **(
                                            {"status": foodObj.available}
                                            if real_store_data.access_type == 3
                                            else {}
                                        ),
                                    }
                                )

    else:
        raise HTTPException(
            status_code=403, detail="You should select a template from the list"
        )
    if "Shabnam" in base_template_name:
        categoryObj.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )
    elif "ivaan" in base_template_name:
        categoryObj.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )
        saahel_subs.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )
    store_info = []
    find_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    menu_description = {"fa": find_menu.description}

    if hasattr(find_menu, "multi_language_data") and find_menu.multi_language_data:
        for lang_data in json.loads(find_menu.multi_language_data):
            if lang_data.get("language_id") != "fa":
                menu_description[lang_data.get("language_id")] = lang_data.get(
                    "description"
                )

    if selected_menu.is_sub_shop:
        store = db.query(models.Members).filter(models.Members.id == store_id).first()

        store_info.append(
            {
                "store_id": store.id,
                "shop_id": store_data.id,
                "online_access": store.online_order,
                "menu_id": menu_id,
                "is_restaurant": bool(getattr(store_data, "IsShop", 0)),
                "multiLanguage": shop_info.multi_language_currency,
                "currencies": (
                    (
                        {
                            item["language"]: item["currency"]
                            for item in (
                                store_data.language_currencies
                                if isinstance(store_data.language_currencies, list)
                                else json.loads(store_data.language_currencies)
                            )
                            if isinstance(item, dict)
                            and "language" in item
                            and "currency" in item
                        }
                    )
                    if store_data.multi_language_currency
                    and store_data.language_currencies
                    else None
                ),
                "callorder": store.call_order,
                "payment_gateway": store.payment_gateway,
                "payment_methods": store.payment_methods,
                "city": store.city,
                "address": store_data.address,
            }
        )

    else:
        store_info.append(
            {
                "store_id": store_data.id,
                "shop_id": None,
                "online_access": store_data.online_order,
                "menu_id": menu_id,
                "is_restaurant": bool(getattr(store_data, "IsShop", 0)),
                "multiLanguage": store_data.multi_language_currency,
                "currencies": (
                    (
                        {
                            item["language"]: item["currency"]
                            for item in (
                                store_data.language_currencies
                                if isinstance(store_data.language_currencies, list)
                                else json.loads(store_data.language_currencies)
                            )
                            if isinstance(item, dict)
                            and "language" in item
                            and "currency" in item
                        }
                    )
                    if store_data.multi_language_currency
                    and store_data.language_currencies
                    else None
                ),
                "callorder": store_data.call_order,
                "payment_gateway": store_data.payment_gateway,
                "payment_methods": store_data.payment_methods,
                "city": store_data.city,
                "address": store_data.address,
            }
        )

    print(
        "✅ Final CategoryObj:", json.dumps(categoryObj, indent=2, ensure_ascii=False)
    )
    print("✅ Final FoodObject:", json.dumps(foodObject, indent=2, ensure_ascii=False))

    json_object = json.dumps(categoryObj, indent=4, ensure_ascii=False)
    food_object = json.dumps(foodObject, indent=4, ensure_ascii=False)
    shop_object = json.dumps(store_info, indent=4, ensure_ascii=False)
    desc_object = json.dumps(menu_description, indent=4, ensure_ascii=False)
    template_filename = f"{tmp_name.lower()}.html"
    search_results = find_file(template_filename, Path("/"))
    # # Writing to js file
    if "saahel" in base_template_name:
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods,subCategories,store_info};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "sepehr" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + f"const menu_description={desc_object}\n"
                f'const background="{backg}"\n'
                + "export {"
                + "categories,foods,subCategories,background,store_info,menu_description};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "ghahve" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                + f'const background="{backg}"\n'
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods,subCategories , background,store_info};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "shiraz" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            if theme is not None and (
                theme.backgroundColor or theme.secondColor is not None
            ):
                back_obj = json.dumps(
                    {
                        "bodyColor": theme.backgroundColor,
                        "secondaryColor": theme.secondColor,
                    },
                    indent=4,
                    ensure_ascii=False,
                )
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                    + f'const background="{backg}"\n'
                    + f"const theme = {back_obj}\n"
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme, store_info};"
                )
            else:
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                                const foods={food_object}\n"
                    + f'const background="{backg}"\n const theme = null;\n'
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme,store_info};"
                )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "gerdoo" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            if theme is not None and (
                theme.backgroundColor or theme.secondColor is not None
            ):
                back_obj = json.dumps(
                    {
                        "bodyColor": theme.backgroundColor,
                        "secondaryColor": theme.secondColor,
                    },
                    indent=4,
                    ensure_ascii=False,
                )
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                    + f'const background="{backg}"\n'
                    + f"const theme = {back_obj}\n"
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme, store_info};"
                )
            else:
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                                const foods={food_object}\n"
                    + f'const background="{backg}"\n const theme = null;\n'
                    + f"const store_info={shop_object}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme,store_info};"
                )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "ivaan" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        saahel_subs = list({item["id"]: item for item in saahel_subs}.values())
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n "
                + f"const subCategories={saahel_subs}\n"
                + f"const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + f"const menu_description={desc_object}\n"
                f'const background="{backg}"\n'
                + "export {"
                + "categories,foods,background,store_info,subCategories,menu_description};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)

    elif "Shabnam" in base_template_name:
        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const foods={food_object}\n"
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods , store_info};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    else:

        with open(
            f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const foods={food_object}\n"
                + f"const menu_description={desc_object}\n"
                + f"const store_info={shop_object}\n"
                + "export {"
                + "categories,foods,store_info,menu_description};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)

    folder_name = (
        menu_folder_name if isinstance(menu_folder_name, str) else "menu.rhinomenu.com"
    )
    template_path = get_template_path(folder_name, tmp_name)
    with open(template_path) as html_file:

        soup = BeautifulSoup(html_file.read(), features="html.parser")
        # if 'Dalia' in tmp_name:
        for tag in soup.find_all(id="change-data"):
            if tag is not None:
                tag.string.replace_with(str(random.randint(10, 99)))

        for tag in soup.find(id="menu_name"):
            tag.string.replace_with(menu_name)
        for tag in soup.find_all(id="restaurant_title"):
            if tag is not None:
                tag.string = store_data.brand_name

        for tag in soup.find_all(id="food_desc"):
            if tag is not None:
                tag.string = selected_menu.description
        for tag in soup.find_all(id="desc"):
            if tag is not None:
                tag.string = selected_menu.description

        for tag in soup.find_all(id="res_logo"):
            if tag is not None:
                if store_data.brand_logo != None and store_data.brand_logo != "":
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                    )
                else:
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                    )

        for tag in soup.find_all(id="map"):
            if tag is not None:
                if store_data.location_url != None:
                    if "https" not in store_data.location_url:
                        tag["href"] = (
                            f"https://www.google.com/maps/place/{store_data.location_url}"
                        )
                    else:
                        tag["href"] = store_data.location_url

        for tag in soup.find_all(id="instagram"):
            if tag is not None:
                if store_data.instagram_address is not None:
                    if "instagram.com" in store_data.instagram_address:
                        tag["href"] = f"{store_data.instagram_address}"
                    else:
                        tag["href"] = (
                            f"https://instagram.com/{store_data.instagram_address}"
                        )

        for tag in soup.find_all(id="phone"):
            if tag is not None:
                tag["href"] = f"Tel:{store_data.telephone}"
        if "saahel" in base_template_name:
            for tag in soup.find_all(id="telegram"):
                if tag is not None:
                    tag["href"] = (
                        f"https://t.me/+98{remove_leading_zero(store_data.cellphone)}"
                    )
            for tag in soup.find_all(id="eitaa"):
                if tag is not None:
                    tag["href"] = (
                        f"https://eitaa.com/+98{remove_leading_zero(store_data.cellphone)}"
                    )

        # Handle meta tags and redirect URL for smart templates
        for tag in soup.find_all(id="descript"):
            if tag is not None:
                tag["content"] = (
                    selected_menu.description
                    if selected_menu.description
                    else store_data.brand_name
                )

        for tag in soup.find_all(id="canon"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        for tag in soup.find_all(id="redirectUrl"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        new_text = soup.prettify()

    # Write new contents to test.html
    with open(f"../{menu_folder_name}/{file_name}.html", mode="w") as new_html_file:
        new_html_file.write(new_text)
    db.commit()
    return {"success": True}


def find_file(filename: str, search_path: Path):
    found_files = []

    for root, dirs, files in os.walk(search_path):
        if filename in files:
            found_path = Path(root) / filename
            found_files.append(found_path)

    return found_files


def get_template_path(menu_folder_name: str, template_name: str) -> str:
    current_dir = Path(__file__).resolve().parent

    api_dir = current_dir.parent

    root_dir = api_dir.parent

    template_path = (
        Path("/") / menu_folder_name / "rinho" / f"{template_name.lower()}.html"
    )

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found at: {template_path}")

    return str(template_path)


async def publish_menu_local(menu_id, user_id, db: Session = Depends(get_db)):
    all_menus_primary = (
        db.query(models.Menu).filter(models.Menu.store_id == user_id).all()
    )
    store_data = db.query(models.Members).filter(models.Members.id == user_id).first()
    all_menus = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user_id)
        .filter(models.Menu.id == menu_id)
        .first()
    )
    selected_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    file_name = ""
    menu_folder_name = os.getenv("MENU_FOLDER_NAME")
    if selected_menu.is_sub_shop:
        shop_info = (
            db.query(models.Shops)
            .filter(models.Shops.id == selected_menu.shop_id)
            .first()
        )
        store_data = shop_info
        all_menus = (
            db.query(models.Menu)
            .filter(models.Menu.shop_id == shop_info.id)
            .filter(models.Menu.id == menu_id)
            .first()
        )
        all_menus_primary = (
            db.query(models.Menu).filter(models.Menu.shop_id == shop_info.id).all()
        )
        if shop_info.default_url is not None:
            if "https://" in shop_info.default_url:
                file_name = shop_info.default_url.split("/")[-1]
                menu_folder_name = shop_info.default_url.split("/")[-2]

            else:
                file_name = shop_info.default_url
        else:
            file_name = members.generate_random_value(7)
            shop_info.default_url = file_name
            db.add(shop_info)
            db.commit()

    else:
        if store_data.default_url is not None:
            if "https://" in store_data.default_url:
                file_name = store_data.default_url.split("/")[-1]
                menu_folder_name = store_data.default_url.split("/")[-2]

            else:
                file_name = store_data.default_url
        else:
            file_name = members.generate_random_value(7)
            store_data.default_url = file_name
            db.add(store_data)
            db.commit()
    menu_name = ""
    if selected_menu is not None:
        menu_name = selected_menu.title
        tmp_name = selected_menu.template_name
        if tmp_name == None or tmp_name == "":
            tmp_name = "custom"

        # Handle custom templates (e.g., shiraz_custom)
        base_template_name = tmp_name
        if "custom" in tmp_name and "_custom" in tmp_name:
            # Extract base template name (e.g., "shiraz" from "shiraz_custom")
            base_template_name = tmp_name.split("_custom")[0]
            print(
                f"Custom template detected: {tmp_name}, using base template: {base_template_name}"
            )

        # type 1
        categoryObj = []
        foodObject = []
        categories = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.parent_id != 0)
            .filter(models.FoodCategory.menu_id == menu_id)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        parent_cats = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.parent_id == 0)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )

        all_menus.categories = categories
        saahel_subs = []
        for index, category in enumerate(categories):
            food = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == all_menus.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )
            print(f"Foods for category {category.id} - {category.title}: {food}")

            if "Dalia" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append({"category": category.title, "icon": cat_ig})
            elif "Dalia_v2" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append({"category": category.title, "icon": cat_ig})

        categories = (
            db.query(models.FoodCategory)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        all_menus.categories = categories
        for category in categories:
            food = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == all_menus.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )

            category.text = category.title
            category.icon = category.cat_image
            subcats = (
                db.query(models.FoodCategory)
                .filter(
                    models.FoodCategory.parent_id == category.id,
                    models.FoodCategory.menu_id != category.id,
                )
                .all()
            )
            for foodObj in food:
                all_img = []
                for food in foodObj.food_image:
                    all_img.append(f'{os.getenv("BASE_URL")}/food/images/{food}')
                if len(all_img) == 0:
                    if store_data.brand_logo != None and len(store_data.brand_logo) > 0:
                        all_img.append(
                            f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                        )
                    else:
                        all_img.append(
                            f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                        )
                video_url = ""
                if foodObj.food_video != None and len(foodObj.food_video) > 0:
                    video_url = (
                        f'{os.getenv("BASE_URL")}/food/videos/{foodObj.food_video}'
                    )
                if "Dalia" in base_template_name:
                    final_price = 0
                    if foodObj.price == "0":
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            final_price = list(foodObj.sizes)[0].get("price")
                    else:
                        final_price = foodObj.price
                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "category": category.title,
                            "images": all_img,
                            "details": foodObj.description,
                            "price": final_price,
                            "videoUrl": video_url,
                        }
                    )
                elif "Dalia_v2" in base_template_name:
                    final_price = 0
                    if foodObj.price == "0":
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            final_price = list(foodObj.sizes)[0].get("price")
                    else:
                        final_price = foodObj.price
                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "category": category.title,
                            "images": all_img,
                            "details": foodObj.description,
                            "price": final_price,
                            "videoUrl": video_url,
                        }
                    )

    if "Shabnam" in base_template_name:
        categoryObj.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )
    store_info = []
    if selected_menu.is_sub_shop:
        store = (
            db.query(models.Members).filter(models.Members.id == user.get("id")).first()
        )
        store_info.append(
            {
                "store_id": store.id,
                "shop_id": store_data.id,
                "online_access": store.online_order,
            }
        )

    else:
        store_info.append(
            {
                "store_id": store_data.id,
                "shop_id": None,
                "online_access": store_data.online_order,
            }
        )

    print(
        "✅ Final CategoryObj:", json.dumps(categoryObj, indent=2, ensure_ascii=False)
    )
    print("✅ Final FoodObject:", json.dumps(foodObject, indent=2, ensure_ascii=False))

    json_object = json.dumps(categoryObj, indent=4, ensure_ascii=False)
    food_object = json.dumps(foodObject, indent=4, ensure_ascii=False)
    shop_object = json.dumps(store_info, indent=4, ensure_ascii=False)
    with open(
        f"../{menu_folder_name}/{file_name}.js", "w", encoding="utf-8"
    ) as outfile:
        outfile.write(
            f"const categories = {json_object}\n const foods={food_object}\n"
            + f"const store_info={shop_object}\n"
            + "export {"
            + "categories,foods,store_info};"
        )

    template_path = find_template_file(menu_folder_name, base_template_name)
    with open(template_path) as html_file:
        # with open(f"../{menu_folder_name}/{tmp_name.lower()}.html") as html_file:
        soup = BeautifulSoup(html_file.read(), features="html.parser")
        # if 'Dalia' in tmp_name:
        for tag in soup.find_all(id="change-data"):
            if tag is not None:
                tag.string.replace_with(str(random.randint(10, 99)))

        for tag in soup.find(id="menu_name"):
            tag.string.replace_with(menu_name)
        for tag in soup.find_all(id="restaurant_title"):
            if tag is not None:
                tag.string = store_data.brand_name

        for tag in soup.find_all(id="food_desc"):
            if tag is not None:
                tag.string = selected_menu.description
                # tag.string.replace_with(selected_menu.description)

        for tag in soup.find_all(id="res_logo"):
            if tag is not None:
                if store_data.brand_logo != None and store_data.brand_logo != "":
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                    )
                else:
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                    )

        for tag in soup.find_all(id="map"):
            if tag is not None:
                if store_data.location_url != None:
                    if "https" not in store_data.location_url:
                        tag["href"] = (
                            f"https://www.google.com/maps/place/{store_data.location_url}"
                        )
                    else:
                        tag["href"] = store_data.location_url

        for tag in soup.find_all(id="instagram"):
            if tag is not None:
                if store_data.instagram_address is not None:
                    if "instagram.com" in store_data.instagram_address:
                        tag["href"] = f"{store_data.instagram_address}"
                    else:
                        tag["href"] = (
                            f"https://instagram.com/{store_data.instagram_address}"
                        )

        for tag in soup.find_all(id="phone"):
            if tag is not None:
                tag["href"] = f"Tel:{store_data.telephone}"

        # Handle meta tags and redirect URL for smart templates
        for tag in soup.find_all(id="descript"):
            if tag is not None:
                tag["content"] = (
                    selected_menu.description
                    if selected_menu.description
                    else store_data.brand_name
                )

        for tag in soup.find_all(id="canon"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        for tag in soup.find_all(id="redirectUrl"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        new_text = soup.prettify()
    # Write new contents to test.html
    with open(f"../{menu_folder_name}/{file_name}.html", mode="w") as new_html_file:
        new_html_file.write(new_text)

    return {"success": True}


@router.post("/menu_preview/{menu_id}")
async def preview_a_menu(
    menu_id: int,
    theme: PublishMenu | None = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()
    all_menus_primary = (
        db.query(models.Menu).filter(models.Menu.store_id == user.get("id")).all()
    )
    store_data = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    all_menus = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"))
        .filter(models.Menu.id == menu_id)
        .first()
    )
    selected_menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    file_name = ""
    menu_folder_name = os.getenv("MENU_FOLDER_NAME")
    if selected_menu.is_sub_shop:
        shop_info = (
            db.query(models.Shops)
            .filter(models.Shops.id == selected_menu.shop_id)
            .first()
        )
        store_data = shop_info
        all_menus = (
            db.query(models.Menu)
            .filter(models.Menu.shop_id == shop_info.id)
            .filter(models.Menu.id == menu_id)
            .first()
        )
        all_menus_primary = (
            db.query(models.Menu).filter(models.Menu.shop_id == shop_info.id).all()
        )
        if shop_info.default_url is not None:
            if "https://" in shop_info.default_url:
                file_name = shop_info.default_url.split("/")[-1]
                menu_folder_name = shop_info.default_url.split("/")[-2]

            else:
                file_name = shop_info.default_url
        else:
            file_name = members.generate_random_value(7)
            shop_info.default_url = file_name
            db.add(shop_info)
            db.commit()

    else:
        if store_data.default_url is not None:
            if "https://" in store_data.default_url:
                file_name = store_data.default_url.split("/")[-1]
                menu_folder_name = store_data.default_url.split("/")[-2]

            else:
                file_name = store_data.default_url
        else:
            file_name = members.generate_random_value(7)
            store_data.default_url = file_name
            db.add(store_data)
            db.commit()
    menu_name = ""
    if selected_menu is not None:
        menu_name = selected_menu.title
        tmp_name = selected_menu.template_name
        if tmp_name == None or tmp_name == "":
            tmp_name = "custom"
        # type 1
        categoryObj = []
        foodObject = []
        categories = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.parent_id != 0)
            .filter(models.FoodCategory.menu_id == menu_id)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        parent_cats = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.parent_id == 0)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        all_menus.categories = categories
        saahel_subs = []
        for index, category in enumerate(categories):
            food = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == all_menus.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )
            print(f"Foods for category {category.id} - {category.title}: {food}")
            if "Dalia" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append({"category": category.title, "icon": cat_ig})
            elif "Dalia_v2" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append({"category": category.title, "icon": cat_ig})
            elif "Shabnam" in base_template_name:

                if category.parent_id != 0:
                    if category.parent_id != menu_id:
                        head_cat = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.id == category.parent_id)
                            .first()
                        )
                        categoryObj.append(
                            {
                                "category": category.title,
                                "id": category.id,
                                "parent_id": category.parent_id,
                                "position": category.position,
                                "parent_id_position": head_cat.position,
                            }
                        )
                    else:
                        all_heads = (
                            db.query(models.FoodCategory)
                            .filter(
                                models.FoodCategory.parent_id == 0,
                                models.FoodCategory.menu_id == menu_id,
                            )
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        if len(all_heads) > 0:
                            categoryObj.append(
                                {
                                    "category": category.title,
                                    "id": category.id,
                                    "parent_id": category.parent_id,
                                    "position": category.position,
                                    "parent_id_position": all_heads[-1].position + 1,
                                }
                            )
                        else:
                            categoryObj.append(
                                {
                                    "category": category.title,
                                    "id": category.id,
                                    "parent_id": category.parent_id,
                                    "position": category.position,
                                    "parent_id_position": 0,
                                }
                            )
            elif "Sorme" in base_template_name:
                if index == 0 and parent_cats:
                    for pr in parent_cats:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.parent_id == pr.id)
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        all_sub = []
                        for item in subs:
                            all_sub.append(item.title)
                        categoryObj.append(
                            {
                                "category": pr.title,
                                "id": pr.id,
                                "subCategory": all_sub,
                                "parent_id": pr.parent_id,
                            }
                        )
                if category.parent_is_menu:
                    subs = (
                        db.query(models.FoodCategory)
                        .filter(
                            models.FoodCategory.parent_id == category.id,
                            models.FoodCategory.menu_id != category.id,
                        )
                        .order_by(models.FoodCategory.position.asc())
                        .all()
                    )
                    all_sub = []
                    for item in subs:
                        all_sub.append(item.title)
                    categoryObj.append(
                        {
                            "category": category.title,
                            "id": category.id,
                            "subCategory": all_sub,
                            "parent_id": category.parent_id,
                        }
                    )
            elif "Yakh" in base_template_name:
                if category.parent_id != 0:
                    categoryObj.append(
                        {
                            "category": category.title,
                            "id": category.id,
                        }
                    )
            elif "shiraz" in base_template_name:
                if index == 0 and parent_cats:
                    for pr in parent_cats:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.parent_id == pr.id)
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        if subs:
                            for val in subs:
                                cat_ig = val.cat_image
                                if len(cat_ig) == 0:
                                    cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                                else:
                                    if "https://" in val.cat_image:
                                        cat_ig = val.cat_image
                                    else:
                                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                                saahel_subs.append(
                                    {
                                        "id": val.id,
                                        "category": pr.title,
                                        "subCategory": val.title,
                                        "icon": cat_ig,
                                    }
                                )
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                }
                            )

                subcats = (
                    db.query(models.FoodCategory)
                    .filter(
                        models.FoodCategory.parent_id == category.id,
                        models.FoodCategory.menu_id != category.id,
                    )
                    .all()
                )
                if subcats:
                    for val in subcats:
                        cat_ig = val.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in val.cat_image:
                                cat_ig = val.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                        saahel_subs.append(
                            {
                                "id": val.id,
                                "category": category.title,
                                "subCategory": val.title,
                                "icon": cat_ig,
                            }
                        )
                else:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    saahel_subs.append(
                        {
                            "id": category.id,
                            "category": category.title,
                            "subCategory": category.title,
                            "icon": cat_ig,
                        }
                    )
                # if category.parent_is_menu:
                if category.parent_is_menu == True:
                    categoryObj.append({"category": category.title, "id": category.id})

            elif "custom" in base_template_name:
                if index == 0 and parent_cats:
                    for pr in parent_cats:
                        categoryObj.append(
                            {
                                "category": pr.title,
                                "id": pr.id,
                                "parent_is_menu": pr.parent_is_menu,
                                "parent_id": pr.parent_id,
                            }
                        )
                categoryObj.append(
                    {
                        "category": category.title,
                        "id": category.id,
                        "parent_id": category.parent_id,
                        "parent_is_menu": category.parent_is_menu,
                    }
                )
            elif "zomorod" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append(
                        {"category": category.title, "icon": cat_ig, "id": category.id}
                    )
            elif "Zomorod" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append(
                        {"category": category.title, "icon": cat_ig, "id": category.id}
                    )
            elif "gerdoo" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append(
                        {"category": category.title, "icon": cat_ig, "id": category.id}
                    )

            elif "sepehr" in base_template_name:
                if index == 0 and parent_cats:
                    for pr in parent_cats:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.parent_id == pr.id)
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        all_sub = []
                        find_foods = (
                            db.query(models.Foods)
                            .filter(models.Foods.cat_id == pr.id)
                            .all()
                        )
                        for item in subs:
                            all_sub.append(item.title)
                        if len(all_sub) > 0 or len(find_foods) > 0:
                            categoryObj.append(
                                {
                                    "category": pr.title,
                                    "id": pr.id,
                                    "subCategory": all_sub,
                                    "parent_id": pr.parent_id,
                                }
                            )

                subcats = (
                    db.query(models.FoodCategory)
                    .filter(
                        models.FoodCategory.parent_id == category.id,
                        models.FoodCategory.menu_id != category.id,
                    )
                    .all()
                )
                if subcats:
                    for val in subcats:
                        cat_ig = val.cat_image
                        if category.parent_id == menu_id:
                            cat_val = "سایر"
                            sub_val = category.title
                        else:
                            main_cat = (
                                db.query(models.FoodCategory)
                                .filter(models.FoodCategory.id == category.parent_id)
                                .first()
                            )
                            cat_val = main_cat.title
                            sub_val = category.title
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in val.cat_image:
                                cat_ig = val.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{val.cat_image}'
                        saahel_subs.append(
                            {
                                "id": val.id,
                                "category": cat_val,
                                "subCategory": sub_val,
                                "icon": cat_ig,
                            }
                        )
                else:
                    cat_ig = category.cat_image
                    if category.parent_id == menu_id:
                        cat_val = "سایر"
                        sub_val = category.title
                    else:
                        main_cat = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.id == category.parent_id)
                            .first()
                        )
                        cat_val = main_cat.title
                        sub_val = category.title
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'

                    saahel_subs.append(
                        {
                            "id": category.id,
                            "category": cat_val,
                            "subCategory": sub_val,
                            "icon": cat_ig,
                        }
                    )

                if category.parent_is_menu:
                    if category.parent_id == menu_id:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(
                                models.FoodCategory.parent_id == menu_id,
                                models.FoodCategory.menu_id != category.id,
                            )
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        all_sub = []
                        for item in subs:
                            if item.title not in all_sub:
                                all_sub.append(item.title)
                        if len(all_sub) > 0:

                            resObj = {
                                "category": "سایر",
                                "id": 1,
                                "subCategory": all_sub,
                                "parent_id": 0,
                            }
                            if resObj not in categoryObj:
                                categoryObj.append(resObj)

            elif "cookie" in base_template_name:
                if category.parent_id != 0:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append(
                        {"text": category.title, "icon": cat_ig, "id": category.id}
                    )

            # sorme & ivaan
            elif "ivaan" in base_template_name:
                if index == 0 and parent_cats:
                    for pr in parent_cats:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.parent_id == pr.id)
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        all_sub = []
                        for item in subs:
                            all_sub.append(item.title)
                        categoryObj.append(
                            {
                                "category": pr.title,
                                "id": pr.id,
                                "subCategory": all_sub,
                            }
                        )
                subcats = (
                    db.query(models.FoodCategory)
                    .filter(
                        models.FoodCategory.parent_id == category.id,
                        models.FoodCategory.menu_id != category.id,
                    )
                    .all()
                )
                all_sub = []
                for val in subcats:
                    all_sub.append(val.title)
                category.subCategory = all_sub
                if category.parent_is_menu:
                    categoryObj.append(
                        {
                            "category": category.title,
                            "id": category.id,
                            "subCategory": all_sub,
                        }
                    )

            elif "saahel" in base_template_name:
                if index == 0 and parent_cats:
                    for pr in parent_cats:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.parent_id == pr.id)
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )
                        for val in subs:
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": pr.title,
                                    "subCategory": val.title,
                                    "icon": val.cat_image,
                                }
                            )
                        cat_ig = pr.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in pr.cat_image:
                                cat_ig = pr.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{pr.cat_image}'
                        categoryObj.append(
                            {
                                "category": pr.title,
                                "id": pr.id,
                                "parent_is_menu": val.parent_is_menu,
                                "parent_id": pr.parent_id,
                                "icon": cat_ig,
                            }
                        )
                subcats = (
                    db.query(models.FoodCategory)
                    .filter(
                        models.FoodCategory.parent_id == category.id,
                        models.FoodCategory.menu_id != category.id,
                    )
                    .all()
                )
                for val in subcats:
                    saahel_subs.append(
                        {
                            "id": val.id,
                            "category": category.title,
                            "subCategory": val.title,
                            "icon": val.cat_image,
                        }
                    )
                # if category.parent_is_menu:
                if category.parent_is_menu == True:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append(
                        {
                            "category": category.title,
                            "id": category.id,
                            "parent_id": category.parent_id,
                            "parent_is_menu": category.parent_is_menu,
                            "icon": cat_ig,
                        }
                    )
            elif "ghahve" in base_template_name:
                if index == 0 and parent_cats:
                    for pr in parent_cats:
                        subs = (
                            db.query(models.FoodCategory)
                            .filter(
                                models.FoodCategory.parent_id == pr.id,
                                models.FoodCategory.menu_id == menu_id,
                            )
                            .order_by(models.FoodCategory.position.asc())
                            .all()
                        )

                        for val in subs:
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": pr.title,
                                    "subCategory": val.title,
                                }
                            )
                        cat_ig = pr.cat_image
                        if len(cat_ig) == 0:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                        else:
                            if "https://" in pr.cat_image:
                                cat_ig = pr.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{pr.cat_image}'
                        categoryObj.append(
                            {"category": pr.title, "id": pr.id, "icon": cat_ig}
                        )
                subcats = (
                    db.query(models.FoodCategory)
                    .filter(
                        models.FoodCategory.parent_id == category.id,
                        models.FoodCategory.menu_id != category.id,
                    )
                    .all()
                )
                for val in subcats:
                    saahel_subs.append(
                        {
                            "id": val.id,
                            "category": category.title,
                            "subCategory": val.title,
                        }
                    )
                if category.parent_is_menu:
                    cat_ig = category.cat_image
                    if len(cat_ig) == 0:
                        cat_ig = f'{os.getenv("BASE_URL")}/category/images/defaults/CatIcon.svg'
                    else:
                        if "https://" in category.cat_image:
                            cat_ig = category.cat_image
                        else:
                            cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                    categoryObj.append(
                        {"category": category.title, "icon": cat_ig, "id": category.id}
                    )

        # type2
        categories = (
            db.query(models.FoodCategory)
            .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
            .filter(models.MenuIDS.menu_id == menu_id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        all_menus.categories = categories
        for category in categories:
            food = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == all_menus.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )

            category.text = category.title
            category.icon = category.cat_image
            subcats = (
                db.query(models.FoodCategory)
                .filter(
                    models.FoodCategory.parent_id == category.id,
                    models.FoodCategory.menu_id != category.id,
                )
                .all()
            )
            for foodObj in food:
                all_img = []
                for food in foodObj.food_image:
                    all_img.append(f'{os.getenv("BASE_URL")}/food/images/{food}')
                if len(all_img) == 0:
                    all_img.append(
                        f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                    )
                video_url = ""
                if foodObj.food_video != None and len(foodObj.food_video) > 0:
                    video_url = (
                        f'{os.getenv("BASE_URL")}/food/videos/{foodObj.food_video}'
                    )

                if "custom" in base_template_name:
                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "category": category.title,
                            "images": all_img,
                            "details": foodObj.description,
                            "price": foodObj.price,
                            "videoUrl": video_url,
                        }
                    )
                elif "Dalia" in base_template_name:
                    final_price = 0
                    if foodObj.price == "0":
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            final_price = list(foodObj.sizes)[0].get("price")
                    else:
                        final_price = foodObj.price
                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "category": category.title,
                            "images": all_img,
                            "details": foodObj.description,
                            "price": final_price,
                            "videoUrl": video_url,
                        }
                    )
                elif "Dalia_v2" in base_template_name:
                    final_price = 0
                    if foodObj.price == "0":
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            final_price = list(foodObj.sizes)[0].get("price")
                    else:
                        final_price = foodObj.price
                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "category": category.title,
                            "images": all_img,
                            "details": foodObj.description,
                            "price": final_price,
                            "videoUrl": video_url,
                        }
                    )
                elif "Shabnam" in base_template_name:
                    final_price = 0
                    if foodObj.price == "0":
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            final_price = list(foodObj.sizes)[0].get("price")
                    else:
                        final_price = foodObj.price
                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "englishTitle": foodObj.englishTitle,
                            "price": final_price,
                            "category": category.title,
                            "images": all_img,
                            "description": foodObj.description,
                            "videoUrl": video_url,
                        }
                    )
                elif "Sorme" in base_template_name:
                    final_price = 0
                    if foodObj.price == "0":
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            final_price = list(foodObj.sizes)[0].get("price")
                    else:
                        final_price = foodObj.price
                    cat_name = (
                        db.query(models.FoodCategory)
                        .filter(models.FoodCategory.id == foodObj.cat_id)
                        .first()
                    )

                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "englishTitle": foodObj.englishTitle,
                            "price": final_price,
                            "category": category.title,
                            "images": all_img,
                            "description": foodObj.description,
                            "videoUrl": video_url,
                            "subCategoryFood": cat_name.title,
                        }
                    )
                elif "Yakh" in base_template_name:
                    final_price = 0
                    if foodObj.price == "0":
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            final_price = list(foodObj.sizes)[0].get("price")
                    else:
                        final_price = foodObj.price
                    foodObject.append(
                        {
                            "id": foodObj.id,
                            "title": foodObj.title,
                            "englishTitle": foodObj.englishTitle,
                            "price": final_price,
                            "category": category.title,
                            "images": all_img,
                            "details": foodObj.description,
                            "videoUrl": video_url,
                        }
                    )
                elif "zomorod" in base_template_name:
                    food_image = ""
                    if len(foodObj.food_image) > 0:
                        food_image = f'{os.getenv("BASE_URL")}/food/images/{foodObj.food_image[0]}'
                    else:
                        food_image = f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "name": foodObj.title,
                                    "sizes": foodObj.sizes,
                                    "category": category.title,
                                    "image": food_image,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "name": foodObj.title,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "category": category.title,
                                    "image": food_image,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "name": foodObj.title,
                                "MainPrice": foodObj.price,
                                "sizes": None,
                                "category": category.title,
                                "image": food_image,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )
                elif "ivaan" in base_template_name:
                    cat_name = (
                        db.query(models.FoodCategory)
                        .filter(models.FoodCategory.id == foodObj.cat_id)
                        .first()
                    )
                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "sizes": foodObj.sizes,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "MainPrice": foodObj.price,
                                "sizes": None,
                                "subCategory": cat_name.title,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )

                elif "shiraz" in base_template_name:
                    cat_name = (
                        db.query(models.FoodCategory)
                        .filter(models.FoodCategory.id == foodObj.cat_id)
                        .first()
                    )
                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "sizes": foodObj.sizes,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "MainPrice": foodObj.price,
                                    "subCategory": cat_name.title,
                                    "sizes": [],
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "MainPrice": foodObj.price,
                                "subCategory": cat_name.title,
                                "sizes": [],
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )
                elif "ghahve" in base_template_name:
                    cat_name = (
                        db.query(models.FoodCategory)
                        .filter(models.FoodCategory.id == foodObj.cat_id)
                        .first()
                    )
                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "sizes": foodObj.sizes,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "MainPrice": foodObj.price,
                                    "subCategory": cat_name.title,
                                    "sizes": None,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "MainPrice": foodObj.price,
                                "subCategory": cat_name.title,
                                "sizes": None,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )
                elif "gerdoo" in base_template_name:
                    cat_name = (
                        db.query(models.FoodCategory)
                        .filter(models.FoodCategory.id == foodObj.cat_id)
                        .first()
                    )
                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "sizes": foodObj.sizes,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "MainPrice": foodObj.price,
                                "sizes": None,
                                "subCategory": cat_name.title,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )
                elif "sepehr" in base_template_name:
                    englishTitle = foodObj.englishTitle
                    cat_name = (
                        db.query(models.FoodCategory)
                        .filter(models.FoodCategory.id == foodObj.cat_id)
                        .first()
                    )
                    if foodObj.englishTitle == None:
                        englishTitle = ""
                    if category.parent_id == menu_id:
                        cat_val = "سایر"
                        sub_val = cat_name.title
                    else:
                        main_cat = (
                            db.query(models.FoodCategory)
                            .filter(models.FoodCategory.id == cat_name.parent_id)
                            .first()
                        )
                        cat_val = main_cat.title
                        sub_val = cat_name.title

                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]

                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": englishTitle,
                                    "sizes": foodObj.sizes,
                                    "category": cat_val,
                                    "subCategory": sub_val,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": englishTitle,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "category": cat_val,
                                    "subCategory": sub_val,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": englishTitle,
                                "MainPrice": foodObj.price,
                                "sizes": None,
                                "category": cat_val,
                                "subCategory": sub_val,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )
                elif "cookie" in base_template_name:
                    popup = None
                    all_imgs = None
                    if len(all_img) > 0:
                        all_imgs = all_img[0]
                        if len(all_img) > 1:
                            popup = all_img[1]
                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "sizes": foodObj.sizes,
                                    "category": category.title,
                                    "image": all_imgs,
                                    "popupBackground": popup,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "englishTitle": foodObj.englishTitle,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "category": category.title,
                                    "image": all_imgs,
                                    "popupBackground": popup,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "englishTitle": foodObj.englishTitle,
                                "MainPrice": foodObj.price,
                                "sizes": None,
                                "category": category.title,
                                "image": all_imgs,
                                "popupBackground": popup,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )
                elif "saahel" in base_template_name:
                    cat_name = (
                        db.query(models.FoodCategory)
                        .filter(models.FoodCategory.id == foodObj.cat_id)
                        .first()
                    )
                    if foodObj.sizes != None:
                        if len(foodObj.sizes) > 0:
                            foodObj.sizes = [
                                it
                                for it in foodObj.sizes
                                if it.get("status", 1) is not None
                                and it.get("status", 1) != 0
                            ]
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "sizes": foodObj.sizes,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                        else:
                            foodObject.append(
                                {
                                    "id": foodObj.id,
                                    "title": foodObj.title,
                                    "MainPrice": foodObj.price,
                                    "sizes": None,
                                    "subCategory": cat_name.title,
                                    "category": category.title,
                                    "images": all_img,
                                    "description": foodObj.description,
                                    "videoUrl": video_url,
                                }
                            )
                    else:
                        foodObject.append(
                            {
                                "id": foodObj.id,
                                "title": foodObj.title,
                                "MainPrice": foodObj.price,
                                "sizes": None,
                                "subCategory": cat_name.title,
                                "category": category.title,
                                "images": all_img,
                                "description": foodObj.description,
                                "videoUrl": video_url,
                            }
                        )

    else:
        raise HTTPException(
            status_code=403, detail="You should select a template from the list"
        )

    if "Shabnam" in base_template_name:
        categoryObj.sort(
            key=lambda x: (x.get("parent_id_position"), x.get("position")),
            reverse=False,
        )

    print("Final CategoryObj:", json.dumps(categoryObj, indent=2, ensure_ascii=False))
    print("Final FoodObject:", json.dumps(foodObject, indent=2, ensure_ascii=False))

    json_object = json.dumps(categoryObj, indent=4, ensure_ascii=False)
    food_object = json.dumps(foodObject, indent=4, ensure_ascii=False)

    # # Writing to js file
    if "saahel" in base_template_name:
        with open(
            f"../{menu_folder_name}/{file_name}_preview.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n const foods={food_object}\n"
                + "export {"
                + "categories,foods,subCategories};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "ghahve" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}_preview.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                + f'const background="{backg}"\n'
                + "export {"
                + "categories,foods,subCategories , background};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    elif "shiraz" in base_template_name:

        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}_preview.js", "w", encoding="utf-8"
        ) as outfile:
            if theme is not None and (
                theme.backgroundColor or theme.secondColor is not None
            ):
                back_obj = json.dumps(
                    {
                        "bodyColor": theme.backgroundColor,
                        "secondaryColor": theme.secondColor,
                    },
                    indent=4,
                    ensure_ascii=False,
                )
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                               const foods={food_object}\n"
                    + f'const background="{backg}"\n'
                    + f"const theme = {back_obj}\n"
                    + "export {"
                    + "categories,foods,subCategories , background , theme};"
                )
            else:
                outfile.write(
                    f"const categories = {json_object}\n const subCategories={saahel_subs}\n\
                                const foods={food_object}\n"
                    + f'const background="{backg}"\n const theme = null;\n'
                    + "export {"
                    + "categories,foods,subCategories , background , theme};"
                )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)

    elif "ivaan" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}_preview.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const foods={food_object}\n"
                + f'const background="{backg}"\n'
                + "export {"
                + "categories,foods,background};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)

    elif "sepehr" in base_template_name:
        backg = f'{os.getenv("BASE_URL")}/menu/images/{selected_menu.background_image}'
        with open(
            f"../{menu_folder_name}/{file_name}_preview.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const foods={food_object}\n"
                + f'const background="{backg}"\n'
                + "export {"
                + "categories,foods,background};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)

    else:

        with open(
            f"../../{menu_folder_name}/{file_name}_preview.js", "w", encoding="utf-8"
        ) as outfile:
            outfile.write(
                f"const categories = {json_object}\n const foods={food_object}\n"
                + "export {"
                + "categories,foods};"
            )
        if len(all_menus_primary) > 0:
            for menu in all_menus_primary:
                if menu.id == menu_id:
                    menu.is_primary = True
                else:
                    menu.is_primary = False
                db.add(menu)
    with open(f"../../{menu_folder_name}/{tmp_name.lower()}.html") as html_file:
        soup = BeautifulSoup(html_file.read(), features="html.parser")

        for tag in soup.find(id="menu_name"):
            tag.string.replace_with(menu_name)
        for tag in soup.find_all(id="restaurant_title"):
            tag.string.replace_with(store_data.brand_name)

        for tag in soup.find_all(id="food_desc"):
            if tag != None:
                tag.string = selected_menu.description

        for tag in soup.find_all(id="res_logo"):
            if tag is not None:
                if store_data.brand_logo != None and store_data.brand_logo != "":
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/members/images/{store_data.brand_logo}'
                    )
                else:
                    tag["src"] = (
                        f'{os.getenv("BASE_URL")}/category/images/defaults/default_logo.png'
                    )
        for tag in soup.find_all(id="map"):
            if tag is not None:
                if store_data.location_url != None:
                    if "https" not in store_data.location_url:
                        tag["href"] = (
                            f"https://www.google.com/maps/place/{store_data.location_url}"
                        )
                    else:
                        tag["href"] = store_data.location_url

        for tag in soup.find_all(id="instagram"):
            if tag is not None:
                if store_data.instagram_address is not None:
                    if "instagram.com" in store_data.instagram_address:
                        tag["href"] = f"{store_data.instagram_address}"
                    else:
                        tag["href"] = (
                            f"https://instagram.com/{store_data.instagram_address}"
                        )

        for tag in soup.find_all(id="phone"):
            if tag is not None:
                tag["href"] = f"Tel:{store_data.telephone}"

        # Handle meta tags and redirect URL for smart templates
        for tag in soup.find_all(id="descript"):
            if tag is not None:
                tag["content"] = (
                    selected_menu.description
                    if selected_menu.description
                    else store_data.brand_name
                )

        for tag in soup.find_all(id="canon"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        for tag in soup.find_all(id="redirectUrl"):
            if tag is not None:
                tag["href"] = f"https://{file_name}.rhinomenu.com"

        new_text = soup.prettify()

    # Write new contents to test.html
    with open(
        f"../../{menu_folder_name}/{file_name}_preview.html", mode="w"
    ) as new_html_file:
        new_html_file.write(new_text)
    db.commit()
    return {
        "success": True,
        "preview_url": f'{os.getenv("MENU_BASE_URL")}{file_name}_preview.html',
    }


@router.get("/get_all_menus")
async def get_user_all_menus(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    final_res = []
    if not user:
        raise get_user_exception()
    else:
        all_menu = (
            db.query(models.Menu)
            .filter(models.Menu.store_id == user.get("id"))
            .order_by(models.Menu.position.asc())
            .all()
        )
        if not all_menu:
            raise HTTPException(status_code=404, detail="Menu not found")

        for menu in all_menu:
            categories = (
                db.query(models.FoodCategory)
                .filter(models.FoodCategory.menu_id == menu.id)
                .order_by(models.FoodCategory.position.asc())
                .all()
            )
            if menu.multi_language_data:
                menu.multi_language_data = json.loads(menu.multi_language_data)
            menu.category = categories
            user_info = (
                db.query(models.Members)
                .filter(models.Members.id == user.get("id"))
                .first()
            )
            menu.custom_template = user_info.custom_template
            for category in categories:
                food = (
                    db.query(models.Foods)
                    .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                    .filter(
                        models.MenuIDS.menu_id == menu.id,
                        models.MenuIDS.cat_id == category.id,
                    )
                    .order_by(models.Foods.position.asc())
                    .all()
                )
                if category.multi_language_data:
                    category.multi_language_data = json.loads(
                        category.multi_language_data
                    )
                for foo in food:
                    if foo.multi_language_data:
                        if isinstance(foo.multi_language_data, (dict, list)):
                            foo.multi_language_data = foo.multi_language_data

                        # If it's a string, try to parse it
                        if isinstance(foo.multi_language_data, str):
                            try:
                                foo.multi_language_data = json.loads(
                                    foo.multi_language_data
                                )
                            except json.JSONDecodeError:
                                # Handle invalid JSON
                                pass

                category.foods = food

            if menu not in final_res:
                final_res.append(menu)

        return {"all_menu": final_res}


class CategoryInfo(BaseModel):
    id: int
    title: str
    parent_id: Optional[int] = None
    parent_is_menu: bool
    type: str = "category"
    children: List["Category"] = []


Category.update_forward_refs()


class ShowMenuInfo(BaseModel):
    id: int
    title: str
    type: str
    children: List[CategoryInfo] = []


@router.get("/v2/get_menu/{menu_id}", response_model=ShowMenuInfo)
async def get_user_specific_menu(
    menu_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    """
    Retrieve a specific menu with nested categories for an authenticated user.
    Only includes menu and category information with type field, excluding food items.

    Args:
        menu_id: The ID of the menu to retrieve
        user: Authenticated user data from dependency
        db: Database session from dependency

    Returns:
        Dict containing menu details and nested category structure with type field

    Raises:
        HTTPException: If user is not authenticated or menu is not found/accessible
    """
    if not user:
        raise get_user_exception()

    # Get the specific menu by ID and verify ownership
    menu = (
        db.query(models.Menu)
        .filter(models.Menu.id == menu_id, models.Menu.store_id == user.get("id"))
        .first()
    )

    if not menu:
        raise HTTPException(
            status_code=404, detail="Menu not found or you don't have access to it"
        )

    # Get all categories for this menu
    categories = (
        db.query(models.FoodCategory)
        .filter(models.FoodCategory.menu_id == menu_id)
        .all()
    )

    # Build nested category structure without food items
    nested_categories = build_nested_categories(
        categories=categories, db=db, menu_id=menu_id
    )

    # Create menu response object with type field
    menu_dict = {
        "id": menu.id,
        "title": menu.title,
        "type": "menu",  # Add type for menu
        "children": nested_categories,
    }

    return menu_dict


def build_nested_categories(
    categories: List[models.FoodCategory],
    parent_id: Optional[int] = None,
    db: Optional[Session] = None,
    menu_id: Optional[int] = None,
) -> List[Dict]:
    """
    Build a nested structure of categories with parent-child relationships.
    Adds a type field and explicitly excludes any food-related information.

    Args:
        categories: List of category objects from database
        parent_id: ID of the parent category (None for top-level categories)
        db: Database session (passed through for consistency, not used here)
        menu_id: ID of the menu to determine top-level relationship

    Returns:
        List of dictionaries representing nested category structure with type field
    """
    result = []

    for category in categories:
        if category.parent_id == parent_id:
            category_dict = {
                "id": category.id,
                "title": category.title,
                "type": "category",  # Add type for category
                "enabled": category.enabled,
                "position": category.position,
                "menu_id": category.menu_id,
                "parent_id": category.parent_id,
                "parent_is_menu": category.parent_id == menu_id,
                "children": build_nested_categories(
                    categories=categories, parent_id=category.id, db=db, menu_id=menu_id
                ),
            }
            result.append(category_dict)

    # Sort by position
    return sorted(result, key=lambda x: x.get("position", 0))


class SizeItem(BaseModel):
    id: str
    name: str
    size: Optional[str]
    price: Optional[float]
    status: Optional[int]
    url: Optional[str]


class LanguageData(BaseModel):
    language_id: str
    title: Optional[str]
    description: Optional[str]
    price: Optional[float]


class MenuItem(BaseModel):
    id: str
    title: str
    type: str
    description: Optional[str] = None
    discount: Optional[int] = None
    ready_by_time: Optional[int] = None
    image: Union[List[str], str] = []
    price: Optional[float] = None
    template_color: Optional[str] = None
    currency: Optional[str] = None
    show_price: Optional[bool] = None
    show_store_info: Optional[bool] = None
    is_primary: Optional[bool] = None
    available: Optional[bool] = None
    template_name: Optional[str] = None
    smart_template: Optional[bool] = None
    custom_template: Optional[str] = None
    position: Optional[int] = None
    children: List["MenuItem"] = []
    sizes: Optional[List[SizeItem]] = None
    languages: Optional[List[LanguageData]] = None


class MenuItemNews(BaseModel):
    id: str
    title: str
    type: str
    description: Optional[str] = None
    discount: Optional[int] = None
    ready_by_time: Optional[int] = None
    image: Union[List[str], str] = []
    price: Optional[float] = None
    template_color: Optional[str] = None
    currency: Optional[str] = None
    theme_url: Optional[str] = None
    show_price: Optional[bool] = None
    show_store_info: Optional[bool] = None
    is_primary: Optional[bool] = None
    available: Optional[bool] = None
    template_name: Optional[str] = None
    smart_template: Optional[bool] = None
    custom_template: Optional[str] = None
    sizes: Optional[List[SizeItem]] = None
    languages: Optional[List[LanguageData]] = None
    background_image: Optional[Union[List[str], str]] = []
    position: Optional[int] = None
    children: List["Category"] = []
    multi_language_data: Optional[List[LanguageData]] = None


def transform_menu_data(menu) -> MenuItemNews:
    if not isinstance(menu, dict):
        # Filter out SQLAlchemy internal attributes
        menu = {k: v for k, v in menu.__dict__.items() if not k.startswith("_sa_")}
    multi_language_data = menu.get("multi_language_data", {})
    if isinstance(multi_language_data, str):
        try:
            multi_language_data = json.loads(multi_language_data)
        except json.JSONDecodeError:
            multi_language_data = {}
    return MenuItemNews(
        type="menu",
        id=str(menu.get("id")),
        title=menu.get("title", ""),
        description=menu.get("description"),
        is_primary=menu.get("is_primary"),
        currency=menu.get("currency"),
        show_price=menu.get("show_price"),
        show_store_info=menu.get("show_store_info"),
        template_name=menu.get("template_name"),
        theme_url=menu.get("theme_url"),
        template_color=menu.get("template_color"),
        customizable_background=menu.get("customizable_background", False),
        smart_template=menu.get("smart_template"),
        background_image=menu.get("background_image", []),
        position=menu.get("position"),
        children=[
            transform_category_data(category) for category in menu.get("category", [])
        ],
        multi_language_data=transform_language_data(multi_language_data),
    )


def transform_category_data(category: dict) -> Category:
    # Handle multi_language_data
    multi_language_data = category.get("multi_language_data", [])
    if isinstance(multi_language_data, str):
        try:
            multi_language_data = json.loads(multi_language_data)
        except json.JSONDecodeError:
            multi_language_data = []

    # Transform language data to MultiLanguage
    transformed_language_data = []
    language_data_list = transform_language_data(multi_language_data)
    if language_data_list:
        transformed_language_data = [
            MultiLanguage(
                language_id=lang.language_id,
                title=lang.title,
                description=lang.description,
            )
            for lang in language_data_list
        ]

    # Transform children (categories or foods)
    children = []
    for child in category.get("children", []) or category.get("foods", []):
        if "children" in child or "foods" in child:
            children.append(transform_category_data(child))
        else:
            children.append(transform_food_data(child))

    cat_image = category.get("cat_image")
    if isinstance(cat_image, str) and not cat_image.strip():
        cat_image = None

    return Category(
        type="category",
        id=str(category.get("id")),
        title=category.get("title", ""),
        description=category.get("description", ""),
        cat_image=cat_image,
        parent_id=category.get("parent_id"),
        parent_is_menu=category.get("parent_is_menu", False),  # Include required field
        menu_id=category.get("menu_id", 0),  # Include required field
        enabled=category.get("enabled"),
        multi_language_data=(
            transformed_language_data if transformed_language_data else None
        ),
        children=children,
    )


def transform_food_data(food: dict) -> Food:
    multi_language_data = food.get("multi_language_data", [])
    if isinstance(multi_language_data, str):
        try:
            multi_language_data = json.loads(multi_language_data)
        except json.JSONDecodeError:
            multi_language_data = []

    transformed_language_data = (
        [
            MultiLanguage(
                language_id=str(item.get("language_id", item.get("language", ""))),
                title=item.get("title"),
                price=item.get("price"),
                description=item.get("description"),
            )
            for item in multi_language_data
        ]
        if multi_language_data
        else None
    )

    food_image = food.get("food_image", [])
    if isinstance(food_image, str):
        try:
            food_image = json.loads(food_image)
        except json.JSONDecodeError:
            food_image = [food_image] if food_image else []

    sizes = food.get("sizes", [])
    if isinstance(sizes, str):
        try:
            sizes = json.loads(sizes)
        except json.JSONDecodeError:
            sizes = []
    return Food(
        type="food",
        id=str(food.get("id")),
        menu_id=food.get("menu_id", 0),
        category_id=food.get("cat_id", 0),
        title=food.get("title", ""),
        englishTitle=food.get("englishTitle", ""),
        price=food.get("price", 0),
        food_image=food_image,
        food_video=food.get("food_video", ""),
        description=food.get("description", ""),
        discount=food.get("discount"),
        ready_by_time=food.get("ready_by_time"),
        available=food.get("available"),
        sizes=sizes,
        multi_language_data=transformed_language_data,
    )


def transform_size_data(size: dict) -> SizeItem:
    return SizeItem(
        id=str(size.get("id")),
        name=size.get("title", ""),
        size=size.get("size"),
        price=float(size.get("price")) if size.get("price") else None,
        status=size.get("status"),
        url=size.get("url"),
    )


def transform_language_data(languages: Optional[dict]) -> Optional[List[LanguageData]]:
    if not languages:
        return None

    if isinstance(languages, list):
        return [
            LanguageData(
                language_id=str(lang.get("language_id", "")),
                title=lang.get("title"),
                description=lang.get("description"),
                price=float(lang.get("price")) if lang.get("price") else None,
            )
            for lang in languages
        ]

    if isinstance(languages, dict):
        return [
            LanguageData(
                language_id=str(lang_id),
                title=data.get("title"),
                description=data.get("description"),
                price=float(data.get("price")) if data.get("price") else None,
            )
            for lang_id, data in languages.items()
        ]

    return None


@router.get("/items/menu/{id}", response_model=Menu)
async def get_menu_detail(
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific menu by ID.

    Returns detailed information about a menu including its configuration,
    template settings, and basic properties. This endpoint is specifically
    designed for menu objects and excludes irrelevant fields like price or size.

    Args:
        id: The unique identifier of the menu
        user: Authenticated user information
        db: Database session

    Returns:
        Menu: Complete menu information with proper structure

    Raises:
        HTTPException: 401 if user is not authenticated
        HTTPException: 404 if menu is not found or doesn't belong to user
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    menu = (
        db.query(models.Menu)
        .filter(models.Menu.id == id, models.Menu.store_id == user.get("id"))
        .first()
    )

    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    return transform_menu_data(menu.__dict__)


@router.get("/items/category/{id}", response_model=Category)
async def get_category_detail(
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific category by ID.

    Returns detailed information about a category including its properties,
    multi-language data, and hierarchical structure. This endpoint is specifically
    designed for category objects.

    Args:
        id: The unique identifier of the category
        user: Authenticated user information
        db: Database session

    Returns:
        Category: Complete category information with proper structure

    Raises:
        HTTPException: 401 if user is not authenticated
        HTTPException: 404 if category is not found or doesn't belong to user
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    category = (
        db.query(models.FoodCategory)
        .filter(
            models.FoodCategory.id == id,
            models.FoodCategory.store_id == user.get("id"),
        )
        .first()
    )

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return transform_category_data(category.__dict__)


@router.get("/items/food/{id}", response_model=Food)
async def get_food_detail(
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific food item by ID.

    Returns detailed information about a food item including its properties,
    pricing, sizes, images, and multi-language data. This endpoint is specifically
    designed for food objects and includes all relevant food-specific fields.

    Args:
        id: The unique identifier of the food item
        user: Authenticated user information
        db: Database session

    Returns:
        Food: Complete food information with proper structure

    Raises:
        HTTPException: 401 if user is not authenticated
        HTTPException: 404 if food item is not found or doesn't belong to user
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    food = (
        db.query(models.Foods)
        .filter(models.Foods.id == id, models.Foods.store_id == user.get("id"))
        .first()
    )

    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    # Get the category to determine menu_id
    find_cat = (
        db.query(models.FoodCategory)
        .filter(models.FoodCategory.id == food.cat_id)
        .first()
    )

    if find_cat:
        food.menu_id = find_cat.menu_id

    return transform_food_data(food.__dict__)


# Legacy endpoint - keeping for backward compatibility but marking as deprecated
@router.get("/items/{type}/{id}", response_model=MenuItemResponse, deprecated=True)
async def get_item_detail(
    type: MenuItemType,
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    DEPRECATED: Use specific endpoints instead.

    This endpoint is deprecated. Please use the following specific endpoints:
    - GET /menu/items/menu/{id} for menu items
    - GET /menu/items/category/{id} for category items
    - GET /menu/items/food/{id} for food items

    The dynamic type-based approach has been replaced with dedicated endpoints
    for better clarity, maintainability, and type safety.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    item = None
    if type == MenuItemType.MENU:
        item = (
            db.query(models.Menu)
            .filter(models.Menu.id == id, models.Menu.store_id == user.get("id"))
            .first()
        )
        if item:
            return transform_menu_data(item.__dict__)

    elif type == MenuItemType.CATEGORY:
        item = (
            db.query(models.FoodCategory)
            .filter(
                models.FoodCategory.id == id,
                models.FoodCategory.store_id == user.get("id"),
            )
            .first()
        )
        if item:
            return transform_category_data(item.__dict__)

    elif type == MenuItemType.FOOD:
        item = (
            db.query(models.Foods)
            .filter(models.Foods.id == id, models.Foods.store_id == user.get("id"))
            .first()
        )
        if item:
            find_cat = (
                db.query(models.FoodCategory)
                .filter(models.FoodCategory.id == item.cat_id)
                .first()
            )
            item.menu_id = find_cat.menu_id
            return transform_food_data(item.__dict__)

    if not item:
        raise HTTPException(status_code=404, detail=f"{type} not found")


@router.get("/store-details/{unique_name}")
async def get_store_details(
    request: Request, unique_name: str, db: Session = Depends(get_db)
) -> Dict:
    # Extract the host from headers
    store = (
        db.query(models.Members)
        .filter(models.Members.default_url == unique_name)
        .first()
    )
    if not store:
        raise HTTPException(
            status_code=404, detail=f"No store found for URL: {unique_name}"
        )

    # Get primary menu for the store (if exists)
    menu = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == store.id, models.Menu.is_primary == True)
        .first()
    )

    # Get banners for the store
    banners = (
        db.query(models.ClientBanner)
        .filter(models.ClientBanner.store_id == store.id)
        .all()
    )

    # Prepare response with requested fields
    response = {
        "store_details": {
            "background_image": menu.background_image if menu else None,
            "default_wait_time": store.public_wait_time,
            "menu_title": menu.title if menu else None,
            "logo": store.brand_logo,
            "owner_name": store.user_name,
            "brand_name": store.brand_name,
            "menu_name": menu.title if menu else None,
            "menu_description": menu.description if menu else store.default_description,
            "landing_link": store.profile_url,
            "address": store.address,
            "location_url": store.location_url,
            "instagram_link": store.instagram_address,
            "reservation_phone": store.telephone,
            "template_name": menu.template_name if menu else store.custom_template,
            "template_color": menu.template_color if menu else None,
            "call_to_action": store.call_order,
            "online_order": store.online_order,
            "payment_gateway": store.payment_gateway,
            "languages": store.language_currencies if store.language_currencies else [],
            "menu_counter": store.menu_counter,
            "multi_language": store.multi_language_currency,
            "banners": [
                {"link": banner.link, "image": banner.image_path} for banner in banners
            ],
            "customer_club": store.import_contact,
        }
    }

    return response


from sqlalchemy.orm import joinedload


@router.get("/menu-structure/{unique_name}")
async def get_menu_structure(
    request: Request, unique_name: str, db: Session = Depends(get_db)
) -> Dict:
    from sqlalchemy.orm import joinedload

    # Step 1: Identify store/shop by unique_name
    store_record = (
        db.query(models.Members)
        .filter(
            or_(
                models.Members.default_url == unique_name,
                models.Members.unique_name == unique_name,
            )
        )
        .first()
    )

    shop_record = (
        db.query(models.Shops)
        .filter(
            or_(
                models.Shops.default_url == unique_name,
                models.Shops.unique_name == unique_name,
            )
        )
        .first()
    )

    if store_record and shop_record:
        raise HTTPException(
            status_code=409, detail="Conflict: Found in both store and shop"
        )

    if not store_record and not shop_record:
        raise HTTPException(status_code=404, detail="Store/shop not found")

    if store_record:
        store_id = store_record.id
        store_data = store_record
    else:
        store_id = shop_record.store_id
        store_data = (
            db.query(models.Members).filter(models.Members.id == store_id).first()
        )

    # Step 2: Find primary menu
    menu = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == store_id, models.Menu.is_primary == True)
        .first()
    )

    if not menu:
        raise HTTPException(status_code=404, detail="No primary menu found")

    menu_id = menu.id

    # Step 3: Fetch top-level categories (where parent_is_menu == True)
    categories = (
        db.query(models.FoodCategory)
        .filter(
            models.FoodCategory.menu_id == menu_id,
            models.FoodCategory.store_id == store_id,
            models.FoodCategory.parent_is_menu == True,
        )
        .all()
    )

    category_ids = [cat.id for cat in categories]

    # Step 4: Fetch subcategories (where parent_id in category_ids)
    subcategories = (
        db.query(models.FoodCategory)
        .filter(
            models.FoodCategory.menu_id == menu_id,
            models.FoodCategory.store_id == store_id,
            models.FoodCategory.parent_id.in_(category_ids),
        )
        .all()
    )

    # Step 5: Parse multilanguage
    def parse_multilang(item, default_title):
        fa = en = default_title or ""
        data = item.multi_language_data
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                data = []
        if isinstance(data, list):
            for lang in data:
                if lang.get("language_id") in ["fa", "fa-ir"]:
                    fa = lang.get("title", fa)
                elif lang.get("language_id") == "en":
                    en = lang.get("title", en)
        return {"fa": fa, "en": en}

    # Step 6: Build category & subcategory list
    category_list = [
        {"id": cat.id, "name": parse_multilang(cat, cat.title)} for cat in categories
    ]

    subcategory_list = [
        {"id": sub.id, "name": parse_multilang(sub, sub.title), "catId": sub.parent_id}
        for sub in subcategories
    ]

    # Step 7: Fetch foods linked to subcategories
    subcat_ids = [sub.id for sub in subcategories]
    foods = (
        db.query(models.Foods)
        .options(joinedload(models.Foods.food_labels))
        .filter(models.Foods.store_id == store_id, models.Foods.cat_id.in_(subcat_ids))
        .all()
    )

    # Step 8: Build food list
    food_list = []
    for food in foods:
        name = parse_multilang(food, food.title)
        desc = parse_multilang(food, food.description or "")
        try:
            images = json.loads(food.food_image) if food.food_image else []
            if isinstance(images, str):  # fallback
                images = [images]
        except Exception:
            images = []

        labels = (
            [lbl.label_id_rel.title for lbl in food.food_labels if lbl.label_id_rel]
            if food.food_labels
            else []
        )

        food_list.append(
            {
                "id": food.id,
                "name": name,
                "description": desc,
                "tags": [],
                "images": images,
                "videos": [food.food_video] if food.food_video else [],
                "wait_time": food.ready_by_time or store_data.public_wait_time,
                "labels": labels,
                "subCategoryId": food.cat_id,
                "price": food.price,
                "sizes": food.sizes,
                "discount": food.discount,
            }
        )

    # Step 9: Debug logs
    print("✅ Store ID:", store_id)
    print("✅ Menu ID:", menu_id)
    print("✅ Categories:", len(category_list))
    print("✅ Subcategories:", len(subcategory_list))
    print("✅ Foods:", len(food_list))

    # Step 10: Return structured response
    return {
        "categories": category_list,
        "subCategories": subcategory_list,
        "foods": food_list,
    }


# @router.get("/menu-structure/{unique_name}")
# async def get_menu_structure(
#     request: Request, unique_name: str, db: Session = Depends(get_db)
# ) -> Dict:
#     # Step 1: Find the store_id using unique_name (check both default_url and unique_name fields)
#     # Check in stores table first
#     store_record = db.query(models.Members).filter(
#         or_(models.Members.default_url == unique_name, models.Members.unique_name == unique_name)
#     ).first()
#     shop_record = db.query(models.Shops).filter(
#         or_(models.Shops.default_url == unique_name, models.Shops.unique_name == unique_name)
#     ).first()

#     store_id = None
#     store_data = None

#     if store_record and shop_record:
#         raise HTTPException(status_code=409, detail="Conflict: unique_name exists in both store and shop tables")

#     if not store_record and not shop_record:
#         raise HTTPException(status_code=404, detail=f"No store or shop found for unique_name: {unique_name}")

#     # Step 2: Get the store_id from whichever table has the record
#     if store_record:
#         store_id = store_record.id
#         store_data = store_record
#     elif shop_record:
#         store_id = shop_record.store_id
#         # Get the actual store data from Members table
#         store_data = db.query(models.Members).filter(models.Members.id == store_id).first()
#         if not store_data:
#             raise HTTPException(status_code=404, detail="Store referenced by shop not found")

#     # Step 3: Find the menu_id using store_id where is_primary = 1
#     menu = (
#         db.query(models.Menu)
#         .filter(models.Menu.store_id == store_id, models.Menu.is_primary == True)
#         .first()
#     )
#     if not menu:
#         raise HTTPException(status_code=404, detail="No primary menu found for this store")

#     menu_id = menu.id

#     # Step 4: Build the menu structure using the found store_id and menu_id

#     # Categories (top-level) - where parent_id equals menu_id
#     categories = (
#         db.query(models.FoodCategory)
#         .filter(
#             models.FoodCategory.store_id == store_id,
#             models.FoodCategory.parent_id == menu_id,
#             models.FoodCategory.menu_id == menu_id,
#         )
#         .all()
#     )

#     category_list = []
#     for cat in categories:
#         multi_language_data = cat.multi_language_data
#         if isinstance(multi_language_data, str):
#             try:
#                 multi_language_data = json.loads(multi_language_data)
#             except json.JSONDecodeError:
#                 multi_language_data = []
#         if not isinstance(multi_language_data, (dict, list)):
#             multi_language_data = []

#         fa_title = cat.title
#         en_title = cat.title
#         if isinstance(multi_language_data, list):
#             for lang in multi_language_data:
#                 if lang.get("language_id") in ("fa", "fa-ir"):
#                     fa_title = lang.get("title", cat.title)
#                 if lang.get("language_id") == "en":
#                     en_title = lang.get("title", cat.title)

#         category_list.append({
#             "id": cat.id,
#             "name": {"fa": fa_title, "en": en_title}
#         })

#     # Subcategories (where parent_id is a category ID, not menu_id)
#     subcategories = (
#         db.query(models.FoodCategory)
#         .filter(
#             models.FoodCategory.store_id == store_id,
#             models.FoodCategory.parent_id != menu_id,  # Not directly under menu
#             models.FoodCategory.parent_id != None,     # Has a parent
#             models.FoodCategory.menu_id == menu_id,
#         )
#         .all()
#     )

#     subcategory_list = []
#     subcategory_ids = []  # Keep track of valid subcategory IDs
#     for subcat in subcategories:
#         subcategory_ids.append(subcat.id)  # Store the subcategory ID

#         multi_language_data = subcat.multi_language_data
#         if isinstance(multi_language_data, str):
#             try:
#                 multi_language_data = json.loads(multi_language_data)
#             except json.JSONDecodeError:
#                 multi_language_data = []
#         if not isinstance(multi_language_data, (dict, list)):
#             multi_language_data = []

#         fa_title = subcat.title
#         en_title = subcat.title
#         if isinstance(multi_language_data, list):
#             for lang in multi_language_data:
#                 if lang.get("language_id") in ("fa", "fa-ir"):
#                     fa_title = lang.get("title", subcat.title)
#                 if lang.get("language_id") == "en":
#                     en_title = lang.get("title", subcat.title)

#         subcategory_list.append({
#             "id": subcat.id,
#             "name": {"fa": fa_title, "en": en_title},
#             "catId": subcat.parent_id,
#         })

#     # Foods - FIXED: Only get foods that belong to valid subcategories
#     foods = (
#         db.query(models.Foods)
#         .filter(
#             models.Foods.store_id == store_id,
#             models.Foods.cat_id.in_(subcategory_ids)  # Only foods in valid subcategories
#         )
#         .all()
#     )

#     food_list = []
#     for food in foods:
#         multi_language_data = food.multi_language_data
#         if isinstance(multi_language_data, str):
#             try:
#                 multi_language_data = json.loads(multi_language_data)
#             except json.JSONDecodeError:
#                 multi_language_data = []
#         if not isinstance(multi_language_data, (dict, list)):
#             multi_language_data = []

#         fa_title = food.title
#         en_title = food.englishTitle
#         fa_desc = food.description
#         en_desc = food.description
#         if isinstance(multi_language_data, list):
#             for lang in multi_language_data:
#                 if lang.get("language_id") in ("fa", "fa-ir"):
#                     fa_title = lang.get("title", food.title)
#                     fa_desc = lang.get("description", food.description)
#                 if lang.get("language_id") == "en":
#                     en_title = lang.get("title", food.englishTitle)
#                     en_desc = lang.get("description", food.description)

#         food_image = food.food_image
#         if isinstance(food_image, str):
#             try:
#                 food_image = json.loads(food_image)
#             except json.JSONDecodeError:
#                 food_image = [food_image] if food_image else []

#         food_list.append(
#             {
#                 "id": food.id,
#                 "name": {"fa": fa_title, "en": en_title},
#                 "description": {"fa": fa_desc, "en": en_desc},
#                 "tags": [],
#                 "images": food_image if food_image else [],
#                 "videos": [food.food_video] if food.food_video else [],
#                 "wait_time": (
#                     food.ready_by_time if food.ready_by_time else store_data.public_wait_time
#                 ),
#                 "labels": (
#                     [label.title for label in food.food_labels]
#                     if food.food_labels
#                     else []
#                 ),
#                 "subCategoryId": food.cat_id,
#             }
#         )

#     # Prepare response
#     response = {
#         "categories": category_list,
#         "subCategories": subcategory_list,
#         "foods": food_list,
#     }

#     return response


@router.get("/categories/{category_id}", response_model=MenuItem)
async def get_category_with_subcategories_and_foods(
    category_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Fetch the parent category
    category = (
        db.query(models.FoodCategory)
        .filter(
            models.FoodCategory.id == category_id,
            models.FoodCategory.store_id == user.get("id"),
        )
        .first()
    )

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Transform and include subcategories and foods
    return transform_category_data(category.__dict__, include_children=True, db=db)


@router.delete("/items/{type}/{id}")
async def delete_item(
    type: MenuItemType,
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()

    item = None
    if type == MenuItemType.MENU:
        item = (
            db.query(models.Menu)
            .filter(models.Menu.id == id, models.Menu.store_id == user.get("id"))
            .first()
        )
    elif type == MenuItemType.CATEGORY:
        item = (
            db.query(models.FoodCategory)
            .filter(
                models.FoodCategory.id == id,
                models.FoodCategory.store_id == user.get("id"),
            )
            .first()
        )
    elif type == MenuItemType.FOOD:
        item = (
            db.query(models.Foods)
            .filter(models.Foods.id == id, models.Foods.store_id == user.get("id"))
            .first()
        )

    if not item:
        raise HTTPException(status_code=404, detail=f"{type} not found")

    db.delete(item)
    db.commit()
    return {"message": f"{type} deleted successfully"}


@router.patch("/items/{type}/{id}", response_model=MenuItemResponse)
async def update_item(
    type: MenuItemType,
    id: int,
    item_update: MenuItem,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()

    # Query the existing item
    item = None
    store_id = user.get("id")

    # More explicit querying with better error handling
    try:
        if type == MenuItemType.MENU:
            item = (
                db.query(models.Menu)
                .filter(models.Menu.id == id, models.Menu.store_id == store_id)
                .first()
            )
        elif type == MenuItemType.CATEGORY:
            item = (
                db.query(models.FoodCategory)
                .filter(
                    models.FoodCategory.id == id,
                    models.FoodCategory.store_id == store_id,
                )
                .first()
            )
        elif type == MenuItemType.FOOD:
            item = (
                db.query(models.Foods)
                .filter(models.Foods.id == id, models.Foods.store_id == store_id)
                .first()
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid item type")
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database query failed")

    if not item:
        raise HTTPException(status_code=404, detail=f"{type} with ID {id} not found")

    # Get the update data (only fields explicitly provided in the request)
    # Force exclude_unset to ensure we only update provided fields
    update_data = item_update.dict(exclude_unset=True, exclude_none=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid update data provided")

    # Apply updates to the database item
    for key, value in update_data.items():
        if hasattr(item, key):
            current_value = getattr(item, key)
            setattr(item, key, value)
        else:
            print(f"Warning: Field '{key}' not found in {type} model")

    try:
        # Explicitly mark as modified
        db.add(item)
        db.commit()
        db.refresh(item)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update: {str(e)}")

    # Return the actual database item after update, not merged data
    if type == MenuItemType.MENU:
        return transform_menu_data(item.__dict__)
    elif type == MenuItemType.CATEGORY:
        return transform_category_data(item.__dict__)
    else:
        return transform_food_data(item.__dict__)


@router.get("/banner/{image_path:path}")
async def get_banner_image(image_path: str):
    file_path = os.path.join(os.getcwd(), "client_banner", image_path)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Image not found")

    content_type, _ = mimetypes.guess_type(file_path)

    return FileResponse(
        file_path, media_type=content_type, filename=os.path.basename(file_path)
    )


@router.post("/upload_banner")
async def upload_banner(
    link: str = Form(...),
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()

    banner_dir = os.path.join(os.getcwd(), "client_banner")
    if not os.path.exists(banner_dir):
        os.makedirs(banner_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_ext = os.path.splitext(image.filename)[1]
    filename = f"banner_{user.get('id')}_{timestamp}{file_ext}"

    # Save image
    file_path = os.path.join(banner_dir, filename)
    with open(file_path, "wb+") as file_object:
        file_object.write(await image.read())

    # Save to database
    new_banner = models.ClientBanner(
        store_id=user.get("id"), image_path=f"/{filename}", link=link
    )

    db.add(new_banner)
    db.commit()
    db.refresh(new_banner)

    return {
        "status": "success",
        "message": "Banner uploaded successfully",
        "data": {
            "id": new_banner.id,
            "image_path": new_banner.image_path,
            "link": new_banner.link,
        },
    }


@router.get("/all_banners")
async def get_all_banners(
    user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user:
        raise get_user_exception()

    get_banners = (
        db.query(models.ClientBanner)
        .filter(models.ClientBanner.store_id == user.get("id"))
        .all()
    )
    return get_banners


@router.post("/drag_menu_position")
async def change_menu_position(
    cat_info: DragMenu,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()
    for i, food_item in enumerate(cat_info.menu_id):
        food = db.query(models.Menu).filter(models.Menu.id == food_item).first()
        food.position = i
        db.add(food)
    db.commit()
    all_menu = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"))
        .order_by(models.Menu.position.asc())
        .all()
    )
    if not all_menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    for menu in all_menu:
        categories = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.menu_id == menu.id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        menu.category = categories
        for category in categories:
            food = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == menu.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )

            category.foods = food

    return {"success": True, "all_menus": all_menu}


@router.post("/price_management")
async def set_price_management(
    priceData: PriceManager,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user:
        raise get_user_exception()

    user_detail = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    access_detail = (
        db.query(models.AccessType)
        .filter(models.AccessType.id == user_detail.access_type)
        .first()
    )

    if not access_detail.price_control:
        raise HTTPException(
            status_code=403, detail="You don't have access to this part"
        )

    menu = (
        db.query(models.Menu)
        .filter(models.Menu.id == priceData.menu_id)
        .filter(models.Menu.store_id == user.get("id"))
        .first()
    )

    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    menu.fix_price = priceData.fix_price
    menu.percent_price = priceData.percent_price

    for category_id in priceData.categories:
        all_foods = (
            db.query(models.Foods).filter(models.Foods.cat_id == category_id).all()
        )

        for foodInfo in all_foods:
            # Update main price if exists
            if foodInfo.price and int(foodInfo.price) > 0:
                if priceData.fix_price is not None:
                    foodInfo.price = str(
                        int(float(foodInfo.price)) + priceData.fix_price
                    )
                else:
                    percent_value = int(float(foodInfo.price)) * (
                        priceData.percent_price / 100
                    )
                    foodInfo.price = str(
                        int(float(foodInfo.price)) + int(percent_value)
                    )

            if foodInfo.multi_language_data:
                multi_data = foodInfo.multi_language_data
                if isinstance(multi_data, str):
                    try:
                        multi_data = json.loads(multi_data)
                    except json.JSONDecodeError:
                        continue

                if isinstance(multi_data, list):
                    for lang_item in multi_data:
                        # Update main price in language item
                        if (
                            isinstance(lang_item, dict)
                            and "price" in lang_item
                            and float(lang_item["price"]) > 0
                        ):
                            current_price = int(float(lang_item["price"]))
                            new_price = 0
                            if priceData.fix_price is not None:
                                new_price = current_price + priceData.fix_price
                            else:
                                percent_value = current_price * (
                                    priceData.percent_price / 100
                                )
                                new_price = current_price + int(percent_value)
                            lang_item["price"] = str(new_price)

                        # Update prices in sizes within language item
                        if "sizes" in lang_item and isinstance(
                            lang_item["sizes"], list
                        ):
                            for size in lang_item["sizes"]:
                                if (
                                    isinstance(size, dict)
                                    and "price" in size
                                    and float(size["price"]) > 0
                                ):
                                    current_price = int(float(size["price"]))
                                    new_price = 0
                                    if priceData.fix_price is not None:
                                        new_price = current_price + priceData.fix_price
                                    else:
                                        percent_value = current_price * (
                                            priceData.percent_price / 100
                                        )
                                        new_price = current_price + int(percent_value)
                                    size["price"] = str(new_price)

                    foodInfo.multi_language_data = json.dumps(multi_data)
                    flag_modified(foodInfo, "multi_language_data")

            # Update prices in sizes if they exist
            if foodInfo.sizes:
                sizes_data = foodInfo.sizes
                if isinstance(sizes_data, list):
                    for size in sizes_data:
                        if isinstance(size, dict) and "price" in size:
                            current_price = int(float(size["price"]))
                            if priceData.fix_price is not None:
                                size["price"] = str(current_price + priceData.fix_price)
                            else:
                                percent_value = current_price * (
                                    priceData.percent_price / 100
                                )
                                size["price"] = str(current_price + int(percent_value))
                    foodInfo.sizes = sizes_data
                    flag_modified(foodInfo, "sizes")

            db.add(foodInfo)

    db.add(menu)
    try:
        db.commit()
        return {"success": True}

    except Exception as ex:
        if isinstance(ex, HTTPException):
            raise ex
        raise HTTPException(status_code=403, detail=str(ex))


# get menu_id and return related => menu, categories, foods
@router.get("/menu_items/{menu_id}")
async def get_menu_items(
    menu_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user:
        raise get_user_exception()

    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    categories = (
        db.query(models.FoodCategory)
        .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
        .filter(models.MenuIDS.menu_id == menu_id)
        .all()
    )

    for category in categories:
        food = (
            db.query(models.Foods)
            .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
            .filter(
                models.MenuIDS.menu_id == menu_id, models.MenuIDS.cat_id == category.id
            )
            .all()
        )

        category.foods = food
    return {"menu": menu}


@router.delete("/{menu_id}")
async def delete_a_menu(
    menu_id: int, user: dict = Depends(get_current_user), db: Session = Depends(get_db)
):
    if not user:
        raise get_user_exception()

        # Retrieve the menu by menu_id
    menu = db.query(models.Menu).filter(models.Menu.id == menu_id).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    # Retrieve all categories related to the menu
    categories = (
        db.query(models.FoodCategory)
        .join(models.MenuIDS, models.MenuIDS.cat_id == models.FoodCategory.id)
        .filter(models.MenuIDS.menu_id == menu_id)
        .all()
    )

    # For each category, retrieve and delete all foods related to the category
    for category in categories:
        foods = (
            db.query(models.Foods)
            .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
            .filter(
                models.MenuIDS.menu_id == menu_id, models.MenuIDS.cat_id == category.id
            )
            .all()
        )
        for food in foods:
            db.delete(food)
        db.delete(category)

    # Delete the menu
    db.delete(menu)
    db.commit()
    all_menu = (
        db.query(models.Menu)
        .filter(models.Menu.store_id == user.get("id"))
        .order_by(models.Menu.position.asc())
        .all()
    )
    if not all_menu:
        return {"success": True, "all_menu": []}

    for menu in all_menu:
        categories = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.menu_id == menu.id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )
        menu.category = categories
        for category in categories:
            food = (
                db.query(models.Foods)
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == menu.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )

            category.foods = food
    return {"success": True, "all_menu": all_menu}


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Pydantic Models
class SizeResponse(BaseModel):
    url: str
    size: str
    id: Optional[int]
    title: str
    price: float
    status: int


class LanguageCategoryResponse(BaseModel):
    id: int
    title: str
    description: str
    foods: List["LanguageFoodResponse"]


class LanguageFoodResponse(BaseModel):
    id: int
    title: str
    description: str
    price: float
    sizes: List[SizeResponse]


class LanguageMenuResponse(BaseModel):
    language_id: str
    currency_id: str
    title: str
    price: float
    description: str
    sizes: List[SizeResponse]
    categories: List[LanguageCategoryResponse]


class MultiLanguageMenuResponse(BaseModel):
    id: int
    multi_language_data: List[LanguageMenuResponse]


# Update Pydantic model dependencies
LanguageCategoryResponse.update_forward_refs()


def convert_to_dict(
    data, entity_type: str, entity_id: int, default_language: str = None
):
    """Convert string or invalid data to a dictionary."""
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            parsed = json.loads(data)
            if isinstance(parsed, dict):
                return parsed
            if isinstance(parsed, list):
                return parsed[0] if parsed else {}
            logger.warning(
                f"Invalid JSON parsed for {entity_type} {entity_id}: {parsed}"
            )
            return {}
        except json.JSONDecodeError:
            logger.warning(
                f"Failed to parse {entity_type} {entity_id} data as JSON: {data}"
            )
            if entity_type in ["menu", "food"]:
                return {
                    "language_id": data or default_language or "",
                    "title": "",
                    "description": "",
                    "price": 0,
                }
            elif entity_type == "category":
                return {
                    "language_id": data or default_language or "",
                    "title": "",
                    "description": "",
                }
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return item
        logger.warning(f"No valid dict in {entity_type} {entity_id} list: {data}")
        return {}
    logger.warning(f"Invalid {entity_type} {entity_id} data type: {data}")
    return {}


@router.get("/all_menus_multi_language")
async def get_user_all_menus_multi_language(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    shop_id: Optional[int] = None,
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify user exists
    user_info = (
        db.query(models.Members).filter(models.Members.id == user.get("id")).first()
    )
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")

    # Get language currencies
    language_currencies = user_info.language_currencies or []
    logger.debug(
        f"language_currencies: {language_currencies}, type: {type(language_currencies)}"
    )

    if not isinstance(language_currencies, list):
        raise HTTPException(
            status_code=500,
            detail="Invalid language_currencies format: expected a list",
        )

    if not language_currencies:
        logger.warning("No language currencies configured")
        language_currencies = [{"language": "default", "currency": ""}]

    # Query menus
    query = db.query(models.Menu).filter(models.Menu.store_id == user.get("id"))
    if shop_id is not None:
        query = query.filter(models.Menu.shop_id == shop_id)
    menus = query.order_by(models.Menu.position.asc()).all()

    if not menus:
        raise HTTPException(status_code=404, detail="No menus found")

    response = []

    for menu in menus:
        multi_language_data = []
        # Handle menu.multi_language_data
        menu_translations = []
        if isinstance(menu.multi_language_data, str):
            try:
                menu_translations = json.loads(menu.multi_language_data)
                logger.debug(
                    f"Menu {menu.id} parsed multi_language_data: {menu_translations}"
                )
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse menu {menu.id} multi_language_data: {e}")
                menu_translations = [
                    convert_to_dict(menu.multi_language_data, "menu", menu.id)
                ]
        elif isinstance(menu.multi_language_data, list):
            menu_translations = [
                convert_to_dict(t, "menu", menu.id) if not isinstance(t, dict) else t
                for t in menu.multi_language_data
            ]
        else:
            menu_translations = []
        logger.debug(f"Menu {menu.id} multi_language_data: {menu_translations}")

        # Get categories
        categories = (
            db.query(models.FoodCategory)
            .filter(models.FoodCategory.menu_id == menu.id)
            .order_by(models.FoodCategory.position.asc())
            .all()
        )

        for lang_currency in language_currencies:
            if not isinstance(lang_currency, dict):
                logger.warning(f"Invalid lang_currency entry: {lang_currency}")
                continue
            language_id = lang_currency.get("language_id") or lang_currency.get(
                "language", ""
            )
            currency_id = lang_currency.get("currency_id") or lang_currency.get(
                "currency", ""
            )

            if not language_id:
                logger.warning(
                    f"Skipping lang_currency with missing language_id/language: {lang_currency}"
                )
                continue

            # Find menu translation
            menu_translation = next(
                (
                    t
                    for t in menu_translations
                    if isinstance(t, dict) and t.get("language_id") == language_id
                ),
                {
                    "title": menu.title,
                    "description": menu.description or "",
                    "price": float(menu.fix_price or 0),
                },
            )

            sizes = []
            size_id_set = set()
            size_counter = 1

            category_responses = []

            for category in categories:
                # Handle category.multi_language_data
                cat_translations = []
                if isinstance(category.multi_language_data, str):
                    try:
                        cat_translations = json.loads(category.multi_language_data)
                        logger.debug(
                            f"Category {category.id} parsed multi_language_data: {cat_translations}"
                        )
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"Failed to parse category {category.id} multi_language_data: {e}"
                        )
                        cat_translations = [
                            convert_to_dict(
                                category.multi_language_data, "category", category.id
                            )
                        ]
                elif isinstance(category.multi_language_data, list):
                    cat_translations = [
                        (
                            convert_to_dict(t, "category", category.id)
                            if not isinstance(t, dict)
                            else t
                        )
                        for t in category.multi_language_data
                    ]
                else:
                    cat_translations = []
                logger.debug(
                    f"Category {category.id} multi_language_data: {cat_translations}"
                )

                cat_translation = next(
                    (
                        t
                        for t in cat_translations
                        if isinstance(t, dict) and t.get("language_id") == language_id
                    ),
                    {
                        "title": category.title,
                        "description": category.description or "",
                    },
                )

                # Get foods
                foods = (
                    db.query(models.Foods)
                    .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                    .filter(
                        models.MenuIDS.menu_id == menu.id,
                        models.MenuIDS.cat_id == category.id,
                    )
                    .order_by(models.Foods.position.asc())
                    .all()
                )

                food_responses = []

                for food in foods:
                    # Handle food.multi_language_data
                    food_translations = []
                    if isinstance(food.multi_language_data, str):
                        try:
                            food_translations = json.loads(food.multi_language_data)
                            logger.debug(
                                f"Food {food.id} parsed multi_language_data: {food_translations}"
                            )
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Failed to parse food {food.id} multi_language_data: {e}"
                            )
                            food_translations = [
                                convert_to_dict(
                                    food.multi_language_data, "food", food.id
                                )
                            ]
                    elif isinstance(food.multi_language_data, list):
                        food_translations = [
                            (
                                convert_to_dict(t, "food", food.id)
                                if not isinstance(t, dict)
                                else t
                            )
                            for t in food.multi_language_data
                        ]
                    else:
                        food_translations = []
                    logger.debug(
                        f"Food {food.id} multi_language_data: {food_translations}"
                    )

                    food_translation = next(
                        (
                            t
                            for t in food_translations
                            if isinstance(t, dict)
                            and t.get("language_id") == language_id
                        ),
                        {
                            "title": food.title,
                            "description": food.description or "",
                            "price": float(food.price or 0),
                        },
                    )

                    # Handle food.sizes
                    food_sizes = []
                    if isinstance(food.sizes, str):
                        try:
                            food_sizes = json.loads(food.sizes)
                            logger.debug(f"Food {food.id} parsed sizes: {food_sizes}")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse food {food.id} sizes: {e}")
                            food_sizes = []
                    elif isinstance(food.sizes, list):
                        food_sizes = food.sizes
                    else:
                        food_sizes = []
                    logger.debug(f"Food {food.id} sizes: {food_sizes}")

                    food_sizes_response = []
                    for size_data in food_sizes:
                        if not isinstance(size_data, dict):
                            logger.warning(
                                f"Invalid size_data for food {food.id}: {size_data}"
                            )
                            continue
                        size_id = size_data.get("id")
                        if size_id in size_id_set:
                            continue
                        size_id_set.add(size_id)

                        # Check size multi_language_data
                        size_lang_data = {}
                        if "multi_language_data" in size_data:
                            if isinstance(size_data["multi_language_data"], list):
                                size_lang_data = next(
                                    (
                                        s
                                        for s in size_data["multi_language_data"]
                                        if isinstance(s, dict)
                                        and s.get("language_id") == language_id
                                    ),
                                    {},
                                )
                            elif isinstance(size_data["multi_language_data"], dict):
                                size_lang_data = size_data["multi_language_data"].get(
                                    language_id, {}
                                )
                            elif isinstance(size_data["multi_language_data"], str):
                                try:
                                    size_multi_lang = json.loads(
                                        size_data["multi_language_data"]
                                    )
                                    if isinstance(size_multi_lang, dict):
                                        size_lang_data = size_multi_lang.get(
                                            language_id, {}
                                        )
                                    elif isinstance(size_multi_lang, list):
                                        size_lang_data = next(
                                            (
                                                s
                                                for s in size_multi_lang
                                                if isinstance(s, dict)
                                                and s.get("language_id") == language_id
                                            ),
                                            {},
                                        )
                                except json.JSONDecodeError:
                                    logger.warning(
                                        f"Failed to parse size multi_language_data for food {food.id}: {size_data['multi_language_data']}"
                                    )
                                    size_lang_data = {}

                        size_response = SizeResponse(
                            url=size_lang_data.get("url", size_data.get("url", "")),
                            size=size_lang_data.get("size", size_data.get("size", "")),
                            id=size_id or size_counter,
                            title=size_lang_data.get(
                                "title", size_data.get("title", "")
                            ),
                            price=float(
                                size_lang_data.get("price", size_data.get("price", 0))
                            ),
                            status=int(
                                size_lang_data.get("status", size_data.get("status", 0))
                            ),
                        )
                        food_sizes_response.append(size_response)
                        sizes.append(size_response)
                        size_counter += 1

                    food_responses.append(
                        LanguageFoodResponse(
                            id=food.id,
                            title=food_translation.get("title", food.title),
                            description=food_translation.get(
                                "description", food.description or ""
                            ),
                            price=float(food_translation.get("price", food.price or 0)),
                            sizes=food_sizes_response,
                        )
                    )

                category_responses.append(
                    LanguageCategoryResponse(
                        id=category.id,
                        title=cat_translation.get("title", category.title),
                        description=cat_translation.get(
                            "description", category.description or ""
                        ),
                        foods=food_responses,
                    )
                )

            language_menu = LanguageMenuResponse(
                language_id=language_id,
                currency_id=currency_id,
                title=menu_translation.get("title", menu.title),
                price=float(menu_translation.get("price", menu.fix_price or 0)),
                description=menu_translation.get("description", ""),
                sizes=sizes,
                categories=category_responses,
            )
            multi_language_data.append(language_menu)

        response.append({"id": menu.id, "multi_language_data": multi_language_data})

    return {"all_menu": response}


# Exceptions
def get_user_exception():
    credential_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate User",
        headers={"www-Authenticate": "Bearer"},
    )
    return credential_exception


def token_exception():
    token_exception_response = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Email or password incorrect",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return token_exception_response


# @router.post("/create_step_two")
# async def create_order_step_two(
#     next_step: CreateOrderStepTwo, db: Session = Depends(get_db)
# ):
#     find_order = (
#         db.query(models.OnlineOrders)
#         .filter(models.OnlineOrders.unique_address == next_step.unique_address)
#         .first()
#     )

#     if not find_order:
#         raise HTTPException(status_code=404, detail="Order not found")

#     check_order = (
#         db.query(models.Members)
#         .filter(models.Members.id == find_order.store_id)
#         .first()
#     )

#     if not check_order.online_order:
#         raise HTTPException(
#             status_code=403, detail="You don't have access to use this feature"
#         )

#     try:
#         # Check if customer exists by cellphone
#         customer = None
#         if next_step.cellphone:
#             customer = (
#                 db.query(models.Customer)
#                 .filter(models.Customer.cellphone == next_step.cellphone)
#                 .first()
#             )

#             # If customer doesn't exist, create new customer
#             if not customer:
#                 customer = models.Customer(
#                     fname=next_step.customer_name,
#                     cellphone=next_step.cellphone,
#                     address=next_step.address,
#                     register_date=datetime.utcnow(),
#                 )
#                 db.add(customer)
#                 db.flush()  # Get customer ID before commit

#         # Update order with customer_id
#         if customer:
#             find_order.customer_id = customer.id

#         # Update order details
#         find_order.description = next_step.description
#         if next_step.payment_method_id is not None:
#             find_order.payment_method_id = next_step.payment_method_id
#         find_order.address = next_step.address
#         find_order.customer_name = next_step.customer_name
#         find_order.cellphone = next_step.cellphone
#         if next_step.room_number:
#             find_order.room_number = next_step.room_number
#         if next_step.table_number:
#             find_order.table_number = next_step.table_number
#         find_order.order_status = 1

#         # Handle discount
#         if next_step.discount_code:
#             find_discount = (
#                 db.query(models.DiscountCode)
#                 .filter(
#                     and_(
#                         models.DiscountCode.code == next_step.discount_code,
#                         models.DiscountCode.store_id == find_order.store_id,
#                     )
#                 )
#                 .first()
#             )
#             if find_discount:
#                 total_price = find_order.total_price
#                 discount_amount = total_price * (find_discount.percent / 100)
#                 find_order.discount = discount_amount
#                 find_discount.used_count += 1
#                 find_order.discount_code = next_step.discount_code

#         # Handle contact creation/updating
#         if next_step.cellphone:
#             find_tag = (
#                 db.query(models.Tag)
#                 .filter(
#                     models.Tag.title == "سفارش آنلاین",
#                     models.Tag.store_id == check_order.id,
#                 )
#                 .first()
#             )

#             if not find_tag:
#                 find_tag = models.Tag(
#                     title="سفارش آنلاین", enabled=True, store_id=check_order.id
#                 )
#                 db.add(find_tag)
#                 db.flush()

#             existing_contact = (
#                 db.query(models.Contact)
#                 .filter(
#                     models.Contact.store_id == check_order.id,
#                     models.Contact.phone == find_order.cellphone,
#                 )
#                 .first()
#             )

#             if not existing_contact:
#                 contact = models.Contact(
#                     store_id=check_order.id,
#                     name=next_step.customer_name,
#                     family_name="",
#                     phone=next_step.cellphone,
#                     tag_name=find_tag.title,
#                     tag_id=find_tag.id,
#                     customer_id=customer.id if customer else None,
#                 )
#                 db.add(contact)
#             elif customer:
#                 existing_contact.customer_id = customer.id

#         # SMS handling
#         if check_order.remaining_sms > 4:
#             sum_sms_count = 0
#             base_url = (
#                 check_order.default_url
#                 if "https://" in check_order.default_url
#                 else f"{os.getenv('MENU_BASE_URL')}{check_order.default_url}"
#             )
#             url_suffix = ".html" if ".html" not in base_url else ""

#             # Customer SMS
#             customer_sms = f"{next_step.customer_name} عزیز\nسفارش شما به شماره پیگیری {find_order.id} با موفقیت ثبت شد.\n{base_url}{url_suffix}\n{check_order.brand_name}\nلغو11"
#             response_receipt = await send_sms_array(
#                 [find_order.cellphone], "200004044", customer_sms
#             )
#             sum_sms_count += int(len(customer_sms) / 70) + 2

#             # Store owner SMS
#             owner_sms = f'یک سفارش برای مجموعه {check_order.brand_name} ثبت شده است.\n{base_url.split("/")[-2]}\nلغو11'
#             response_customer = await send_sms_array(
#                 [check_order.cellphone], "200004044", owner_sms
#             )
#             sum_sms_count += int(len(owner_sms) / 70) + 2

#             # Additional notification number
#             if check_order.online_order_sms:
#                 second_number = await send_sms_array(
#                     [check_order.online_order_sms], "200004044", owner_sms
#                 )
#                 sum_sms_count += int(len(owner_sms) / 70) + 2

#             check_order.remaining_sms -= sum_sms_count

#         db.commit()
#         return {"success": True}

#     except Exception as ex:
#         db.rollback()
#         if isinstance(ex, HTTPException):
#             raise ex
#         raise HTTPException(status_code=403, detail=str(ex))


@router.post("/orders/from-cart", response_model=CartOrderResponse)
async def create_order_from_cart(
    cart_request: CartOrderRequest, db: Session = Depends(get_db)
):
    """
    Create an order from cart items with server-side validation and price calculation.
    This endpoint validates the cart, calculates prices server-side, and stores the order.
    """
    try:
        # Validate cart is not empty
        if not cart_request.cart:
            raise HTTPException(status_code=400, detail="Cart cannot be empty")

        # Validate quantities
        for item in cart_request.cart:
            if item.quantity <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid quantity for item {item.id}: must be greater than 0",
                )

        # Get store information from the first food item
        first_food = (
            db.query(models.Foods)
            .filter(models.Foods.id == cart_request.cart[0].id)
            .first()
        )
        if not first_food:
            raise HTTPException(
                status_code=404, detail=f"Food item {cart_request.cart[0].id} not found"
            )

        store_id = first_food.store_id

        # Check if store has online ordering enabled
        store = db.query(models.Members).filter(models.Members.id == store_id).first()
        if not store or not store.online_order:
            raise HTTPException(
                status_code=403, detail="Online ordering is not enabled for this store"
            )

        # Create new order
        new_order = models.OnlineOrders()
        random_address = "".join(
            random.choice(string.ascii_uppercase + string.digits) for _ in range(10)
        )
        new_order.unique_address = random_address
        new_order.order_time = datetime.utcnow()
        new_order.payment_method_id = cart_request.info.payment_method or 0
        new_order.payment_status = "pending"
        new_order.order_status = 0  # New order
        new_order.store_id = store_id
        new_order.customer_name = cart_request.info.name
        new_order.cellphone = cart_request.info.mobile
        new_order.address = cart_request.info.address or ""
        new_order.description = cart_request.info.description or ""
        new_order.room_number = cart_request.info.room_number or ""
        new_order.table_number = cart_request.info.table_number or ""
        new_order.form_type = store.form_type

        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # Process cart items and calculate total
        total_price = 0.0

        for cart_item in cart_request.cart:
            # Get food item from database
            food = (
                db.query(models.Foods).filter(models.Foods.id == cart_item.id).first()
            )
            if not food:
                raise HTTPException(
                    status_code=404, detail=f"Food item {cart_item.id} not found"
                )

            # Validate food is available
            if not food.enabled or food.available == 0:
                raise HTTPException(
                    status_code=400, detail=f"Food item {food.title} is not available"
                )

            # Calculate price based on size
            unit_price = get_food_price_by_size(
                food, cart_item.size.value if cart_item.size else None
            )

            # Validate size if provided
            if cart_item.size:
                if not food.sizes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Food item {food.title} does not have size options",
                    )

                sizes = (
                    json.loads(food.sizes)
                    if isinstance(food.sizes, str)
                    else food.sizes
                )
                size_found = False
                for size_option in sizes:
                    if size_option.get("size") == cart_item.size.value:
                        size_found = True
                        break

                if not size_found:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Size '{cart_item.size.value}' is not available for {food.title}",
                    )

            # Calculate item total
            item_total = unit_price * cart_item.quantity
            total_price += item_total

            # Create order item
            order_item = models.OrderItem(
                order_id=new_order.id,
                product_id=cart_item.id,
                product_type="food",
                quantity=cart_item.quantity,
                unit_price=int(unit_price),
                price=int(item_total),
                size=cart_item.size.value if cart_item.size else None,
            )
            db.add(order_item)

        # Update order total
        new_order.total_price = total_price
        db.commit()

        return CartOrderResponse(
            success=True,
            order_id=new_order.id,
            unique_address=new_order.unique_address,
            total_price=total_price,
            message="Order created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating order: {str(e)}")


# @router.get("/{menu_id}/export")
# async def export_menu_to_excel(
#     menu_id: int,
#     db: Session = Depends(get_db),
#     user: dict = Depends(get_current_user)
# ):
#     menu = db.query(Menu).filter(Menu.id == menu_id).first()
#     if not menu or menu.store_id != int(user["id"]):
#         raise HTTPException(status_code=404, detail="Menu not found or unauthorized")

#     foods = (
#         db.query(Foods)
#         .join(MenuIDS, MenuIDS.food_id == Foods.id)
#         .filter(MenuIDS.menu_id == menu_id)
#         .all()
#     )

#     if not foods:
#         raise HTTPException(status_code=404, detail="No foods found in this menu")

#     file_path = os.path.join(tempfile.gettempdir(), f"menu_{menu_id}_foods.xlsx")
#     workbook = xlsxwriter.Workbook(file_path)
#     worksheet = workbook.add_worksheet("Foods")
#     worksheet.write_row(0, 0, ["ID", "Food Name", "Price"])

#     row = 1
#     for food in foods:
#         sizes = food.sizes or []
#         if isinstance(sizes, list) and sizes:
#             for i, size in enumerate(sizes, 1):
#                 worksheet.write(row, 0, f"{food.id}-{i}")
#                 worksheet.write(row, 1, f"{food.title} ({size.get('title', '')})")
#                 worksheet.write(row, 2, size.get("price", ""))
#                 row += 1
#         else:
#             worksheet.write(row, 0, str(food.id))
#             worksheet.write(row, 1, food.title)
#             worksheet.write(row, 2, food.price)
#             row += 1

#     workbook.close()

#     return FileResponse(
#         file_path,
#         filename=f"menu_{menu_id}_foods.xlsx",
#         media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
#     )


# @router.post("/{menu_id}/import")
# async def import_menu_prices_from_excel(
#     menu_id: int,
#     file: UploadFile = File(...),
#     db: Session = Depends(get_db),
#     user: dict = Depends(get_current_user)
# ):

#     menu = db.query(Menu).filter(Menu.id == menu_id).first()
#     if not menu or menu.store_id != int(user["id"]):
#         raise HTTPException(status_code=404, detail="Menu not found or unauthorized")


#     try:
#         wb = openpyxl.load_workbook(file.file, data_only=True)
#         sheet = wb.active
#     except Exception as e:
#         raise HTTPException(status_code=400, detail="Invalid Excel file format")

#     updated_count = 0

#     # Iterate rows starting from row 2 (skip headers)
#     for i, row in enumerate(sheet.iter_rows(min_row=2), start=2):
#         raw_id = str(row[0].value).strip() if row[0].value else None
#         new_price = row[2].value

#         if not raw_id or new_price is None:
#             continue

#         try:
#             if '-' in raw_id:
#                 base_id, size_index = map(int, raw_id.split('-'))
#                 food = db.query(Foods).filter(Foods.id == base_id).first()
#                 if food and isinstance(food.sizes, list) and 0 < size_index <= len(food.sizes):
#                     food.sizes[size_index - 1]["price"] = new_price
#                     food.sizes = food.sizes  # trigger update
#                     updated_count += 1
#             else:
#                 base_id = int(raw_id)
#                 food = db.query(Foods).filter(Foods.id == base_id).first()
#                 if food:
#                     food.price = str(new_price)
#                     updated_count += 1
#         except Exception as e:
#             print(f"❌ Error on row {i}: {e}")
#             continue

#     db.commit()
#     return {"detail": f"{updated_count} prices updated successfully."}


#--------updates





from typing import List, Optional
from sqlalchemy.orm import selectinload
import json







class v2MultiLanguage(BaseModel):
    language_id: str
    currency_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None



class v2CategoryTranslation(BaseModel):
    language_id: str
    title: Optional[str] = None
    description: Optional[str] = None



class v2FoodSizeTranslationOut(BaseModel):
    language_id: str
    title: Optional[str] = None
    price: Optional[float] = None



class v2FoodSizeOut(BaseModel):
    id: int
    type_size: str
    status: int
    image_url: Optional[str] = None
    translations: List[v2FoodSizeTranslationOut] = Field(default_factory=list)




from typing import List, Optional, Union
from pydantic import BaseModel, Field
from typing_extensions import Literal

class Categoryv2(BaseModel):
    type: Literal["category"] = "category"
    id: Optional[str] = None
    title: str
    cat_image: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    parent_is_menu: bool
    menu_id: int
    enabled: Optional[int] = None
    multi_language_data: Optional[List[v2CategoryTranslation]] = None
    children: List[Union["Category", "Food"]] = Field(default_factory=list)




class Menuv2(BaseModel):
    type: Literal["menu"]
    id: str
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    is_primary: Optional[bool] = None
    currency: Optional[str] = None
    show_price: Optional[bool] = None
    show_store_info: Optional[bool] = None
    template_name: Optional[str] = None
    theme_url: Optional[str] = None
    customizable_background: bool = False
    smart_template: Optional[bool] = None
    background_image: List[str] = Field(default_factory=list)
    position: Optional[int] = None
    children: List[Category] = Field(default_factory=list)
    multi_language_data: Optional[List[v2MultiLanguage]] = None
    template_color: Optional[str] = None



class Foodv2(BaseModel):
    type: Literal["food"] = "food"
    id: Optional[str] = None
    menu_id: int
    category_id: int
    title: str
    englishTitle: Optional[str] = None
    price: Optional[int] = None  # Flat price optional since per-language pricing exists
    food_image: List[str] = Field(default_factory=list)
    food_video: Optional[str] = None
    description: Optional[str] = None
    discount: Optional[int] = None
    ready_by_time: Optional[int] = None
    available: Optional[int] = None
    sizes: List[v2FoodSizeOut] = Field(default_factory=list)
    multi_language_data: Optional[List[v2MultiLanguage]] = None





from typing import List, Optional
from pydantic import Field
import json

def _safe_json_list(val) -> List[str]:
    """Ensure a value is returned as a list of strings (handles JSON/text)."""
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return []
        try:
            loaded = json.loads(s)
            return loaded if isinstance(loaded, list) else [s]
        except json.JSONDecodeError:
            return [val]
    return []

def _transform_category_translations(translations) -> Optional[List[v2CategoryTranslation]]:
    if not translations:
        return None
    return [
        v2CategoryTranslation(
            language_id=str(t.language_id or ""),
            title=t.title,
            description=t.description
        )
        for t in translations
    ]

def _transform_food_translations(translations) -> Optional[List[v2MultiLanguage]]:
    if not translations:
        return None
    return [
        v2MultiLanguage(
            language_id=str(t.language_id or ""),
            currency_id=getattr(t, "currency_id", None),
            title=t.title,
            description=t.description,
            price=float(t.price) if t.price is not None else None
        )
        for t in translations
    ]

def _transform_sizes(size_items) -> List[v2FoodSizeOut]:
    if not size_items:
        return []
    return [
        v2FoodSizeOut(
            id=s.id,
            type_size=s.type_size,
            status=s.status,
            image_url=s.image_url,
            translations=[
                v2FoodSizeTranslationOut(
                    language_id=t.language_id,
                    title=t.title,
                    price=t.price
                )
                for t in (s.translations or [])
            ]
        )
        for s in size_items
    ]





# Helper functions for the refactored publish_menu function
def get_category_translations(category):
    """Get category translations from the new relational model"""
    if not category.translations:
        return {}
    
    titles = {"fa": category.title}
    additional_titles = {
        translation.language_id: translation.title
        for translation in category.translations
        if translation.language_id != "fa" and translation.title
    }
    titles.update(additional_titles)
    return titles

def get_food_sizes(food):
    """Get food sizes from the new relational model"""
    if not food.size_items:
        return []
    
    sizes = []
    for size_item in food.size_items:
        size_data = {
            "id": size_item.id,
            "type_size": size_item.type_size,
            "status": size_item.status,
            "image_url": size_item.image_url
        }
        
        # Add translations if available
        if size_item.translations:
            size_data["translations"] = [
                {
                    "language_id": trans.language_id,
                    "title": trans.title,
                    "price": trans.price
                }
                for trans in size_item.translations
            ]
        
        sizes.append(size_data)
    
    return sizes

def transform_menu_data_v2(menu) -> Menuv2:
    if not isinstance(menu, dict):
        return Menuv2(
            type="menu",
            id=str(menu.id),
            title=menu.title or "",
            description=menu.description,
            is_primary=menu.is_primary,
            currency=menu.currency,
            show_price=menu.show_price,
            show_store_info=menu.show_store_info,
            template_name=menu.template_name,
            theme_url=menu.theme_url,
            template_color=menu.template_color,
            customizable_background=getattr(menu, "customizable_background", False),
            smart_template=menu.smart_template,
            background_image=_safe_json_list(menu.background_image),
            position=menu.position,
            children=[],
            multi_language_data=None
        )
    # Fallback dict
    return Menuv2(
        type="menu",
        id=str(menu.get("id")),
        title=menu.get("title", ""),
        description=menu.get("description"),
        is_primary=menu.get("is_primary"),
        currency=menu.get("currency"),
        show_price=menu.get("show_price"),
        show_store_info=menu.get("show_store_info"),
        template_name=menu.get("template_name"),
        theme_url=menu.get("theme_url"),
        template_color=menu.get("template_color"),
        customizable_background=menu.get("customizable_background", False),
        smart_template=menu.get("smart_template"),
        background_image=_safe_json_list(menu.get("background_image", [])),
        position=menu.get("position"),
        children=[],
        multi_language_data=None
    )

def transform_category_data_v2(category) -> Categoryv2:
    if not isinstance(category, dict):
        return Categoryv2(
            type="category",
            id=str(category.id),
            title=category.title or "",
            description=category.description or "",
            cat_image=category.cat_image or None,
            parent_id=category.parent_id,
            parent_is_menu=category.parent_is_menu or False,
            menu_id=category.menu_id or 0,
            enabled=category.enabled,
            multi_language_data=_transform_category_translations(category.translations),
            children=[]
        )
    return Categoryv2(
        type="category",
        id=str(category.get("id")),
        title=category.get("title", ""),
        description=category.get("description", ""),
        cat_image=category.get("cat_image") or None,
        parent_id=category.get("parent_id"),
        parent_is_menu=category.get("parent_is_menu", False),
        menu_id=category.get("menu_id", 0),
        enabled=category.get("enabled"),
        multi_language_data=None,
        children=[]
    )

def transform_food_data_v2(food) -> Foodv2:
    if not isinstance(food, dict):
        return Foodv2(
            type="food",
            id=str(food.id),
            menu_id=getattr(food, "menu_id", 0) or 0,
            category_id=food.cat_id or 0,
            title=food.title or "",
            englishTitle=getattr(food, "englishTitle", None),
            price=food.price or None,
            food_image=_safe_json_list(food.food_image),
            food_video=food.food_video or None,
            description=food.description or None,
            discount=food.discount,
            ready_by_time=food.ready_by_time,
            available=food.available,
            sizes=_transform_sizes(food.size_items),
            multi_language_data=_transform_food_translations(food.translations)
        )
    return Foodv2(
        type="food",
        id=str(food.get("id")),
        menu_id=food.get("menu_id", 0),
        category_id=food.get("cat_id", 0),
        title=food.get("title", ""),
        englishTitle=food.get("englishTitle"),
        price=food.get("price", None),
        food_image=_safe_json_list(food.get("food_image", [])),
        food_video=food.get("food_video"),
        description=food.get("description"),
        discount=food.get("discount"),
        ready_by_time=food.get("ready_by_time"),
        available=food.get("available"),
        sizes=[],
        multi_language_data=None
    )









from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session, selectinload

@router.get("/v2/items/menu/{id}", response_model=Menuv2)
async def get_menu_detail_v2(
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    menu = db.query(models.Menu).filter(
        models.Menu.id == id,
        models.Menu.store_id == user.get("id")
    ).first()
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")

    categories = db.query(models.FoodCategory).options(
        selectinload(models.FoodCategory.translations),
        selectinload(models.FoodCategory.food_id).selectinload(models.Foods.translations),
        selectinload(models.FoodCategory.food_id).selectinload(models.Foods.size_items).selectinload(models.FoodSize.translations),
    ).filter(
        models.FoodCategory.menu_id == menu.id,
        models.FoodCategory.parent_id == 0,
        models.FoodCategory.store_id == user.get("id"),
    ).order_by(models.FoodCategory.position.asc()).all()

    menu_out = transform_menu_data_v2(menu)

    def build_category_tree(cat: models.FoodCategory):
        cat_out = transform_category_data_v2(cat)
        cat_out.children.extend([transform_food_data_v2(f) for f in (cat.food_id or [])])
        subs = db.query(models.FoodCategory).options(
            selectinload(models.FoodCategory.translations),
            selectinload(models.FoodCategory.food_id).selectinload(models.Foods.translations),
            selectinload(models.FoodCategory.food_id).selectinload(models.Foods.size_items).selectinload(models.FoodSize.translations),
        ).filter(
            models.FoodCategory.parent_id == cat.id,
            models.FoodCategory.menu_id == menu.id,
            models.FoodCategory.store_id == user.get("id"),
        ).order_by(models.FoodCategory.position.asc()).all()
        for sc in subs:
            cat_out.children.append(build_category_tree(sc))
        return cat_out

    menu_out.children = [build_category_tree(c) for c in categories]
    return menu_out

@router.get("/v2/items/category/{id}", response_model=Categoryv2)
async def get_category_detail_v2(
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    category = db.query(models.FoodCategory).options(
        selectinload(models.FoodCategory.translations),
        selectinload(models.FoodCategory.food_id).selectinload(models.Foods.translations),
        selectinload(models.FoodCategory.food_id).selectinload(models.Foods.size_items).selectinload(models.FoodSize.translations),
    ).filter(
        models.FoodCategory.id == id,
        models.FoodCategory.store_id == user.get("id"),
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    def build_category_tree(cat: models.FoodCategory):
        cat_out = transform_category_data_v2(cat)
        cat_out.children.extend([transform_food_data_v2(f) for f in (cat.food_id or [])])
        subs = db.query(models.FoodCategory).options(
            selectinload(models.FoodCategory.translations),
            selectinload(models.FoodCategory.food_id).selectinload(models.Foods.translations),
            selectinload(models.FoodCategory.food_id).selectinload(models.Foods.size_items).selectinload(models.FoodSize.translations),
        ).filter(
            models.FoodCategory.parent_id == cat.id,
            models.FoodCategory.store_id == user.get("id"),
        ).order_by(models.FoodCategory.position.asc()).all()
        for sc in subs:
            cat_out.children.append(build_category_tree(sc))
        return cat_out

    return build_category_tree(category)

@router.get("/v2/items/food/{id}", response_model=Foodv2)
async def get_food_detail_v2(
    id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")

    food = db.query(models.Foods).options(
        selectinload(models.Foods.translations),
        selectinload(models.Foods.size_items).selectinload(models.FoodSize.translations),
        selectinload(models.Foods.cat_id_val),
    ).filter(
        models.Foods.id == id,
        models.Foods.store_id == user.get("id")
    ).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    if food.cat_id_val:
        setattr(food, "menu_id", food.cat_id_val.menu_id or 0)
    else:
        setattr(food, "menu_id", 0)

    return transform_food_data_v2(food)


