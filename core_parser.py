import asyncio
import random
from playwright.async_api import async_playwright, Page
from database.data_logic import KaspiDB

# ── Stealth-скрипт (без изменений) ──────────────────────────────────────────
STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'plugins',   { get: () => [1,2,3,4,5] });
Object.defineProperty(navigator, 'languages', { get: () => ['ru-KZ','ru','en'] });
window.chrome = { runtime: {}, loadTimes: function(){}, csi: function(){}, app: {} };
"""

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
]

KASPI_CITY_COOKIES = {
    "almaty":  "750000000",
    "astana":  "710000000",
    "shymkent":"732000000",
}

# ── Главный JS: рекурсивный обход Shadow DOM ────────────────────────────────
#
# Логика:
#   1. queryDeep(selector, root) — ищет элементы по всему дереву,
#      включая все shadowRoot на любой глубине.
#   2. extractText(el) — достаёт текст, даже если он в <slot> или вложен.
#   3. Три стратегии поиска строк таблицы (на случай обновления классов Kaspi).
#
SHADOW_DOM_SCRAPER = """
() => {
    // ── 1. Рекурсивный поиск по всем Shadow DOM ──────────────────────────
    function queryDeep(selector, root = document) {
        const results = [];

        function walk(node) {
            // Ищем в текущем контексте
            try {
                node.querySelectorAll(selector).forEach(el => results.push(el));
            } catch(e) {}

            // Рекурсивно заходим в shadowRoot каждого потомка
            node.querySelectorAll('*').forEach(child => {
                if (child.shadowRoot) {
                    walk(child.shadowRoot);
                }
            });
        }

        walk(root);
        return results;
    }

    // ── 2. Извлечение чистого текста (работает со <slot>) ─────────────────
    function extractText(el) {
        return (el?.innerText || el?.textContent || '').trim();
    }

    function parsePrice(str) {
        const digits = str.replace(/[^0-9]/g, '');
        const val = parseInt(digits, 10);
        return isNaN(val) ? 0 : val;
    }

    // ── 3. Три стратегии поиска (Kaspi меняет классы — мы устойчивы) ──────
    const STRATEGIES = [
        {
            // Берем все строки таблицы напрямую
            rows:   '.sellers-table tr, .sellers-table__self tr, .sellers-table__row',
            // Ищем имя магазина в ссылке или в специальном классе
            name:   '.sellers-table__seller-name, .seller-item__delivery-option-link, a[href*="/shop/seller/"]',
            // Ищем цену там, где есть цифры
            price:  '.sellers-table__price-cell, .sellers-table__cell:nth-child(4)', 
        }
    ];

    // ── 4. Перебираем стратегии, берём первую рабочую ─────────────────────
    for (const strategy of STRATEGIES) {
        const rows = queryDeep(strategy.rows);

        if (rows.length === 0) continue;  // стратегия не сработала

        const sellers = [];
        rows.forEach(row => {
            // 1. Ищем ячейку, где лежит название (обычно первая ячейка строки)
            const cells = row.querySelectorAll('.sellers-table__cell');
            if (cells.length === 0) return;

            // 2. Название магазина — это текст ПЕРВОЙ ссылки в первой ячейке
            const nameLink = cells[0].querySelector('a');
            
            // 3. Цена обычно лежит в четвертой ячейке или имеет свой класс
            const priceEl = row.querySelector('.sellers-table__price-cell') || cells[3];

            if (nameLink && priceEl) {
                // Извлекаем только текст из ссылки (там чистое название магазина)
                const name = nameLink.innerText.trim();
                
                // Очищаем цену от символов "₸" и пробелов
                const price = parseInt(priceEl.innerText.replace(/[^0-9]/g, ''));

                if (name && price > 0) {
                    sellers.push({ name, price });
                }
            }
        });

        if (sellers.length > 0) {
            return {
                ok:       true,
                strategy: STRATEGIES.indexOf(strategy),
                sellers:  sellers,
            };
        }
    }

    // ── 5. Все стратегии провалились — возвращаем диагностику ─────────────
    // Собираем все уникальные классы на странице для отладки
    const allClasses = new Set();
    queryDeep('[class]').slice(0, 200).forEach(el => {
        el.className.toString().split(' ')
            .filter(c => c.includes('seller') || c.includes('offer') || c.includes('merchant'))
            .forEach(c => allClasses.add(c));
    });

    return {
        ok:          false,
        strategy:    -1,
        sellers:     [],
        debug_classes: [...allClasses],
    };
}
"""


# ── Основная функция парсинга ────────────────────────────────────────────────

async def get_kaspi_data(url: str, city: str = "almaty") -> list[dict] | None:
    """
    Возвращает список продавцов: [{"name": str, "price": int}, ...]
    или None при критической ошибке.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            locale="ru-KZ",
            timezone_id="Asia/Almaty",
            viewport={"width": 1366, "height": 768},
            extra_http_headers={"Accept-Language": "ru-KZ,ru;q=0.9"},
        )
        await context.add_init_script(STEALTH_SCRIPT)

        city_id = KASPI_CITY_COOKIES.get(city, KASPI_CITY_COOKIES["almaty"])
        await context.add_cookies([
            {"name": "ks.city",
             "value": city_id, "domain": ".kaspi.kz", "path": "/"},
            {"name": "kaspi.storefront.cookie.city",
             "value": city_id, "domain": ".kaspi.kz", "path": "/"},
        ])

        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=60_000)
            await asyncio.sleep(random.uniform(2.0, 3.5))  # имитируем чтение

            result = await page.evaluate(SHADOW_DOM_SCRAPER)

            if result["ok"]:
                sellers = result["sellers"]
                print(f"✅ Найдено {len(sellers)} продавцов "
                      f"(стратегия {result['strategy']})")
                for i, s in enumerate(sellers[:5], 1):
                    print(f"  {i}. {s['name']} — {s['price']:,} ₸")
                return sellers

            else:
                # Все стратегии провалились — помогаем себе в отладке
                print("❌ Продавцы не найдены. Диагностика:")
                print(f"   Классы с 'seller/offer/merchant': "
                      f"{result.get('debug_classes', [])}")
                await page.screenshot(path="shadow_dom_debug.png", full_page=True)

                # Последний шанс: дамп HTML для ручного анализа
                html = await page.content()
                with open("page_dump.html", "w", encoding="utf-8") as f:
                    f.write(html)
                print("   Сохранены: shadow_dom_debug.png, page_dump.html")
                return None

        except Exception as e:
            print(f"💥 Критическая ошибка: {e}")
            await page.screenshot(path="crash_debug.png")
            return None

        finally:
            await browser.close()

