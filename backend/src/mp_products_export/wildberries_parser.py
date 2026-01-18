"""
Парсер для сбора товаров и дерево категорий с Wildberries
"""
import requests
import json
import time
import pandas as pd
from typing import List, Dict, Optional
from ..config import Config


class WildberriesParser:
    def __init__(self, api_key: str = None):
        """Инициализация парсера Wildberries"""
        
        if not api_key:
            api_key = Config.WILDBERRIES_API_KEY
        
        if not api_key:
            raise ValueError("API ключ не указан! Установите переменную окружения WILDBERRIES_API_KEY в .env файле или передайте в конструктор")
        
        self.api_key = api_key
        
        self.url = "https://content-api.wildberries.ru"
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
    
    def _get_products(self, max_products: Optional[int] = None) -> List[Dict]:
        """Получение списка товаров"""
        limit = 100
        next_page = True
        cursor = {"limit": limit}
        products = []
                
        while next_page:
            body = {
                "settings": {
                    "cursor": cursor,
                    "filter": {"withPhoto": -1}
                }
            }
            
            response = requests.post(
                url=f"{self.url}/content/v2/get/cards/list",
                headers=self.headers,
                data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                timeout=300
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ошибка API! Код: {response.status_code}. Текст: {response.text}")
            
            res = response.json()
            if res.get('error'):
                time.sleep(1)
                continue
            
            cur = res.get("cursor", {})
            cards = res.get("cards", [])
            
            if len(cards) < limit:
                next_page = False
            
            cursor = {
                "updatedAt": cur.get("updatedAt"),
                "nmID": cur.get("nmID"),
                "limit": limit,
            }
            
            for card in cards:
                if max_products and len(products) >= max_products:
                    next_page = False
                    break
                
                product_name = card.get("title", "").strip()
                subject_id = card.get("subjectID")
                subject_name = card.get("subjectName")

                if product_name:
                    products.append({
                        "sku": card.get("nmID"),
                        "product_name": product_name,
                        "categoriy_id": subject_id,
                        "category_name": subject_name
                    })
            
            if next_page:
                time.sleep(0.3)
        
        return products
    
    def _get_category_map(self) -> Dict[int, str]:
        """Получение категорий"""
        limit = 1000
        offset = 0
        cat_map = {}
        next_page = True

        while next_page:
            response = requests.get(
                url=f"{self.url}/content/v2/object/all?limit={limit}&offset={offset}",
                headers=self.headers,
                timeout=300
            )
            
            if response.status_code != 200:
                raise RuntimeError(f"Ошибка при получении категорий! Код: {response.status_code}")
            
            data = response.json().get("data", [])

            if(len(data) < limit):
                next_page = False
            
            for item in data:
                cat_id = item.get("subjectID")
                parent_name = item.get("parentName", "").strip()
                cat_name = item.get("subjectName", "").strip()
                
                if cat_id and cat_name:
                    if parent_name:
                        cat_map[cat_id] = f"{parent_name}/{cat_name}"
                    else:
                        cat_map[cat_id] = cat_name
            
            offset += limit

            if next_page:
                time.sleep(0.2)
        
        return cat_map
    
    def collect_all_products(self, max_products: Optional[int] = None) -> pd.DataFrame:
        """Сбор товаров и их категорий"""
        products = self._get_products(max_products)
        
        if not products:
            return pd.DataFrame(columns=['product_name', 'category'])
        
        cat_map = self._get_category_map()
        
        result = []
        for prod in products:
            subject_id = prod.get('categoriy_id')
            category = cat_map.get(subject_id, 'Неизвестная категория')
            
            result.append({
                'sku': prod['sku'],
                'product_name': prod['product_name'],
                'category_id': prod['categoriy_id'],
                'category_name': prod['category_name'],
                'category_path': category
            })
        
        df = pd.DataFrame(result)
        
        return df
    
    def save_to_csv(self, df: pd.DataFrame, output_path: str):
        """Сохранение данных в CSV файл"""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')

if __name__ == "__main__":
    try:
        parser = WildberriesParser()
        df = parser.collect_all_products(max_products=None)
        parser.save_to_csv(df, "src/data/raw/wildberries_products_list.csv")
        print(f"✅ Готово! Собрано: {len(df)} товаров")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
