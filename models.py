from datetime import datetime
from enum import Enum
from sqlite3 import Date

from sqlalchemy import (
    DATETIME,
    JSON,
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


class Members(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(200))
    birth_date = Column(String(200))
    address = Column(String(200))
    form_type = Column(Integer, default=0)
    zip_code = Column(String(200))
    province = Column(String(200))
    city = Column(String(200))
    telephone = Column(String(200))
    brand_logo = Column(String(200))
    gold_cost = Column(Integer, default=0)
    import_contact = Column(Boolean, default=False)
    profile_url = Column(String(200))
    default_url = Column(String(200))
    default_description = Column(Text(collation="utf8mb4_unicode_ci"))
    cellphone = Column(String(200), unique=True)
    email_address = Column(String(200))
    merchant_id = Column(String(200))
    location_url = Column(String(200))
    survey_sent = Column(Integer, default=0)
    survey_answered = Column(Integer, default=0)
    unique_name = Column(String(200))
    onboarding_option = Column(Integer, default=0)
    typed_menu = Column(Text)
    uploaded_menu = Column(JSON)
    payment_methods = Column(JSON)
    language_currencies = Column(JSON)
    onboarding_receive_messenger = Column(String(200))
    onboarding_description = Column(String(200))
    instagram_address = Column(String(200))
    verification_code = Column(String(9))
    user_name = Column(String(200), unique=False)
    register_date = Column(String(200))
    remaining_sms = Column(Integer, default=0)
    subscription_id = Column(Integer)
    otp_expire_date = Column(String(200))
    publish_event = Column(String(200))
    menu_counter = Column(Boolean, default=False)
    online_order_sms = Column(String(200), default="")
    expire_date = Column(String(200))
    tax_value = Column(Integer, default=0)
    extra_cost = Column(Integer, default=0)
    resNum = Column(String(200))
    multi_language_currency = Column(Boolean, default=False)
    IsShop = Column(Boolean, default=False)
    call_order = Column(Boolean, default=False)
    online_order = Column(Boolean, default=False)
    online_order_report = Column(Boolean, default=False)
    waiter_panel = Column(Boolean, default=False)
    remind_sms3 = Column(Boolean, default=False)
    remind_sms7 = Column(Boolean, default=False)
    remind_sms0 = Column(Boolean, default=False)
    order_discount = Column(Boolean, default=False)
    payment_gateway = Column(Boolean, default=False)
    landing_access = Column(Boolean, default=False)
    domain_access = Column(Boolean, default=False)
    courier = Column(Boolean, default=False)
    public_wait_time = Column(Integer, default=0)
    custom_template = Column(String(200), nullable=True, default=None)
    access_type = Column(Integer, ForeignKey("AccessType.id", ondelete="RESTRICT"))
    verified = Column(Boolean, default=False)
    store_id = relationship("Menu", back_populates="store_id_val")
    store_id_food_category = relationship("FoodCategory", back_populates="store_id_val")
    store_id_foods = relationship("Foods", back_populates="store_id_val")
    store_id_tag = relationship("Tag", back_populates="store_id_val")
    store_id_contact = relationship("Contact", back_populates="store_id_val")
    store_id_payment = relationship("Payment", back_populates="store_id_payment")
    store_id_paid = relationship("UserPaid", back_populates="store_id_paid")
    store_id_shops = relationship("Shops", back_populates="store_id_rel")
    access_type_rel = relationship("AccessType", back_populates="stores_rel")
    store_id_banner = relationship("ClientBanner", back_populates="store_id_rel")
    store_id_label = relationship("Labels", back_populates="store_id_rel")
    survey_q_rel = relationship("SurveyQ", back_populates="store_id_rel")
    store_id_couriers = relationship("Courier", back_populates="store_id_val")
    club = Column(Integer, nullable=False, default=0)
    customer_links = relationship(
        "StoreCustomer", back_populates="store", cascade="all, delete-orphan"
    )


class Shops(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(200))
    brand_logo = Column(String(200))
    tax_value = Column(Integer, default=0)
    form_type = Column(Integer, default=0)
    location_url = Column(String(200))
    survey_sent = Column(Integer, default=0)
    survey_answered = Column(Integer, default=0)
    unique_name = Column(String(200))
    telephone = Column(String(200))
    instagram_address = Column(String(200))
    payment_methods = Column(JSON)
    multi_language_currency = Column(Boolean, default=False)
    remaining_sms = Column(Integer, default=0)
    publish_event = Column(String(200))
    default_url = Column(String(200))
    default_description = Column(Text(collation="utf8mb4_unicode_ci"))
    address = Column(String(200))
    public_wait_time = Column(Integer, default=0)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    store_id_rel = relationship("Members", back_populates="store_id_shops")


class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    theme_url = Column(String(200))
    currency = Column(String(200))
    fix_price = Column(Integer, default=0)
    percent_price = Column(Integer, default=0)
    show_price = Column(Boolean, default=False)
    show_store_info = Column(Boolean, default=False)
    description = Column(String(200))
    is_primary = Column(Boolean, default=False)
    position = Column(Integer, default=0)
    template_name = Column(String(200))
    is_sub_shop = Column(Boolean, default=False)
    shop_id = Column(Integer)
    background_image = Column(String(200))
    date_creation = Column(String(200))
    multi_language_data = Column(JSON)
    smart_template = Column(Boolean, default=False)
    template_color = Column(String(200), nullable=True, default=None)
    store_id_val = relationship("Members", back_populates="store_id")
    menu_ids = relationship("MenuIDS", back_populates="menu")
    main_menu_id = relationship("FoodCategory", back_populates="main_menu_id")


class FoodCategory(Base):
    __tablename__ = "food_category"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    cat_image = Column(String(200))
    description = Column(String(200))
    enabled = Column(Integer, default=0)
    parent_id = Column(Integer)
    position = Column(Integer, default=0)
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"))
    multi_language_data = Column(JSON)
    main_menu_id = relationship("Menu", back_populates="main_menu_id")
    parent_is_menu = Column(Boolean, default=False)
    store_id_val = relationship("Members", back_populates="store_id_food_category")
    food_id = relationship("Foods", back_populates="cat_id_val")
    menu_ids = relationship("MenuIDS", back_populates="cat")
    translations = relationship("FoodCategoryTranslation", back_populates="category", cascade="all, delete")


class Foods(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    cat_id = Column(Integer, ForeignKey("food_category.id", ondelete="CASCADE"))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    title = Column(String(200))
    price = Column(String(200))
    food_image = Column(JSON, nullable=True)
    food_video = Column(String(200))
    sizes = Column(JSON)
    description = Column(String(1500))
    englishTitle = Column(String(200))
    multi_language_data = Column(JSON)
    enabled = Column(Boolean, default=True)
    available = Column(Integer, default=0)
    position = Column(Integer, default=0)
    discount = Column(Integer, default=0)
    ready_by_time = Column(Integer, default=0)
    store_id_val = relationship("Members", back_populates="store_id_foods")
    cat_id_val = relationship("FoodCategory", back_populates="food_id")
    food_labels = relationship("FoodLabels", back_populates="food_id_rel")
    food_sync = relationship("FoodSync", back_populates="food_id_rel")
    translations = relationship("FoodLanguage", back_populates="food", cascade="all, delete")
    size_items = relationship("FoodSize", back_populates="food", cascade="all, delete")




class FoodCategoryTranslation(Base):
    __tablename__ = "food_category_translations"

    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("food_category.id", ondelete="CASCADE"))
    language_id = Column(String(10))  
    title = Column(String(200))
    description = Column(Text)

    __table_args__ = (UniqueConstraint('category_id', 'language_id'),)
    category = relationship("FoodCategory", back_populates="translations")



class FoodLanguage(Base):
    __tablename__ = "food_languages"

    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"))
    language_id = Column(String(10))  
    currency_id = Column(String(10))
    title = Column(String(200))
    description = Column(Text)
    price = Column(Float)

    __table_args__ = (UniqueConstraint('food_id', 'language_id'),)    
    food = relationship("Foods", back_populates="translations")



class FoodSize(Base):
    __tablename__ = "food_sizes"

    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"))
    type_size = Column(String(50))  
    status = Column(Integer, default=1)
    image_url = Column(String(300))

    food = relationship("Foods", back_populates="size_items")
    translations = relationship("FoodSizeTranslation", back_populates="size", cascade="all, delete")




class FoodSizeTranslation(Base):
    __tablename__ = "food_size_translation"

    id = Column(Integer, primary_key=True)
    size_id = Column(Integer, ForeignKey("food_sizes.id", ondelete="CASCADE"))
    language_id = Column(String(10))
    title = Column(String(100))
    price = Column(Float)

    __table_args__ = (UniqueConstraint('size_id', 'language_id'),)

    size = relationship("FoodSize", back_populates="translations")








class MenuIDS(Base):
    __tablename__ = "MenuIDS"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    menu_id = Column(Integer, ForeignKey("menus.id", ondelete="CASCADE"))
    cat_id = Column(Integer, ForeignKey("food_category.id", ondelete="CASCADE"))
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"))
    cat = relationship("FoodCategory", back_populates="menu_ids")
    menu = relationship("Menu", back_populates="menu_ids")


class Tag(Base):
    __tablename__ = "Tag"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    enabled = Column(Boolean, default=True)
    store_id_val = relationship("Members", back_populates="store_id_tag")
    tag_id_contact = relationship("Contact", back_populates="tag_id_val")


class Contact(Base):
    __tablename__ = "Contact"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    tag_id = Column(Integer, ForeignKey("Tag.id", ondelete="RESTRICT"))
    family_name = Column(String(200))
    email = Column(String(200), nullable=True)
    phone = Column(String(200))
    birth_date = Column(DATETIME)
    tag_name = Column(String(200))
    created_at = Column(DATETIME, default=datetime.utcnow())
    store_id_val = relationship("Members", back_populates="store_id_contact")
    tag_id_val = relationship("Tag", back_populates="tag_id_contact")
    customer_id = Column(
        Integer, ForeignKey("customer.id", ondelete="SET NULL"), nullable=True
    )


class Subscription(Base):
    __tablename__ = "Subscription"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    title_en = Column(String(200))
    title_tr = Column(String(200))
    title_gr = Column(String(200))
    title_ar = Column(String(200))
    price = Column(Integer)
    price_en = Column(Integer)
    price_tr = Column(Integer)
    price_gr = Column(Integer)
    price_ar = Column(Integer)
    price_with_discount = Column(Integer)
    price_with_discount_en = Column(Integer)
    price_with_discount_tr = Column(Integer)
    price_with_discount_gr = Column(Integer)
    price_with_discount_ar = Column(Integer)
    label = Column(String(200))
    label_en = Column(String(200))
    label_tr = Column(String(200))
    label_gr = Column(String(200))
    label_ar = Column(String(200))
    icon = Column(String(200))
    icon_en = Column(String(200))
    icon_tr = Column(String(200))
    icon_gr = Column(String(200))
    icon_ar = Column(String(200))
    access_id = Column(Integer, ForeignKey("AccessType.id", ondelete="RESTRICT"))
    access_id_rel = relationship("AccessType", back_populates="access_id_rel")
    currency = Column(String(100))
    currency_en = Column(String(100))
    currency_tr = Column(String(100))
    currency_gr = Column(String(100))
    currency_ar = Column(String(100))
    sms_count = Column(Integer, default=100)
    sms_count_en = Column(Integer, default=100)
    sms_count_tr = Column(Integer, default=100)
    sms_count_gr = Column(Integer, default=100)
    sms_count_ar = Column(Integer, default=100)
    advantages = Column(JSON, nullable=True)
    advantages_en = Column(JSON, nullable=True)
    advantages_tr = Column(JSON, nullable=True)
    advantages_gr = Column(JSON, nullable=True)
    advantages_ar = Column(JSON, nullable=True)
    subscriptionType = Column(String(200))
    subscriptionType_en = Column(String(200))
    subscriptionType_tr = Column(String(200))
    subscriptionType_gr = Column(String(200))
    subscriptionType_ar = Column(String(200))
    discount_description = Column(String(200))
    discount_description_en = Column(String(200))
    discount_description_tr = Column(String(200))
    discount_description_gr = Column(String(200))
    discount_description_ar = Column(String(200))
    all_description = Column(String(200))
    all_description_en = Column(String(200))
    all_description_tr = Column(String(200))
    all_description_gr = Column(String(200))
    all_description_ar = Column(String(200))
    additional_sms = Column(Integer, default=0)
    days = Column(Integer)
    days_en = Column(Integer)
    days_tr = Column(Integer)
    days_gr = Column(Integer)
    days_ar = Column(Integer)


class Payment(Base):
    __tablename__ = "Payment"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(String(200))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="RESTRICT"))
    store_id_payment = relationship("Members", back_populates="store_id_payment")
    created_at = Column(String(200))
    status = Column(String(200))


