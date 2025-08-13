# Menu Management System API

A comprehensive FastAPI-based menu management system for restaurants and food services, providing menu creation, order management, and multi-language support.

## Overview

This system provides a complete solution for managing restaurant menus, handling online orders, and supporting multiple languages and currencies. It's built with FastAPI and includes features for menu publishing, order processing, and customer management.

## Recent Refactoring (v2.1)

### Model Refactoring: JSON Fields → Relational Tables

The system has been refactored to replace JSON fields with proper relational tables for better performance, data integrity, and maintainability.

#### What Changed
- **Before**: Used JSON fields (`multi_language_data`, `sizes`) for storing multilingual content and food sizes
- **After**: Implemented dedicated relational tables with proper foreign key constraints

#### New Relational Models

##### FoodLanguage
```python
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
```

##### FoodSize
```python
class FoodSize(Base):
    __tablename__ = "food_sizes"
    
    id = Column(Integer, primary_key=True)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="CASCADE"))
    type_size = Column(String(50))
    status = Column(Integer, default=1)
    image_url = Column(String(300))
    
    food = relationship("Foods", back_populates="size_items")
    translations = relationship("FoodSizeTranslation", back_populates="size", cascade="all, delete")
```

##### FoodCategoryTranslation
```python
class FoodCategoryTranslation(Base):
    __tablename__ = "food_category_translations"
    
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, ForeignKey("food_category.id", ondelete="CASCADE"))
    language_id = Column(String(10))
    title = Column(String(200))
    description = Column(Text)
    
    __table_args__ = (UniqueConstraint('category_id', 'language_id'),)
    category = relationship("FoodCategory", back_populates="translations")
```

#### Benefits of Refactoring
- ✅ **Better Performance**: Proper indexing and query optimization
- ✅ **Data Integrity**: Foreign key constraints and validation
- ✅ **Easier Queries**: Standard SQL joins instead of JSON parsing
- ✅ **Scalability**: Better support for large datasets
- ✅ **Maintainability**: Cleaner code and easier debugging

#### Migration Notes
- Existing JSON data can be migrated to the new relational structure
- The API maintains backward compatibility where possible
- New endpoints use the optimized relational models
- Legacy endpoints still work but may be deprecated in future versions

## Features

- **Menu Management**: Create, edit, and publish restaurant menus
- **Order Processing**: Handle online orders with real-time status updates
- **Multi-language Support**: Support for multiple languages and currencies
- **Template System**: Multiple menu templates (Atlas, Sayeh, Shabnam, Sorme, Yakh, Shiraz, Zomorod, Gerdoo, Sepehr, Custom)
- **Category Management**: Hierarchical food categories with subcategories
- **Food Items**: Manage food items with sizes, prices, and descriptions
- **Image Management**: Upload and optimize menu images and backgrounds
- **SMS Notifications**: Automated SMS notifications for orders
- **Authentication**: JWT-based authentication system
- **Database Integration**: SQLAlchemy ORM with PostgreSQL support

## API Endpoints

### Menu Management

#### Create Menu
- **POST** `/menu/create_menu` - Create a new menu
- **POST** `/menu/edit_menu/{menu_id}` - Edit existing menu
- **GET** `/menu/all_menus` - Get all menus for a user
- **GET** `/menu/get_foods` - Get all foods in a menu
- **GET** `/menu/v2/get_foods` - Get foods with enhanced features

#### Menu Publishing
- **POST** `/menu/publish_menu/{menu_id}` - Publish a menu with template rendering
- **GET** `/menu/menu/show/{store_url}` - Display published menu
- **GET** `/menu/temp_preview/{temp_address}` - Preview menu templates
- **GET** `/menu/get_all_templates` - Get available template options

#### Menu Structure
- **GET** `/menu/v2/{menu_id}` - Get menu structure with nested categories
- **GET** `/menu/v2/items/menu/{id}` - Get detailed menu information
- **GET** `/menu/v2/items/category/{id}` - Get category details
- **GET** `/menu/v2/items/food/{id}` - Get food item details

### Order Management

#### Order Creation
- **POST** `/menu/create_order` - Create a new order
- **POST** `/menu/create_step_two` - Complete order with customer details
- **GET** `/menu/get_order_detail/{unique_address}` - Get order details
- **GET** `/menu/get_order_detail_2/{unique_address}` - Get enhanced order details

#### Order Management
- **PUT** `/menu/orders/{order_id}` - Update existing order
- **PUT** `/menu/v2/orders/{order_id}` - Enhanced order update
- **POST** `/menu/change_order_status` - Change order status
- **GET** `/menu/store_order` - Get store orders with pagination
- **GET** `/menu/v2/store_order` - Enhanced store orders
- **GET** `/menu/new_order_count` - Get count of new orders

#### Cart Operations
- **POST** `/menu/cart_order` - Process cart order

### Image Management

- **POST** `/menu/upload_menu_template/` - Upload menu template images
- **POST** `/menu/menu_background/` - Upload and optimize menu background images
- **GET** `/menu/images/{image_address}/{image_name}` - Serve menu images

