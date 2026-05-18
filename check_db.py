import sqlite3

def view_data():
    conn = sqlite3.connect("kaspi_monitor.db")
    cursor = conn.cursor()
    
    # Выбираем все записи из таблицы истории цен
    cursor.execute("SELECT * FROM price_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    print(f"{'ID':<4} | {'Название':<25} | {'Цена':<10} | {'Дата'}")
    print("-" * 70)
    
    for row in rows:
        print(f"{row[0]:<4} | {row[2]:<25} | {row[3]:<10} | {row[4]}")
    
    conn.close()

if __name__ == "__main__":
    view_data()