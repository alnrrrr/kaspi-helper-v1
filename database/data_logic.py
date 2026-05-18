import sqlite3
from datetime import datetime

class KaspiDB:  # <--- Проверь эту строку, буквы K, D, B должны быть заглавными
    def __init__(self, db_name="kaspi_monitor.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                seller_name TEXT,
                price INTEGER,
                timestamp DATETIME
            )
        ''')
        self.conn.commit()

    def save_price(self, product_id, seller_name, price):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO price_history (product_id, seller_name, price, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (product_id, seller_name, price, datetime.now()))
        self.conn.commit()

    def get_last_price(self, product_id):
        cursor = self.conn.cursor()
        # Ищем последнюю запись для этого товара
        cursor.execute('''
            SELECT price FROM price_history 
            WHERE product_id = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (product_id,))
        result = cursor.fetchone()
        return result[0] if result else None