class UserPaid(Base):
    __tablename__ = "UserPaid"

    id = Column(Integer, primary_key=True, index=True)
    ref_num = Column(String(10))
    created_at = Column(String(200))
    user_id = Column(Integer, ForeignKey("stores.id", ondelete="RESTRICT"))
    store_id_paid = relationship("Members", back_populates="store_id_paid")
    plan_id = Column(Integer)
    is_active = Column(Boolean, default=False)
    status = Column(String(200))
    amount = Column(String(200))


class MessageConfig(Base):
    __tablename__ = "MessageConfig"

    id = Column(Integer, primary_key=True, index=True)
    default_message = Column(String(200), nullable=True)
    config_type = Column(Integer)
    created_at = Column(String(200))


class ReceiveSMS(Base):
    __tablename__ = "ReceiveSMS"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer)
    receive = Column(Boolean, default=False)


class StoreConfig(Base):
    __tablename__ = "TableConfig"

    id = Column(Integer, primary_key=True, index=True)
    color_code = Column(String(100))
    show_logo = Column(Boolean, default=False)
    send_link = Column(Boolean, default=False)
    user_id = Column(Integer)


class SurveyQ(Base):
    __tablename__ = "SurveyQ"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(String(200))
    answerType = Column(Integer, default=0)
    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="RESTRICT"), nullable=True
    )
    survey_q_rel = relationship("SurveyQAnswers", back_populates="question_id_rel")
    store_id_rel = relationship("Members", back_populates="survey_q_rel")


