import telebot
from telebot import types

import config


bot = telebot.TeleBot(config.API_TOKEN)

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
        "Приветсвую я бот помощник. Помогу тебе сделать заказ в нашем магазине.\n/catalog - каталог товаров где можно собрать корзину для заказа.\n/basket - корзина с выбранными товарами на которую можно оформить заказ",
        reply_markup=main_kb()

    )


@bot.message_handler(commands=["catalog"])
def catalog(message):
    bot.reply_to(message, "Добро пожаловать в каталог.")


@bot.message_handler(commands=['basket'])
def basket(message):
    bot.reply_to(message, "Ваша корзина.")


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    bot.reply_to(message, message.text)


bot.infinity_polling()
