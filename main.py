import telebot
from telebot import types
import json
from telebot.callback_data import CallbackData


import config
from catalog import load_catalog
from catalog_tools import get_all_up_categories, get_all_down_categories

bot = telebot.TeleBot(config.API_TOKEN)

# Глобальный список для данных каталога
CATALOG_DATA = []

# Словарь для хранения состояния пользователей
user_states = {}


def create_kb(buttons):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(0, len(buttons), 2):
        keyboard.add(*buttons[i:i + 2])
    return keyboard


def main_kb():
    return create_kb([
        types.KeyboardButton('/catalog'),
        types.KeyboardButton('/basket')
    ])





@bot.message_handler(commands=['help', 'start'])
def send_welcome(message):
    bot.reply_to(
        message,
        "Приветствую! Я бот-помощник. Помогу тебе сделать заказ в нашем магазине.\n"
        "/catalog - каталог товаров где можно собрать корзину для заказа.\n"
        "/basket - корзина с выбранными товарами на которую можно оформить заказ",
        reply_markup=main_kb()
    )


@bot.message_handler(commands=["catalog"])
def catalog(message):
    """
    Отображает каталог с inline-кнопками категорий
    """
    user_id = message.from_user.id
    global CATALOG_DATA
    # Проверяем, есть ли категории
    if not CATALOG_DATA:
        try:
            CATALOG_DATA = load_catalog()
        except FileNotFoundError as e:
            print(e)
            bot.reply_to(message, "Каталог временно недоступен")
            return

    # Инициализируем состояние пользователя
    user_states[user_id] = {
        'current_level': 'categories',
        'current_category': None,
        'current_subcategory': None,
        'current_product': None,
        'message_id': None,
        'chat_id': None
    }



    # Создаем inline-кнопки с категориями
    markup = types.InlineKeyboardMarkup(row_width=2)

    # Добавляем кнопки для каждой категории
    buttons = []
    for category in get_all_up_categories(CATALOG):
        callback_data = json.dumps({
            'action': 'select_category',
            'category': category
        })
        buttons.append(
            types.InlineKeyboardButton(
                category,
                callback_data=callback_data
            )
        )

    # Располагаем кнопки по 2 в ряд
    markup.add(*buttons, row_width=2)


    # Отправляем сообщение с кнопками
    msg = bot.send_message(
        message.chat.id,
        " *Добро пожаловать в каталог!*\n\nВыберите категорию:",
        parse_mode='Markdown',
        reply_markup=markup
    )

    # Сохраняем ID сообщения для редактирования
    user_states[user_id]['message_id'] = msg.message_id
    user_states[user_id]['chat_id'] = msg.chat.id


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """
    Обрабатывает нажатия на inline-кнопки
    """
    user_id = call.from_user.id

    # Инициализируем состояние, если его нет
    if user_id not in user_states:
        user_states[user_id] = {
            'current_level': 'categories',
            'current_category': None,
            'current_subcategory': None,
            'current_product': None,
            'message_id': call.message.message_id,
            'chat_id': call.message.chat_id
        }
    else:
        user_states[user_id]['message_id'] = call.message.message_id

    try:
        data = json.loads(call.data)
        action = data.get('action')

        if action == 'select_category':
            category = data.get('category')


            user_states[user_id].update({
                'current_level': 'subcategories',
                'current_category': category,
                'current_subcategory': None,
                'current_product': None
            })

            category_data = CATALOG_DATA[category]

            markup = types.InlineKeyboardMarkup()

            # Кнопка "Назад"
            markup.add(
                types.InlineKeyboardButton(
                    "️ Назад",
                    callback_data=json.dumps({'action': 'back_to_categories'})
                )
            )

            # Кнопки подкатегорий
            for subcategory in get_all_down_categories():
                callback_data = json.dumps({
                    'action': 'select_subcategory',
                    'category': category,
                    'subcategory': subcategory
                })
                markup.add(
                    types.InlineKeyboardButton(
                        subcategory,
                        callback_data=callback_data
                    )
                )

            bot.edit_message_text(
                f" *{category_data['name']}*\n\nВыберите подкатегорию:",
                user_states[user_id]['chat_id'],
                user_states[user_id]['message_id'],
                parse_mode='Markdown',
                reply_markup=markup
            )

        elif action == 'select_subcategory':
            category_key = data.get('category')
            subcategory_key = data.get('subcategory')
            if category_key in CATALOG_DATA and subcategory_key in CATALOG_DATA[category_key]['subcategories']:
                show_products(call.message.chat.id, user_id, category_key, subcategory_key)

        elif action == 'select_product':
            category_key = data.get('category')
            subcategory_key = data.get('subcategory')
            product_key = data.get('product')

            if (category_key in CATALOG_DATA and
                    subcategory_key in CATALOG_DATA[category_key]['subcategories'] and
                    product_key in CATALOG_DATA[category_key]['subcategories'][subcategory_key]['products']):
                show_product_card(call.message.chat.id, user_id, category_key, subcategory_key, product_key)

        elif action == 'back_to_categories':
            show_categories(call.message.chat.id, user_id)

        elif action == 'back_to_subcategories':
            category_key = data.get('category')
            show_subcategories(call.message.chat.id, user_id, category_key)

        elif action == 'back_to_products':
            category_key = data.get('category')
            subcategory_key = data.get('subcategory')
            show_products(call.message.chat.id, user_id, category_key, subcategory_key)

        elif action == 'add_to_cart':
            bot.answer_callback_query(call.id, "Товар добавлен в корзину!")
            return

        # Подтверждаем callback
        bot.answer_callback_query(call.id)

    except json.JSONDecodeError:
        bot.answer_callback_query(call.id, "Ошибка обработки")
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")