class SurveyQAnswers(Base):
    __tablename__ = "SurveyQAnswers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    value = Column(Integer)
    question_type = Column(Integer)
    question_id = Column(Integer, ForeignKey("SurveyQ.id", ondelete="RESTRICT"))
    question_id_rel = relationship("SurveyQ", back_populates="survey_q_rel")


class SubmitAnswer(Base):
    __tablename__ = "SubmitAnswers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer)
    question_answer = Column(String(200))
    submit_time = Column(String(200))
    store_id = Column(String(200))


class SMSInfo(Base):
    __tablename__ = "SMSInfo"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DATETIME, default=datetime.utcnow())
    receiver = Column(String(200))
    sender = Column(String(200))
    text = Column(Text)
    is_sending = Column(Boolean, default=False)
    store_id = Column(String(200))


class Banner(Base):
    __tablename__ = "Banner"

    id = Column(Integer, primary_key=True, index=True)
    banner_link = Column(String(200))
    image_address = Column(String(200))


class DefaultIcons(Base):
    __tablename__ = "default_icons"

    id = Column(Integer, primary_key=True, index=True)
    link_address = Column(String(200))
    is_used = Column(Boolean, default=False)
    group_type = Column(Integer)
    size = Column(String)


class Admin(Base):
    __tablename__ = "admin"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(200))
    password = Column(String(200))


