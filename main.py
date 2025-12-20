#!/usr/bin/python
import telebot
from telebot import types
import pandas as pd
import os

API_TOKEN = '8433567433:AAH9bDuB8tEmiQiZIJfkEN3_qI_RmvhoJEo'
bot = telebot.TeleBot(API_TOKEN)


class CatalogManager:
    def __init__(self, catalog_path="data/catalog"):
        self.catalog_path = catalog_path
        self.dataframes = {}
        if not os.path.exists(self.catalog_path):
            os.makedirs(self.catalog_path)
        self.load_all_data()

    def load_all_data(self):
        for file in os.listdir(self.catalog_path):
            if file.endswith('.csv'):
                file_path = os.path.join(self.catalog_path, file)
                category = file.replace('.csv', '')
                df = pd.read_csv(file_path)
                self.dataframes[category] = df

    def get_filtered_data(self, category, filters=None, columns=None):
        if category not in self.dataframes:
            file_path = os.path.join(self.catalog_path, f"{category}.csv")
            if os.path.exists(file_path):
                self.dataframes[category] = pd.read_csv(file_path)
            else:
                return pd.DataFrame()

        df = self.dataframes[category].copy()

        if filters:
            for column, value in filters.items():
                if column in df.columns:
                    if isinstance(value, list):
                        df = df[df[column].isin(value)]
                    elif callable(value):
                        df = df[df[column].apply(value)]
                    else:
                        df = df[df[column] == value]

        if columns:
            available_columns = [col for col in columns if col in df.columns]
            if available_columns:
                df = df[available_columns]

        return df

    def get_categories(self):
        categories = []
        for file in os.listdir(self.catalog_path):
            if file.endswith('.csv'):
                categories.append(file.replace('.csv', ''))
        return sorted(categories)

    def get_item_by_id(self, category, item_id):
        if category in self.dataframes:
            df = self.dataframes[category]
            item = df[df['id'] == item_id]
            if not item.empty:
                return item.iloc[0].to_dict()
        return None


catalog_manager = CatalogManager()


class Paginator:
    def __init__(self, items, items_per_page=6):
        self.items = items
        self.items_per_page = items_per_page
        self.total_pages = (len(items) + items_per_page - 1) // items_per_page

    def get_page(self, page):
        if page < 1 or page > self.total_pages:
            return []
        start_idx = (page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.items[start_idx:end_idx]

    def create_keyboard(self, current_page, prefix="cat"):
        keyboard = types.InlineKeyboardMarkup(row_width=3)

        page_items = self.get_page(current_page)
        for item in page_items:
            keyboard.add(types.InlineKeyboardButton(
                text=item.capitalize(),
                callback_data=f"{prefix}:{item}"
            ))

        if self.total_pages > 1:
            nav_buttons = []
            if current_page > 1:
                nav_buttons.append(types.InlineKeyboardButton(
                    text="⬅️",
                    callback_data=f"page:{prefix}:{current_page - 1}"
                ))

            nav_buttons.append(types.InlineKeyboardButton(
                text=f"{current_page}/{self.total_pages}",
                callback_data="noop"
            ))

            if current_page < self.total_pages:
                nav_buttons.append(types.InlineKeyboardButton(
                    text="➡️",
                    callback_data=f"page:{prefix}:{current_page + 1}"
                ))

            if nav_buttons:
                keyboard.row(*nav_buttons)

        keyboard.add(types.InlineKeyboardButton(
            text="🏠 Главное меню",
            callback_data="main_menu"
        ))

        return keyboard


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    show_categories_menu(message)


@bot.message_handler(commands=['catalog'])
def show_catalog(message):
    show_categories_menu(message)


def show_categories_menu(message, page=1):
    categories = catalog_manager.get_categories()

    if not categories:
        bot.send_message(message.chat.id, "Каталог пуст")
        return

    paginator = Paginator(categories)
    keyboard = paginator.create_keyboard(page)

    bot.send_message(
        message.chat.id,
        "📚 Выберите категорию:",
        reply_markup=keyboard
    )


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "main_menu":
        show_categories_menu(call.message)
        bot.answer_callback_query(call.id)
        return

    if call.data == "back_to_categories":
        show_categories_menu(call.message)
        bot.answer_callback_query(call.id)
        return

    if call.data == "noop":
        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("page:"):
        _, prefix, page_str = call.data.split(":")
        page = int(page_str)

        if prefix == "cat":
            categories = catalog_manager.get_categories()
            paginator = Paginator(categories)
            keyboard = paginator.create_keyboard(page)

            bot.edit_message_reply_markup(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=keyboard
            )
        elif prefix.startswith("items_"):
            category = prefix.replace("items_", "")
            show_items_page(call, category, page)

        bot.answer_callback_query(call.id)
        return

    if call.data.startswith("cat:"):
        category = call.data.split(":")[1]
        show_items_page(call, category)
        return

    if call.data.startswith("item:"):
        _, category, item_id = call.data.split(":")
        show_item_details(call, category, int(item_id))
        return


def show_items_page(call, category, page=1):
    items_df = catalog_manager.get_filtered_data(category)

    if items_df.empty:
        bot.answer_callback_query(
            call.id,
            text=f"В категории '{category}' пока нет товаров",
            show_alert=True
        )
        return

    items = []
    for _, row in items_df.iterrows():
        item_text = f"<b>{row['name']}</b>\n"
        if 'description' in row:
            item_text += f"{row['description']}\n"
        if 'price' in row:
            item_text += f"💰 Цена: {row['price']} руб.\n"
        if 'stock' in row:
            item_text += f"📦 Остаток: {row['stock']} шт."
        items.append(item_text)

    paginator = Paginator(items, items_per_page=3)
    page_items = paginator.get_page(page)

    message_text = f"<b>📁 Категория: {category.capitalize()}</b>\n\n"
    message_text += "\n" + "─" * 20 + "\n\n".join(page_items)

    keyboard = types.InlineKeyboardMarkup(row_width=2)

    if paginator.total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(types.InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"page:items_{category}:{page - 1}"
            ))

        nav_buttons.append(types.InlineKeyboardButton(
            text=f"{page}/{paginator.total_pages}",
            callback_data="noop"
        ))

        if page < paginator.total_pages:
            nav_buttons.append(types.InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"page:items_{category}:{page + 1}"
            ))

        if nav_buttons:
            keyboard.row(*nav_buttons)

    for _, row in items_df.iterrows():
        if len(keyboard.keyboard) < 5:
            keyboard.add(types.InlineKeyboardButton(
                text=f"📦 {row['name']}",
                callback_data=f"item:{category}:{row['id']}"
            ))

    keyboard.add(types.InlineKeyboardButton(
        text="← Назад к категориям",
        callback_data="back_to_categories"
    ))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


