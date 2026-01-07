"""
Парсер для сбора данных о товарах с Wildberries
"""
import requests
import time
import pandas as pd
from typing import List, Dict
import os


class WildberriesParser:
    """
    Класс для парсинга товаров с Wildberries
    
    Методы работы:
    1. Через API Wildberries (если есть доступ)
    2. Через веб-скрапинг (парсинг страниц)
    """
    
    def __init__(self, api_key: str = None):
        """
        :param api_key: API ключ для Wildberries (опционально)
        """
        self.api_key = api_key
        self.base_url = "https://www.wildberries.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def get_products_by_category(self, category_url: str, max_products: int = 1000) -> List[Dict]:
        """
        Получить товары из категории
        
        :param category_url: URL категории на Wildberries
        :param max_products: Максимальное количество товаров для сбора
        :return: Список словарей с данными о товарах
        """
        products = []
        
        # Пример: парсинг через API или веб-скрапинг
        # Здесь будет логика получения товаров
        
        # ВАРИАНТ 1: Если есть API доступ
        if self.api_key:
            products = self._fetch_via_api(category_url, max_products)
        else:
            # ВАРИАНТ 2: Веб-скрапинг (нужно добавить selenium или requests+BeautifulSoup)
            products = self._fetch_via_scraping(category_url, max_products)
        
        return products
    
    def _fetch_via_api(self, category_url: str, max_products: int) -> List[Dict]:
        """
        Получение данных через официальный API Wildberries
        """
        products = []
        
        # Пример запроса к API (нужно уточнить документацию API)
        # API endpoint может быть разным, зависит от версии API
        try:
            # Пример структуры запроса
            response = requests.get(
                f"https://catalog.wb.ru/catalog/v1/catalog",
                params={
                    'category': category_url,
                    'limit': min(max_products, 100),  # API может ограничивать
                },
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Парсим ответ API и извлекаем товары
                for item in data.get('data', {}).get('products', []):
                    products.append({
                        'product_name': item.get('name', '').strip(),
                        'category': item.get('category', '').strip(),
                        'marketplace': 'wildberries'
                    })
        except Exception as e:
            print(f"⚠️ Ошибка при получении данных через API: {e}")
        
        return products
    
    def _fetch_via_scraping(self, category_url: str, max_products: int) -> List[Dict]:
        """
        Получение данных через веб-скрапинг
        ВНИМАНИЕ: Нужно соблюдать правила маркетплейса и robots.txt
        """
        products = []
        
        # Пример: использование requests + BeautifulSoup
        # Для динамических страниц может понадобиться Selenium
        try:
            from bs4 import BeautifulSoup
            
            response = requests.get(category_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Находим товары на странице (селекторы нужно уточнить)
                product_cards = soup.find_all('div', class_='product-card')  # Пример селектора
                
                for card in product_cards[:max_products]:
                    product_name = card.find('span', class_='product-name')
                    category = card.find('span', class_='category')
                    
                    if product_name and category:
                        products.append({
                            'product_name': product_name.get_text().strip(),
                            'category': category.get_text().strip(),
                            'marketplace': 'wildberries'
                        })
                
                # Добавить пагинацию для получения большего количества товаров
                # ...
                
        except Exception as e:
            print(f"⚠️ Ошибка при скрапинге: {e}")
        
        return products
    
    def collect_all_categories(self, categories: List[str], max_per_category: int = 500) -> pd.DataFrame:
        """
        Собрать товары из нескольких категорий
        
        :param categories: Список URL категорий или названий категорий
        :param max_per_category: Максимум товаров на категорию
        :return: DataFrame с товарами
        """
        all_products = []
        
        for category in categories:
            print(f"📦 Собираю товары из категории: {category}")
            products = self.get_products_by_category(category, max_per_category)
            all_products.extend(products)
            print(f"✅ Собрано {len(products)} товаров")
            
            # Задержка между запросами (чтобы не заблокировали)
            time.sleep(2)
        
        df = pd.DataFrame(all_products)
        return df
    
    def save_to_csv(self, df: pd.DataFrame, output_path: str):
        """
        Сохранить данные в CSV файл
        
        :param df: DataFrame с товарами
        :param output_path: Путь для сохранения
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"💾 Данные сохранены в {output_path}")


# Пример использования
if __name__ == "__main__":
    parser = WildberriesParser()
    
    # Пример категорий для сбора
    categories = [
        "https://www.wildberries.ru/catalog/elektronika/telefony",
        "https://www.wildberries.ru/catalog/elektronika/noutbuki",
        # ... другие категории
    ]
    
    df = parser.collect_all_categories(categories, max_per_category=500)
    parser.save_to_csv(df, "data/raw/wildberries_products.csv")
    
    print(f"✅ Всего собрано {len(df)} товаров")

