import xml.etree.ElementTree as ET
from datetime import datetime

def generate_kaspi_xml(merchant_id, offers_data, filename="kaspi_price.xml"):
    # Создаем корень XML по правилам Kaspi
    root = ET.Element("kaspi_catalog")
    root.set("date", datetime.now().strftime("%Y-%m-%d %H:%M"))
    root.set("xmlns", "http://kaspi.kz/kaspicatalog/2.0")

    ET.SubElement(root, "company").text = "Comp Master"
    ET.SubElement(root, "merchantid").text = merchant_id

    offers_el = ET.SubElement(root, "offers")

    for item in offers_data:
        offer = ET.SubElement(offers_el, "offer")
        offer.set("sku", str(item['sku'])[:20]) # Ограничение Kaspi до 20 символов
        
        # Обязательные теги по документации
        ET.SubElement(offer, "model").text = item.get('name', 'Компьютер')
        ET.SubElement(offer, "brand").text = item.get('brand', 'Custom')
        ET.SubElement(offer, "price").text = str(int(item['price'])) # Чистая цена без пробелов
        
        # Наличие и остатки на складе
        availabilities = ET.SubElement(offer, "availabilities")
        avail = ET.SubElement(availabilities, "availability", 
                               storeId=item.get('store_id', 'PP1'), 
                               available="yes")
        avail.set("stockCount", str(item.get('stock', 5))) # Передаем остаток 5 штук

    # Сохраняем в файл с красивыми отступами
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"📦 Официальный XML-фид Kaspi сгенерирован: {filename}")