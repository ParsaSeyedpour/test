# Publish.py Update Status

## Overview

This document tracks the progress of updating the `publish.py` file to work with the new refactored models.

## ✅ **Completed Updates**

### 1. **Added Imports and Helper Functions**
- ✅ Added `selectinload` import
- ✅ Added `get_category_translations()` helper function
- ✅ Added `get_food_sizes()` helper function
- ✅ Added function documentation

### 2. **Updated Database Queries**
- ✅ Updated categories query with `selectinload(models.FoodCategory.translations)`
- ✅ Updated parent_cats query with `selectinload(models.FoodCategory.translations)`
- ✅ Updated food query with `selectinload` for translations and sizes
- ✅ Added food size processing for backward compatibility

### 3. **Updated Template Sections**
- ✅ Updated Yakh template (first instance) to use `get_category_translations()`

## 🔄 **In Progress**

### Template Section Updates
- 🔄 Update remaining Yakh template instance
- 🔄 Update Sepehr template instances (multiple locations)
- 🔄 Update Ivaan template instances
- 🔄 Update other template instances

## ❌ **Still Need to Update**

### 1. **Remaining Multi-language Data Handling**
The following sections still use the old JSON parsing approach:

#### Yakh Template (Second Instance)
```python
# Lines ~3150-3184 (approximate)
if (
    hasattr(category, "multi_language_data")
    and category.multi_language_data
):
    try:
        lang_data = json.loads(category.multi_language_data)
        # ... JSON parsing logic
    except json.JSONDecodeError:
        titles = {}
```

#### Sepehr Template (Multiple Instances)
```python
# Lines ~3470-3500 (approximate)
if (
    hasattr(pr, "multi_language_data")
    and pr.multi_language_data
):
    try:
        lang_data = json.loads(pr.multi_language_data)
        # ... JSON parsing logic
    except json.JSONDecodeError:
        titles = {}
```

#### Ivaan Template
```python
# Lines ~3630-3650 (approximate)
if pr.multi_language_data:
    lang_data = json.loads(pr.multi_language_data)
    # ... JSON parsing logic
```

### 2. **Food Size Handling**
All instances of `foodObj.sizes` JSON parsing need to be updated:

```python
# Current approach (needs updating)
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

Should become:
```python
# New approach
if hasattr(foodObj, 'size_items') and foodObj.size_items:
    foodObj.sizes = get_food_sizes(foodObj)
```

### 3. **Menu Multi-language Data**
Menu-level multi-language data handling needs updating:

```python
# Current approach (needs updating)
if hasattr(find_menu, "multi_language_data") and find_menu.multi_language_data:
    for lang_data in json.loads(find_menu.multi_language_data):
        # Process language data
```

Should become:
```python
# New approach
if hasattr(find_menu, "translations") and find_menu.translations:
    for translation in find_menu.translations:
        # Process translation data
```

## 📊 **Progress Summary**

- **Database Queries**: 100% Complete ✅
- **Helper Functions**: 100% Complete ✅
- **Template Updates**: ~15% Complete 🔄
- **Food Size Handling**: 0% Complete ❌
- **Menu Multi-language**: 0% Complete ❌

**Overall Progress: ~25% Complete**

## 🚀 **Next Steps**

### Immediate Actions
1. **Complete Template Updates**: Update remaining template sections systematically
2. **Update Food Size Handling**: Replace all JSON parsing with relational access
3. **Update Menu Multi-language**: Update menu-level translation handling

### Recommended Approach
Since there are duplicate sections in the file, consider:
1. **Systematic Replacement**: Update one section at a time with unique context
2. **Create New Function**: Build a new version of the function with all updates
3. **Use Search and Replace**: Target specific patterns with unique identifiers

### Testing Priority
1. **Database Queries**: Verify selectinload works correctly
2. **Template Rendering**: Test all template types
3. **Multi-language Support**: Verify translations display correctly
4. **Food Sizes**: Ensure sizes work in all templates
5. **Backward Compatibility**: Verify existing functionality still works

## 🔧 **Technical Notes**

### Duplicate Sections Issue
The file contains duplicate template sections, making direct updates challenging. Consider:
- Using more context to uniquely identify sections
- Creating a new version of the function
- Using pattern-based search and replace

### Helper Function Usage
The helper functions are designed to be backward compatible:
- Check for attribute existence before accessing
- Provide fallback values when data is missing
- Maintain the same output structure for templates

### Performance Improvements
- Eliminates JSON parsing overhead
- Uses efficient SQL joins
- Better database indexing capabilities
- Reduced memory usage 