### Authentication & User Management

- **POST** `/menu/token` - User authentication
- **GET** `/menu/check_order_feature` - Check user permissions

## Data Models

### Core Models

#### Menu
```python
class Menu(BaseModel):
    type: Literal["menu"]
    id: str
    title: str
    description: str
    theme_url: str
    currency: str
    show_price: bool
    show_store_info: bool
    is_primary: bool
    template_name: str
    background_image: List[str]
    multi_language_data: Optional[List[LanguageData]]
```

#### Category
```python
class Category(BaseModel):
    type: Literal["category"]
    id: str
    title: str
    cat_image: str
    description: str
    parent_id: Optional[int]
    parent_is_menu: bool
    menu_id: int
    enabled: int
    multi_language_data: Optional[List[MultiLanguage]]
    children: List[Union["Category", "Food"]]
```

#### Food
```python
class Food(BaseModel):
    type: Literal["food"]
    id: str
    menu_id: int
    category_id: int
    title: str
    englishTitle: str
    price: int
    food_image: List[str]
    food_video: str
    description: str
    discount: Optional[int]
    ready_by_time: Optional[int]
    available: int
    sizes: Optional[List[Any]]
    multi_language_data: Optional[List[MultiLanguage]]
```

### Order Models

#### Order
```python
class Order(BaseModel):
    id: int
    store_id: int
    customer_name: str
    cellphone: str
    address: str
    total_price: float
    order_status: int
    payment_status: str
    unique_address: str
    order_time: datetime
```

#### OrderItem
```python
class OrderItem(BaseModel):
    id: int
    order_id: int
    product_id: int
    product_type: str
    quantity: int
    unit_price: int
    price: int
    size: Optional[str]
```

## Template System

The system supports multiple menu templates:

- **Atlas** - Modern, responsive design
- **Sayeh** - Elegant and clean layout
- **Shabnam** - Traditional Persian style
- **Sorme** - Sophisticated design
- **Yakh** - Minimalist approach
- **Shiraz** - Classic restaurant style
- **Zomorod** - Contemporary design
- **Gerdoo** - Modern card-based layout
- **Sepehr** - Premium template
- **Custom** - User-defined templates

Each template supports:
- Customizable colors and backgrounds
- Multi-language content
- Responsive design
- SEO optimization

## Multi-language Support

The system supports multiple languages with:
- Language-specific titles and descriptions
- Currency conversion
- Localized content management
- RTL language support (Persian, Arabic)

## Installation & Setup

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Redis (for caching)
- SMS service (Kavenegar)

### Dependencies
```bash
pip install fastapi sqlalchemy psycopg2-binary passlib python-jose[cryptography] fastapi-pagination kavenegar beautifulsoup4
```

### Environment Variables
```bash
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@localhost/dbname
MENU_BASE_URL=https://yourdomain.com
MENU_FOLDER_NAME=menu_templates
BASE_URL=https://yourdomain.com
```

### Database Setup
```python
from database import engine
from models import Base

Base.metadata.create_all(bind=engine)
```

## Usage Examples

### Creating a Menu
```python
import requests

menu_data = {
    "title": "Main Menu",
    "description": "Our restaurant's main menu",
    "theme_url": "atlas",
    "currency": "USD",
    "show_price": True,
    "show_store_info": True,
    "is_primary": True,
    "template_name": "atlas"
}

response = requests.post(
    "http://localhost:8000/menu/create_menu",
    json=menu_data,
    headers={"Authorization": f"Bearer {token}"}
)
```

### Publishing a Menu
```python
response = requests.post(
    f"http://localhost:8000/menu/publish_menu/{menu_id}",
    headers={"Authorization": f"Bearer {token}"}
)
```

### Creating an Order
```python
order_data = {
    "product_id": [1, 2],
    "quantity": [2, 1],
    "unit_price": [1500, 2000],
    "product_type": ["food", "food"],
    "discount": 0,
    "customer_name": "John Doe",
    "cellphone": "09123456789",
    "address": "123 Main St",
    "description": "Extra spicy please",
    "place_number": "Table 5",
    "store_id": 1
}

response = requests.post(
    "http://localhost:8000/menu/create_order",
    json=order_data
)
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Input validation with Pydantic
- SQL injection protection

## Performance Features

- Database connection pooling
- Pagination for large datasets
- Image optimization and compression
- Efficient database queries with joins
- Caching support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please contact the development team or create an issue in the repository.

## Changelog

### Version 2.1 (Latest)
- **Model Refactoring**: Replaced JSON fields with relational tables
- **Performance Improvements**: Better database queries and indexing
- **Data Integrity**: Added foreign key constraints and validation
- **Backward Compatibility**: Maintained API compatibility during transition

### Version 2.0
- Enhanced multi-language support
- Improved template system
- Better order management
- Performance optimizations

### Version 1.0
- Initial release
- Basic menu management
- Order processing
- Template support 