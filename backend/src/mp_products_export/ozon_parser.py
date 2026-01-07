"""
Парсер для сбора данных о товарах с Ozon
"""
import requests
import time
import pandas as pd
from typing import List, Dict
import os


class OzonParser:
    """
    Класс для парсинга товаров с Ozon
    
    Ozon предоставляет API для партнеров, но для публичного доступа
    может потребоваться веб-скрапинг
    """
    
    def __init__(self, api_key: str = None, client_id: str = None):
        """
        :param api_key: API ключ для Ozon (если есть доступ к Partner API)
        :param client_id: Client ID для Ozon API
        """
        self.api_key = api_key
        self.client_id = client_id
        self.base_url = "https://www.ozon.ru"
        self.api_url = "https://api-seller.ozon.ru" if api_key else None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Client-Id': self.client_id if self.client_id else '',
            'Api-Key': self.api_key if self.api_key else ''
        }
    
    def get_products_by_category(self, category_id: str, max_products: int = 1000) -> List[Dict]:
        """
        Получить товары из категории
        
        :param category_id: ID категории на Ozon
        :param max_products: Максимальное количество товаров
        :return: Список словарей с данными о товарах
        """
        products = []
        
        if self.api_key and self.client_id:
            products = self._fetch_via_api(category_id, max_products)
        else:
            products = self._fetch_via_scraping(category_id, max_products)
        
        return products
    
    def _fetch_via_api(self, category_id: str, max_products: int) -> List[Dict]:
        """
        Получение данных через Ozon Partner API
        """
        products = []
        
        try:
            # Пример запроса к Ozon Partner API
            # Документация: https://docs.ozon.ru/api/seller/
            response = requests.post(
                f"{self.api_url}/v2/product/list",
                json={
                    "filter": {
                        "category_id": category_id,
                        "visibility": "ALL"
                    },
                    "limit": min(max_products, 1000),
                    "offset": 0
                },
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                for item in data.get('result', {}).get('items', []):
                    products.append({
                        'product_name': item.get('name', '').strip(),
                        'category': item.get('category_name', '').strip(),
                        'marketplace': 'ozon'
                    })
        except Exception as e:
            print(f"⚠️ Ошибка при получении данных через API: {e}")
        
        return products
    
    def _fetch_via_scraping(self, category_url: str, max_products: int) -> List[Dict]:
        """
        Получение данных через веб-скрапинг Ozon
        """
        products = []
        
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(category_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Селекторы для Ozon (нужно уточнить актуальные)
                product_cards = soup.find_all('div', {'data-widget': 'searchResultsV2'})
                
                for card in product_cards[:max_products]:
                    # Извлекаем название и категорию
                    product_name_elem = card.find('span', class_='tsBodyL')
                    category_elem = card.find('a', class_='category-link')
                    
                    if product_name_elem:
                        products.append({
                            'product_name': product_name_elem.get_text().strip(),
                            'category': category_elem.get_text().strip() if category_elem else 'Unknown',
                            'marketplace': 'ozon'
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
            print(f"📦 Собираю товары из категории Ozon: {category}")
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
    parser = OzonParser()
    
    categories = [
        "https://www.ozon.ru/category/smartfony-15502/",
        "https://www.ozon.ru/category/noutbuki-11801/",
        # ... другие категории
    ]
    
    df = parser.collect_all_categories(categories, max_per_category=500)
    parser.save_to_csv(df, "data/raw/ozon_products.csv")
    
    print(f"✅ Всего собрано {len(df)} товаров")

