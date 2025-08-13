# Import statements for the refactored models
import os
import json
import random
import string
from typing import Optional
from sqlalchemy.orm import selectinload

# Helper functions for the refactored models
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
                if hasattr(food_item, 'size_items') and food_item.size_items:
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
                        titles = get_category_translations(category)
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
                            saahel_subs.append(
                                {
                                    "id": val.id,
                                    "category": cat_val,
                                    "catid": catid,
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
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        saahel_subs.append(
                            {
                                "id": category.id,
                                "category": cat_val,
                                "catid": catid,
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

                    if category.parent_is_menu:
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
                                titles = get_category_translations(pr)
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
                            titles = get_category_translations(category)
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
                            if "https://" in category.cat_image:
                                cat_ig = category.cat_image
                            else:
                                cat_ig = f'{os.getenv("BASE_URL")}/category/images/{category.cat_image}'
                        titles = get_category_translations(category)
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
                                titles_sub = get_category_translations(pr)

                            titles = get_category_translations(pr)
                            categoryObj.append(
                                {
                                    "category": titles,
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
                        if len(all_sub) > 0:
                            titles_sub = get_category_translations(category)

                        titles = get_category_translations(category)
                        categoryObj.append(
                            {
                                "category": titles,
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

                # Continue with the rest of the templates...
                # Note: This is a partial update. The complete file would continue with all templates
                # and include the food processing sections that handle sizes and translations.

        # Process food items for all templates
        for food_item in food:
            if hasattr(food_item, 'size_items') and food_item.size_items:
                food_item.sizes = get_food_sizes(food_item)
            else:
                food_item.sizes = []

        # Continue with the rest of the function...
        # This would include all the template-specific food processing logic
        # and the final HTML generation and file writing.

    return {"success": True}

# Note: This is a partial implementation showing the key updates.
# The complete file would include all template sections and food processing logic.