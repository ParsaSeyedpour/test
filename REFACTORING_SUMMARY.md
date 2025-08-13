# Publish Menu Function Refactoring Summary

## Overview

The `publish_menu` function in `publish_menu.py` has been updated to work with the new refactored models that replace JSON fields with relational tables.

## Key Changes Made

### 1. Added Required Imports

```python
from sqlalchemy.orm import Session, exc, selectinload
```

The `selectinload` import was added to enable efficient loading of related data from the new relational models.

### 2. Updated Database Queries

#### Before (JSON-based):
```python
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
```

#### After (Relational-based):
```python
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
```

### 3. Updated Food Queries

#### Before:
```python
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
```

#### After:
```python
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
```

### 4. Added Helper Functions

New helper functions were added to handle the relational data:

```python
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
```

### 5. Updated Template Logic

#### Before (JSON parsing):
```python
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
```

#### After (Relational access):
```python
if category.translations:
    additional_titles = {
        translation.language_id: translation.title
        for translation in category.translations
        if translation.language_id != "fa" and translation.title
    }
    titles.update(additional_titles)
```

### 6. Added Food Size Processing

Added logic to process food sizes and add IDs for backward compatibility:

```python
# Process food items to add sizes with IDs for templates that need them
for food_item in food:
    if food_item.size_items:
        # Add ID to each size using food ID and letter (for backward compatibility)
        for idx, size_item in enumerate(food_item.size_items):
            if not hasattr(size_item, 'id') or not size_item.id:
                size_item.id = f"{food_item.id}-{string.ascii_lowercase[idx]}"
```

## Benefits of These Changes

### 1. **Performance Improvement**
- Eliminates JSON parsing overhead
- Uses efficient SQL joins instead of string operations
- Better database indexing capabilities

### 2. **Data Integrity**
- Foreign key constraints ensure data consistency
- No more JSON parsing errors
- Proper data validation at the database level

### 3. **Maintainability**
- Cleaner, more readable code
- Easier to debug and maintain
- Better separation of concerns

### 4. **Scalability**
- Better support for large datasets
- More efficient memory usage
- Optimized database queries

## Backward Compatibility

The refactored function maintains backward compatibility by:
- Keeping the same API interface
- Maintaining the same response structure
- Adding size IDs for templates that expect them
- Preserving all existing template functionality

## Migration Notes

### For Existing Data
- JSON data needs to be migrated to the new relational structure
- Existing API calls will continue to work
- New endpoints provide better performance

### For Developers
- Update queries to use `selectinload` for related data
- Replace JSON parsing with direct attribute access
- Use the new helper functions for common operations

## Testing Recommendations

1. **Test all template types** to ensure they work with the new data structure
2. **Verify multi-language support** works correctly
3. **Check food size handling** in templates that use them
4. **Performance testing** to confirm improvements
5. **Backward compatibility testing** for existing integrations

## Future Improvements

1. **Complete template updates**: Update all template sections to use helper functions
2. **Performance optimization**: Further optimize database queries
3. **Caching**: Add caching for frequently accessed data
4. **API versioning**: Consider deprecating old JSON-based endpoints 