class CategoryIcons(Base):
    __tablename__ = "category_icons"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(200))


class AdminUser(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    password = Column(String(200))
    email = Column(String(200))


class AccessType(Base):
    __tablename__ = "AccessType"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    access_dashboard = Column(Boolean, default=True)
    access_menu_maker = Column(Boolean, default=True)
    access_share = Column(Boolean, default=True)
    access_contacts = Column(Boolean, default=True)
    access_analyze = Column(Boolean, default=True)
    templates_access = Column(JSON)
    price_control = Column(Boolean, default=True)
    event_notification = Column(Boolean, default=True)
    send_sms = Column(Boolean, default=True)
    sms_survey = Column(Boolean, default=True)
    send_sms_ad = Column(Boolean, default=True)
    access_id_rel = relationship("Subscription", back_populates="access_id_rel")
    stores_rel = relationship("Members", back_populates="access_type_rel")


class AppVersion(Base):
    __tablename__ = "appversion"

    id = Column(Integer, primary_key=True, index=True)
    version = Column(Integer, default=1)


class Discounts(Base):
    __tablename__ = "Discounts"

    id = Column(Integer, primary_key=True, index=True)
    expire_date = Column(DATETIME, nullable=False)
    active = Column(Boolean, default=True)
    title = Column(String(200))
    multi_use = Column(Boolean, default=False)
    discount_percent = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)


class DiscountUsed(Base):
    __tablename__ = "DiscountUsed"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    discount_code = Column(String(200))
    status_used = Column(Boolean, default=False)
    resNum = Column(String(200))
    expire_time = Column(DATETIME)


