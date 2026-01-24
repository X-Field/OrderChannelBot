from catalog import filter_catalog

UP_CHAPTER_HEADER_NAME = "Верхний раздел каталога"
DOWN_CHAPTER_HEADER_NAME = "Подраздел каталога"
ID_HEADER_NAME = "id"

def get_categories(chapter_header_name:str, catalog: list[list[str]]) -> list[str]:
    categories = set()
    headers_index = catalog[0].index(chapter_header_name)
    for row in catalog[1:]:
        categories.add(row[headers_index])
    return list(categories)


def get_all_up_categories(catalog: list[list[str]]) -> list[str]:
    return list(set(get_categories(UP_CHAPTER_HEADER_NAME, catalog)))



def get_all_down_categories(up_chapter_name, catalog: list[list[str]]) -> list[str]:
    filter_dict = {UP_CHAPTER_HEADER_NAME: up_chapter_name}
    new_catalog = filter_catalog(filter_dict=filter_dict, catalog=catalog)
    return list(set(get_categories(DOWN_CHAPTER_HEADER_NAME, new_catalog)))


def get_products(up_chapter_name:str, down_chapter_name:str, catalog:list[list[str]]) -> list[tuple[str, str]]:
    filter_dict = {
        UP_CHAPTER_HEADER_NAME: up_chapter_name,
        DOWN_CHAPTER_HEADER_NAME: down_chapter_name,
    }
    products = filter_catalog(filter_dict, catalog)
    return [(row[0], row[1]) for row in products]


def get_product(id:str, catalog: list[list[str]]) -> list[str]:
    filter_dict = {ID_HEADER_NAME: id}
    return filter_catalog(filter_dict,catalog)[1]
