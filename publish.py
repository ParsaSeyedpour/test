

@router.post("/publish_menu/{menu_id}")
async def publish_a_menu(
    menu_id: int,
    theme: Optional[PublishMenu] = None,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
                .join(models.MenuIDS, models.MenuIDS.food_id == models.Foods.id)
                .filter(
                    models.MenuIDS.menu_id == all_menus.id,
                    models.MenuIDS.cat_id == category.id,
                )
                .order_by(models.Foods.position.asc())
                .all()
            )
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