class Log(Base):
    __tablename__ = "Log"

    id = Column(Integer, primary_key=True, index=True)
    time = Column(DATETIME, default=datetime.utcnow())
    user_id = Column(Integer)
    ip = Column(String(200))
    page = Column(String(100))


class OnlineOrders(Base):
    __tablename__ = "OnlineOrders"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer)
    unique_address = Column(String(200))
    form_type = Column(Integer, default=0)
    order_time = Column(DATETIME, default=datetime.utcnow())
    shop_id = Column(Integer, default=0)
    customer_name = Column(String(200))
    cellphone = Column(String(200))
    address = Column(String(200))
    description = Column(String(200))
    room_number = Column(String(200))
    table_number = Column(String(200))
    discount_code = Column(String(200))
    discount = Column(Integer, default=0)
    payment_method = Column(Integer, default=1)
    payment_method_id = Column(Integer)
    authority = Column(String(200), nullable=True)
    total_price = Column(Float, default=0.0, nullable=True)
    # =0 pardakht nashode 1=pardakht shdoe 2= cancel shode
    payment_status = Column(String(200))
    # 0= dar hale barresi 1 = taeid shode 2= ersal shode 3 = cancel shode
    order_status = Column(Integer, default=0)
    order_items_rel = relationship("OrderItem", back_populates="order_items_rel")
    customer_id = Column(
        Integer, ForeignKey("customer.id", ondelete="SET NULL"), nullable=True
    )

    couriers_id = Column(Integer, ForeignKey("couriers.id", ondelete="SET NULL"), nullable=True)
    couriers_fee = Column(Float, default=0, nullable=True)
    courier = relationship("Courier", backref="orders") 


class OrderItem(Base):
    __tablename__ = "OrderItems"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("OnlineOrders.id", ondelete="RESTRICT"))
    product_id = Column(Integer)
    quantity = Column(Integer)
    product_type = Column(String(200))
    price = Column(Integer)
    unit_price = Column(Integer)
    size = Column(String(200), nullable=True)
    order_items_rel = relationship("OnlineOrders", back_populates="order_items_rel")


class PaymentMethods(Base):
    __tablename__ = "PaymentMethods"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    description = Column(String(200))
    enabled = Column(Boolean, default=True)


class Waiter(Base):
    __tablename__ = "Waiter"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer)
    name = Column(String(200))
    verification_code = Column(String(10))
    expire_otp_date = Column(DATETIME)
    active = Column(Boolean, default=True)
    phone = Column(String(200))
    serve_table_from = Column(Integer, default=0)
    serve_table_to = Column(Integer, default=0)
    active_weekdays = Column(JSON)
    work_hour_from = Column(Integer, default=0)
    work_hour_to = Column(Integer, default=0)
    serve_as_waiter = Column(Boolean, default=True)
    serve_as_reception = Column(Boolean, default=False)


class DiscountCode(Base):
    __tablename__ = "discount_codes"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(60), nullable=False)
    code = Column(String(10), unique=True, nullable=False, index=True)
    expire_date = Column(DATETIME, nullable=True)
    percent = Column(Float, nullable=True)
    store_id = Column(Integer, nullable=False)
    shop_id = Column(Integer, nullable=True)
    max_use_count = Column(Integer, default=0)
    creation_date = Column(DATETIME)
    used_count = Column(Integer, default=0)


class ContactUs(Base):
    __tablename__ = "contact_us"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(200))
    message = Column(Text)
    created_at = Column(DATETIME, default=datetime.utcnow)

class ClientBanner(Base):
    __tablename__ = "client_banner"

    id = Column(Integer, primary_key=True, index=True)
    link = Column(String(200))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    store_id_rel = relationship("Members", back_populates="store_id_banner")
    image_path = Column(String(200), nullable=False)