if __name__ == "__main__":
    # 1. Запускаем парсер
    url = "https://kaspi.kz/shop/p/pixel-i5-10400f-rtx-3060-16gb-512-gb-ssd-win-10-103421555/?c=710000000"
    sellers = asyncio.run(get_kaspi_data(url, city="almaty"))

    # 2. Если данные получены, включаем логику демпинга
    if sellers:
        from config import MY_SHOP_NAME, MERCHANT_ID, PRODUCTS_CONFIG
        from xml_generator import generate_kaspi_xml
        from notifier import send_telegram_msg
        
        db = KaspiDB()
        product_id = "103421555"
        conf = PRODUCTS_CONFIG.get(product_id)
        
        top_seller = sellers[0]
        leader_name = top_seller['name']
        leader_price = top_seller['price']
        
        # Сохраняем историю в базу данных
        for s in sellers:
            db.save_price(product_id, s['name'], s['price'])
        print("✅ Данные успешно сохранены в историю БД!")

        # АНАЛИЗ И РАСЧЕТ ЦЕНЫ
        if leader_name == MY_SHOP_NAME:
            # Если мы уже на 1 месте, цену не снижаем, оставляем как есть
            final_price = leader_price
            print(f"😎 {MY_SHOP_NAME} уже на первом месте. Цену держим: {final_price:,} ₸")
        else:
            # Если нас перебили, считаем цену: цена лидера минус наш шаг
            target_price = leader_price - conf['step']
            
            # Проверяем, не упали ли мы ниже минималки
            if target_price >= conf['min_price']:
                final_price = target_price
                msg = (f"⚠️ <b>Вас перебили!</b>\n"
                       f"🥇 Лидер: {leader_name} ({leader_price:,} ₸)\n"
                       f"🎯 Снижаем цену до: <b>{final_price:,} ₸</b> чтобы вернуть Топ-1.")
                send_telegram_msg(msg)
            else:
                # Если конкурент опустил цену ниже нашего минимума
                final_price = conf['min_price']
                msg = (f"🛑 <b>Внимание! Демпинг ниже лимита!</b>\n"
                       f"🥇 Лидер {leader_name} поставил {leader_price:,} ₸.\n"
                       f"Мы держим наш минимум: <b>{final_price:,} ₸</b>, ниже нельзя!")
                send_telegram_msg(msg)

        # 3. ФОРМИРУЕМ ПАКЕТ ДАННЫХ И ИЗМЕНЯЕМ XML
        xml_data = [{
            'sku': product_id,
            'price': final_price,
            'name': conf['name'],
            'brand': conf['brand'],
            'store_id': conf['store_id'],
            'stock': 5
        }]
        
        # Создаем/обновляем XML-файл
        generate_kaspi_xml(MERCHANT_ID, xml_data)