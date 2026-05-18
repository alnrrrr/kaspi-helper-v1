import os 
from dotenv import load_workbook, load_dotenv


load_dotenv

# Твой ID продавца (можно найти в кабинете Kaspi -> Настройки)
MERCHANT_ID = os.getenv ("ТВОЙ_ID_ИЗ_КАБИНЕТА_КАСПИ")
TELEGRAM_TOKEN = os.getenv ("8018409880:AAGNHXaZt6reFmSh35TFE-8kLMVXTgmFNBE")
TELEGRAM_CHAT_ID = os.getenv ("8364786538")

# Название твоего магазина (точно так же, как оно пишется на Kaspi)
MY_SHOP_NAME = "ИП MOON" 

# Настройки для товаров
PRODUCTS_CONFIG = {
    "103421555": {
        "min_price": 295000,  # Ниже этой цены бот не опустится ни за что
        "step": 1,            # Шаг демпинга (срезаем по 1 тенге)
        "name": "Pixel i5-10400F RTX 3060",
        "brand": "Pixel",     # Бренд для XML
        "store_id": "PP1"     # Код твоего склада из кабинета Kaspi
    }
}
