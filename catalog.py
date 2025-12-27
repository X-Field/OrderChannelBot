import csv
from config import CATALOG_PATH

def load_catalog():
    with open(CATALOG_PATH, encoding="utf-8") as file:
        reader = csv.reader(file, delimiter=";")
        catalog = list(reader)
    return catalog


def filter_catalog(filter_dict: dict[str, str], catalog: list[list[str]]) -> list[list[str]]:
    """
    :param filter_dict: фильтр в виде словаря key: столбец, value: значение
    :param catalog: текущий каталог
    :return: отфильтрованный каталог по нужным столбцам
    """
    headers = catalog[0]
    data = catalog [1:]
    result = data.copy()
    for key in filter_dict.keys():
        index_header = headers.index(key)
        result = filter(lambda x: x[index_header] == filter_dict[key], result)

    final_catalog = list(result)
    final_catalog.insert(0, headers)
    return final_catalog


if __name__ == "__main__":
    catalog = load_catalog()
    filtred_data = filter_catalog({"Цвет товара": "Синий"}, catalog)
    print(filtred_data[0])