def show_item_details(call, category, item_id):
    item = catalog_manager.get_item_by_id(category, item_id)

    if not item:
        bot.answer_callback_query(
            call.id,
            text="Товар не найден",
            show_alert=True
        )
        return

    message_text = f"<b>{item.get('name', 'Без названия')}</b>\n\n"

    if 'description' in item and pd.notna(item['description']):
        message_text += f"📝 {item['description']}\n\n"

    if 'price' in item and pd.notna(item['price']):
        message_text += f"💰 Цена: <b>{item['price']}</b> руб.\n"

    if 'stock' in item and pd.notna(item['stock']):
        message_text += f"📦 В наличии: {item['stock']} шт.\n"

    for key, value in item.items():
        if key not in ['id', 'name', 'description', 'price', 'stock', 'category'] and pd.notna(value):
            message_text += f"\n{key}: {value}"

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(
        text="← Назад к товарам",
        callback_data=f"cat:{category}"
    ))
    keyboard.add(types.InlineKeyboardButton(
        text="← Назад к категориям",
        callback_data="back_to_categories"
    ))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=message_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    bot.answer_callback_query(call.id)


@bot.message_handler(commands=['search'])
def search_items(message):
    bot.send_message(
        message.chat.id,
        "Введите название товара для поиска:"
    )
    bot.register_next_step_handler(message, process_search)


def process_search(message):
    search_term = message.text.lower()
    results = []

    for category in catalog_manager.get_categories():
        df = catalog_manager.get_filtered_data(category)
        if not df.empty and 'name' in df.columns:
            filtered = df[df['name'].str.lower().str.contains(search_term)]
            if not filtered.empty:
                for _, row in filtered.iterrows():
                    results.append(f"📁 {category.capitalize()}: {row['name']} - 💰 {row.get('price', '?')} руб.")

    if results:
        response = "🔍 Результаты поиска:\n\n" + "\n".join(results[:20])
        if len(results) > 20:
            response += f"\n\n... и еще {len(results) - 20} товаров"
    else:
        response = "Товары не найдены"

    bot.send_message(message.chat.id, response)


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    if message.text.lower() == 'каталог':
        show_categories_menu(message)
    else:
        bot.reply_to(message, message.text)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()