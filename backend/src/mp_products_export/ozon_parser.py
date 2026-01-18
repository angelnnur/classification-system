"""
Парсер для сбора товаров и дерево категорий с Ozon
"""
import requests
import json
import time
import pandas as pd
from typing import List, Dict, Optional
from ..config import Config


class OzonParser:
    def __init__(self, api_keys: Dict[str, Dict[str, str]] = None):
        """Инициализация парсера Ozon"""
        
        if not api_keys:
            api_keys = {
                "mgt": {
                    "api_key": Config.OZON_MGT_API_KEY,
                    "client_id": Config.OZON_MGT_CLIENT_ID
                },
                "kgt": {
                    "api_key": Config.OZON_KGT_API_KEY,
                    "client_id": Config.OZON_KGT_CLIENT_ID
                }
            }
        
        if not api_keys.get("mgt", {}).get("api_key") and not api_keys.get("kgt", {}).get("api_key"):
            raise ValueError("API ключи не указаны! Установите переменные окружения OZON_MGT_API_KEY, OZON_MGT_CLIENT_ID, OZON_KGT_API_KEY, OZON_KGT_CLIENT_ID в .env файле или передайте в конструктор")
        
        self.api_keys = api_keys
        self.url = 'https://api-seller.ozon.ru'
    
    def _get_products(self, max_products: Optional[int] = None) -> List[Dict]:
        """Получение списка товаров"""
        limit = 1000
        products = []

        for mp_type in self.api_keys:
            if not self.api_keys[mp_type].get("api_key"):
                continue
                
            next = True
            total = None
            last_id = ""
        
            headers = {
                'Client-Id': self.api_keys[mp_type]["client_id"],
                'Api-Key': self.api_keys[mp_type]["api_key"]
            }
            
            while next:
                body = {
                    "limit": limit,
                    "last_id": last_id,
                    "filter": {}
                }
                
                response = requests.post(
                    url=f"{self.url}/v4/product/info/attributes",
                    headers=headers,
                    data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                    timeout=300
                )
                
                if response.status_code != 200:
                    raise RuntimeError(
                        f"Ошибка подключения к API! Код: {response.status_code}. Текст: {response.text}"
                    )
                
                res = response.json()
                
                last_id = res.get("last_id", "")
                res_total = res.get("total", 0)

                for it in res.get("result", []):
                    if max_products and len(products) >= max_products:
                        next = False
                        break
                    
                    product_name = it.get("name", "").strip()
                    category_id = it.get("description_category_id")
                    
                    if product_name:
                        products.append({
                            "sku": it.get("sku"),
                            "product_name": product_name,
                            "category_id": category_id
                        })
                
                if total is None:
                    total = res_total or 0

                total -= limit

                if total < 0:
                    next = False
                
                if next:
                    time.sleep(0.3)
        
        return products
    
    def _get_category_map(self) -> Dict[int, Dict[str, str]]:
        """Получение категорий"""
        headers = None
        for mp_type in self.api_keys:
            if self.api_keys[mp_type].get("api_key"):
                headers = {
                    'Client-Id': self.api_keys[mp_type]["client_id"],
                    'Api-Key': self.api_keys[mp_type]["api_key"]
                }
                break
        
        if not headers:
            raise ValueError("Нет доступных API ключей для получения категорий")
        
        response = requests.post(
            url=f"{self.url}/v1/description-category/tree",
            headers=headers,
            timeout=300
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка при получении категорий! Код: {response.status_code}")
        
        res = response.json()
        cat_tree = self._get_category_path(res)
        
        return cat_tree
    
    def _get_category_path(self, categories: Dict) -> Dict[int, str]:
        """Построение дерева категорий рекурсией"""
        cat_tree = {}

        def recurse_cat(it, path):
            cat_id = it.get("description_category_id")

            if cat_id is None:
                return

            cat_name = it.get("category_name")
            current_path = f"{path} / {cat_name}" if path else cat_name

            cat_tree[cat_id] = {
                "name": cat_name,
                "path": current_path.lstrip(" / ")
            }

            for child in it.get("children", []):
                recurse_cat(child, current_path)

        for it in categories.get("result", []):
            recurse_cat(it, "")

        return cat_tree
    
    def collect_all_products(self, max_products: Optional[int] = None) -> pd.DataFrame:
        """Сбор товаров и их категорий"""
        products = self._get_products(max_products)
        
        if not products:
            return pd.DataFrame(columns=['product_name', 'category'])
        
        cat_map = self._get_category_map()
        
        result = []
        for prod in products:
            category_id = prod.get('category_id')
            cat_info = cat_map.get(category_id, {"name": "Неизвестная категория", "path": "Неизвестная категория"})
            category_name = cat_info.get("name", "Неизвестная категория")
            category_path = cat_info.get("path", "Неизвестная категория")
            
            result.append({
                'sku': prod['sku'],
                'product_name': prod['product_name'],
                'category_id': category_id,
                'category_name': category_name,
                'category_path': category_path
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
        parser = OzonParser()
        df = parser.collect_all_products(max_products=None)
        parser.save_to_csv(df, "src/data/raw/ozon_products_list.csv")
        print(f"✅ Готово! Собрано: {len(df)} товаров")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
