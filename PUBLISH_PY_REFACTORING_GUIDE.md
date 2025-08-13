# Publish.py Refactoring Guide

## Overview

This document outlines the changes needed to update the `publish.py` file to work with the new refactored models that replace JSON fields with relational tables.

## Key Changes Required

### 1. **Database Queries Updates**

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

### 2. **Food Queries Updates**

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

### 3. **Multi-language Data Handling**

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

### 4. **Food Sizes Handling**

#### Before (JSON parsing):
```python
if len(foodObj.sizes) > 0:
    foodObj.sizes = [
        {
            "id": f"{foodObj.id}-{idx + 1}",
            "title": it.get("title", ""),
            "price": it.get("price", 0)
        }
        for idx, it in enumerate(foodObj.sizes)
    ]
```

#### After (Relational access):
```python
if hasattr(foodObj, 'size_items') and foodObj.size_items:
    foodObj.sizes = get_food_sizes(foodObj)
```

## Template-Specific Updates

### Yakh Template
- Replace JSON parsing with `get_category_translations(category)`

### Sepehr Template
- Update parent category handling
- Update subcategory handling
- Replace JSON parsing with relational access

### Ivaan Template
- Update parent category handling
- Replace JSON parsing with relational access

### Other Templates
- Similar pattern: replace `multi_language_data` JSON parsing with `category.translations` access
- Replace `food.sizes` JSON parsing with `food.size_items` access

## Helper Functions Added

### `get_category_translations(category)`
```python
def get_category_translations(category):
    """Get category translations from the new relational model"""
    if not hasattr(category, 'translations') or not category.translations:
        return {}
    
    titles = {"fa": category.title}
    additional_titles = {
        translation.language_id: translation.title
        for translation in category.translations
        if translation.language_id != "fa" and translation.title
    }
    titles.update(additional_titles)
    return titles
```

### `get_food_sizes(food)`
```python
def get_food_sizes(food):
    """Get food sizes from the new relational model"""
    if not hasattr(food, 'size_items') or not food.size_items:
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
        if hasattr(size_item, 'translations') and size_item.translations:
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

## Files to Update

### 1. `publish.py` - Main Function
- Update database queries with `selectinload`
- Replace JSON parsing with helper functions
- Update all template sections

### 2. `publish_menu_after_subscription` Function
- Same updates as main function
- Update database queries
- Replace JSON parsing

## Benefits of These Changes

1. **Performance**: Eliminates JSON parsing overhead
2. **Data Integrity**: Uses proper foreign key constraints
3. **Maintainability**: Cleaner, more readable code
4. **Scalability**: Better support for large datasets
5. **Consistency**: Standard SQL operations instead of string parsing

## Testing Checklist

- [ ] Test all template types (Dalia, Shabnam, Sorme, Yakh, Shiraz, etc.)
- [ ] Verify multi-language support works correctly
- [ ] Check food size handling in templates
- [ ] Test backward compatibility
- [ ] Performance testing to confirm improvements

## Migration Notes

- Existing JSON data needs to be migrated to relational structure
- API maintains backward compatibility
- New endpoints provide better performance
- Legacy JSON-based logic can be deprecated in future versions 