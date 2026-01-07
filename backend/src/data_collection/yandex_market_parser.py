"""
Парсер для сбора данных о товарах с Яндекс Маркет
"""
import requests
import time
import pandas as pd
from typing import List, Dict
import os


class YandexMarketParser:
    """
    Класс для парсинга товаров с Яндекс Маркет
    
    Яндекс Маркет предоставляет API для разработчиков,
    но для публичного доступа может потребоваться веб-скрапинг
    """
    
    def __init__(self, api_key: str = None):
        """
        :param api_key: API ключ для Яндекс Маркет (если есть)
        """
        self.api_key = api_key
        self.base_url = "https://market.yandex.ru"
        self.api_url = "https://api.content.market.yandex.ru" if api_key else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
        }
    
    def get_products_by_category(self, category_url: str, max_products: int = 1000) -> List[Dict]:
        """
        Получить товары из категории
        
        :param category_url: URL категории на Яндекс Маркет
        :param max_products: Максимальное количество товаров
        :return: Список словарей с данными о товарах
        """
        products = []
        
        if self.api_key:
            products = self._fetch_via_api(category_url, max_products)
        else:
            products = self._fetch_via_scraping(category_url, max_products)
        
        return products
    
    def _fetch_via_api(self, category_url: str, max_products: int) -> List[Dict]:
        """
        Получение данных через Яндекс Маркет API
        """
        products = []
        
        try:
            # Пример запроса к Яндекс Маркет API
            # Документация: https://yandex.ru/dev/market/content-api/
            response = requests.get(
                f"{self.api_url}/v1/category/{category_url}/offers",
                params={
                    'count': min(max_products, 30),  # API ограничивает
                    'page': 1
                },
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('offers', []):
                    products.append({
                        'product_name': item.get('name', '').strip(),
                        'category': item.get('category', '').strip(),
                        'marketplace': 'yandex_market'
                    })
        except Exception as e:
            print(f"⚠️ Ошибка при получении данных через API: {e}")
        
        return products
    
    def _fetch_via_scraping(self, category_url: str, max_products: int) -> List[Dict]:
        """
        Получение данных через веб-скрапинг Яндекс Маркет
        """
        products = []
        
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(category_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Селекторы для Яндекс Маркет (нужно уточнить актуальные)
                product_cards = soup.find_all('div', class_='product-card')
                
                for card in product_cards[:max_products]:
                    product_name_elem = card.find('h3', class_='product-title')
                    category_elem = card.find('span', class_='category')
                    
                    if product_name_elem:
                        products.append({
                            'product_name': product_name_elem.get_text().strip(),
                            'category': category_elem.get_text().strip() if category_elem else 'Unknown',
                            'marketplace': 'yandex_market'
                        })
        except Exception as e:
            print(f"⚠️ Ошибка при скрапинге: {e}")
        
        return products
    
    def collect_all_categories(self, categories: List[str], max_per_category: int = 500) -> pd.DataFrame:
        """
        Собрать товары из нескольких категорий
        """
        all_products = []
        
        for category in categories:
            print(f"📦 Собираю товары из категории Яндекс Маркет: {category}")
            products = self.get_products_by_category(category, max_per_category)
            all_products.extend(products)
            print(f"✅ Собрано {len(products)} товаров")
            time.sleep(2)
        
        df = pd.DataFrame(all_products)
        return df
    
    def save_to_csv(self, df: pd.DataFrame, output_path: str):
        """Сохранить данные в CSV"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Данные сохранены в {output_path}")


if __name__ == "__main__":
    parser = YandexMarketParser()
    
    categories = [
        "https://market.yandex.ru/catalog--smartfony/",
        "https://market.yandex.ru/catalog--noutbuki/",
        # ... другие категории
    ]
    
    df = parser.collect_all_categories(categories, max_per_category=500)
    parser.save_to_csv(df, "data/raw/yandex_market_products.csv")
    
    print(f"✅ Всего собрано {len(df)} товаров")