class Labels(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    store_id_rel = relationship("Members", back_populates="store_id_label")
    label_foods = relationship("FoodLabels", back_populates="label_id_rel")
    color = Column(String(200), nullable=False)
    is_available = Column(Boolean, default=False)


class FoodLabels(Base):
    __tablename__ = "food_labels"

    id = Column(Integer, primary_key=True, index=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"))
    label_id = Column(Integer, ForeignKey("labels.id", ondelete="CASCADE"))
    food_id_rel = relationship("Foods", back_populates="food_labels")
    label_id_rel = relationship("Labels", back_populates="label_foods")


class FoodSync(Base):
    __tablename__ = "food_sync"

    id = Column(Integer, primary_key=True, index=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"))
    food_id_rel = relationship("Foods", back_populates="food_sync")
    sync_id = Column(Integer, nullable=False)


class Courier(Base):
    __tablename__ = "couriers"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id", ondelete="CASCADE"))
    name = Column(String(100), nullable=False)
    mobile_number = Column(String(20), nullable=False)
    working_hours = Column(String(200), nullable=False)
    description = Column(String(300), nullable=True)
    delivery_fee_grade1 = Column(Integer, nullable=False, default=0)
    delivery_fee_grade2 = Column(Integer, nullable=False, default=0)
    currency = Column(String(50), nullable=False)

    store_id_val = relationship("Members", back_populates="store_id_couriers")


class Branch(Base):
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    logo = Column(String(255))
    background_image = Column(String(255))
    background_video = Column(String(255))
    welcome_text = Column(Text)
    website = Column(String(255))
    email_addresses = Column(JSON)
    display_type = Column(String(50), default="vertical")
    phone_number = Column(String(50))
    additional_phone_numbers = Column(JSON)
    location_map = Column(String(255))
    address = Column(String(255))
    color_code = Column(String(7))
    user_id = Column(Integer)
    menu_link = Column(String(255), nullable=True)
    # Relationships
    social_media = relationship(
        "SocialMedia", back_populates="branch", cascade="all, delete-orphan"
    )
    gallery_items = relationship(
        "Gallery", back_populates="branch", cascade="all, delete-orphan"
    )
    banners = relationship(
        "BannerClient", back_populates="branch", cascade="all, delete-orphan"
    )
    hero_sections = relationship(
        "HeroSection", back_populates="branch", cascade="all, delete-orphan"
    )


class SocialMedia(Base):
    __tablename__ = "social_media"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"))
    platform = Column(
        String(100), nullable=False
    )  # e.g., "Instagram", "Telegram", "WhatsApp"
    identifier = Column(String(255), nullable=False)  # ID, username, or phone number

    # Relationship
    branch = relationship("Branch", back_populates="social_media")


class Gallery(Base):
    __tablename__ = "gallery"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"))
    image_url = Column(String(255), nullable=False)
    title = Column(String(200))
    description = Column(Text)
    display_order = Column(Integer, default=0)

    # Relationship
    branch = relationship("Branch", back_populates="gallery_items")


class BannerClient(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"))
    image_url = Column(String(255), nullable=False)
    link_url = Column(String(255))
    title = Column(String(200))
    display_order = Column(Integer, default=0)

    # Relationship
    branch = relationship("Branch", back_populates="banners")


class HeroSection(Base):
    __tablename__ = "hero_sections"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"))
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(255))
    display_order = Column(Integer, default=0)

    # Relationship
    branch = relationship("Branch", back_populates="hero_sections")


class Customer(Base):
    __tablename__ = "customer"

    id = Column(Integer, primary_key=True, index=True)
    fname = Column(String(200), nullable=True)
    lname = Column(String(200), nullable=True)
    cellphone = Column(String(200), unique=True, nullable=True)
    address = Column(String(200), nullable=True)
    register_id = Column(String(200), nullable=True)  # Can be repeated
    register_date = Column(DATETIME, nullable=True)
    email = Column(String(200), nullable=True)
    birth_date = Column(DATETIME, nullable=True)
    verification_code = Column(String(9), nullable=True)
    otp_expire_date = Column(DATETIME, nullable=True)
    last_login = Column(DATETIME, nullable=True)
    city = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    label_id = Column(Integer, nullable=True)
    status = Column(Integer, nullable=False, default=1)
    store_links = relationship(
        "StoreCustomer", back_populates="customer", cascade="all, delete-orphan"
    )


class Updates(Base):
    __tablename__ = "updates"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200))
    text = Column(Text)
    publishdate = Column(DATETIME)
    expiredate = Column(DATETIME)


class StoreCustomer(Base):
    __tablename__ = "store_customer"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(
        Integer, ForeignKey("customer.id", ondelete="CASCADE"), nullable=False
    )
    store_id = Column(
        Integer, ForeignKey("stores.id", ondelete="CASCADE"), nullable=False
    )
    Tag_name = Column(String(200), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="store_links")
    store = relationship("Members", back_populates="customer_links")
    register_id = Column(String(200), nullable=True)
    # Unique constraint
    __table_args__ = (
        UniqueConstraint("customer_id", "store_id", name="uc_customer_store"),
    )