def show_categories(chat_id, user_id):
    """
    Показывает список категорий
    """
    if user_id not in user_states:
        return

    user_states[user_id].update({
        'current_level': 'categories',
        'current_category': None,
        'current_subcategory': None,
        'current_product': None
    })

    markup = types.InlineKeyboardMarkup(row_width=2)

    # Добавляем кнопки категорий
    buttons = []
    for category_key in CATALOG_DATA.keys():
        callback_data = json.dumps({
            'action': 'select_category',
            'category': category_key
        })
        buttons.append(
            types.InlineKeyboardButton(
                CATALOG_DATA[category_key]['name'],
                callback_data=callback_data
            )
        )

    # Располагаем кнопки
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            markup.add(buttons[i], buttons[i + 1])
        else:
            markup.add(buttons[i])

    bot.edit_message_text(
        "🛍️ *Каталог товаров*\n\nВыберите категорию:",
        chat_id,
        user_states[user_id]['message_id'],
        parse_mode='Markdown',
        reply_markup=markup
    )


def show_subcategories(chat_id, user_id, category_key):
    """
    Показывает подкатегории
    """



def show_products(chat_id, user_id, category_key, subcategory_key):
    """
    Показывает товары
    """
    if (user_id not in user_states or
            category_key not in CATALOG_DATA or
            subcategory_key not in CATALOG_DATA[category_key]['subcategories']):
        return

    user_states[user_id].update({
        'current_level': 'products',
        'current_category': category_key,
        'current_subcategory': subcategory_key,
        'current_product': None
    })

    category_data = CATALOG_DATA[category_key]
    subcategory_data = category_data['subcategories'][subcategory_key]


    markup = types.InlineKeyboardMarkup()

    # Кнопка "Назад"
    markup.add(
        types.InlineKeyboardButton(
            "⬅ Назад",
            callback_data=json.dumps({
                'action': 'back_to_subcategories',
                'category': category_key
            })
        )
    )

    # Кнопки товаров
    for product_key, product_data in subcategory_data['products'].items():
        callback_data = json.dumps({
            'action': 'select_product',
            'category': category_key,
            'subcategory': subcategory_key,
            'product': product_key
        })

        # Формируем текст кнопки
        name = product_data['name']
        price = product_data['price']

        if len(name) > 25:
            display_name = name[:22] + "..."
        else:
            display_name = name

        button_text = f"{display_name} - {price}₽"

        markup.add(
            types.InlineKeyboardButton(
                button_text,
                callback_data=callback_data
            )
        )

    bot.edit_message_text(
        f" *{subcategory_data['name']}*\n\nВыберите товар:",
        chat_id,
        user_states[user_id]['message_id'],
        parse_mode='Markdown',
        reply_markup=markup
    )


def show_product_card(chat_id, user_id, category_key, subcategory_key, product_key):
    """
    Показывает карточку товара
    """
    if (user_id not in user_states or
            category_key not in CATALOG_DATA or
            subcategory_key not in CATALOG_DATA[category_key]['subcategories'] or
            product_key not in CATALOG_DATA[category_key]['subcategories'][subcategory_key]['products']):
        return

    user_states[user_id].update({
        'current_level': 'product_card',
        'current_category': category_key,
        'current_subcategory': subcategory_key,
        'current_product': product_key
    })

    category_data = CATALOG_DATA[category_key]
    subcategory_data = category_data['subcategories'][subcategory_key]
    product_data = subcategory_data['products'][product_key]

    # Формируем текст карточки
    text = format_product_card(product_data, category_data, subcategory_data)

    markup = types.InlineKeyboardMarkup()

    # Кнопка "Назад"
    markup.add(
        types.InlineKeyboardButton(
            "⬅ Назад",
            callback_data=json.dumps({
                'action': 'back_to_products',
                'category': category_key,
                'subcategory': subcategory_key
            })
        )
    )

    # Кнопка "В корзину"
    markup.add(
        types.InlineKeyboardButton(
            "🛒 Добавить в корзину",
            callback_data=json.dumps({
                'action': 'add_to_cart',
                'category': category_key,
                'subcategory': subcategory_key,
                'product': product_key
            })
        )
    )

    # Если есть фото
    image_url = product_data.get('image_url', '')
    if image_url and image_url.startswith('http'):
        try:
            # Удаляем старое сообщение
            bot.delete_message(chat_id, user_states[user_id]['message_id'])

            # Отправляем фото
            msg = bot.send_photo(
                chat_id,
                image_url,
                caption=text,
                parse_mode='Markdown',
                reply_markup=markup
            )
            user_states[user_id]['message_id'] = msg.message_id
        except:
            # Если фото не отправилось, показываем текст
            bot.edit_message_text(
                text,
                chat_id,
                user_states[user_id]['message_id'],
                parse_mode='Markdown',
                reply_markup=markup
            )
    else:
        # Без фото
        bot.edit_message_text(
            text,
            chat_id,
            user_states[user_id]['message_id'],
            parse_mode='Markdown',
            reply_markup=markup
        )


def format_product_card(product_data, category_data, subcategory_data):
    """
    Форматирует текст карточки товара
    """
    return f"""🛍 *{product_data['name']}*

{product_data['description']}

 *Цена:* {product_data['price']}₽

 *Категория:* {category_data['name']}
 *Подкатегория:* {subcategory_data['name']}
"""


@bot.message_handler(commands=['basket'])
def basket(message):
    bot.reply_to(message, "Ваша корзина.")


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.reply_to(message, message.text)


CATALOG = load_catalog()

bot.infinity_polling()