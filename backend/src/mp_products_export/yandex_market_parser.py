"""
Парсер для сбора товаров и дерево категорий с Яндекс Маркет
"""
import requests
import json
import time
import pandas as pd
from typing import List, Dict, Optional
from ..config import Config


class YandexMarketParser:
    def __init__(self, api_token: str = None, business_id: int = None):
        """Инициализация парсера Яндекс Маркет"""
        
        if not api_token:
            api_token = Config.YM_API_TOKEN
        
        if not business_id:
            business_id = Config.YM_BUSINESS_ID
        
        if not api_token or not business_id:
            raise ValueError("API токен или Business ID не указаны! Установите переменные окружения YM_API_TOKEN и YM_BUSINESS_ID в .env файле или передайте в конструктор")
        
        self.api_token = api_token
        self.business_id = business_id
        self.url = 'https://api.partner.market.yandex.ru'
        self.headers = {
            'Api-Key': self.api_token
        }
    
    def _get_products(self, max_products: Optional[int] = None) -> List[Dict]:
        """Получение списка товаров"""
        archived_boolean = ['true', 'false']
        products = []

        for archived in archived_boolean:
            next_page_token = ''
            next_page = True
            cnt = 0

            while next_page:
                cnt += 1

                data = {
                    "archived": archived
                }

                url_params = f"&page_token={next_page_token}" if next_page_token else ""
                response = requests.post(
                    url=f"{self.url}/v2/businesses/{self.business_id}/offer-mappings?limit=200{url_params}",
                    headers=self.headers,
                    data=json.dumps(data),
                    timeout=300
                )

                if response.status_code != 200:
                    raise RuntimeError(
                        f"Ошибка подключения к API! Код: {response.status_code}. Текст: {response.text}"
                    )

                res = response.json()
                result = res.get("result", {})
                
                if not result or not result.get("paging", {}) or not result.get("paging", {}).get("nextPageToken") or cnt > 500:
                    next_page = False

                next_page_token = result.get("paging", {}).get("nextPageToken", "")
                
                for it in result.get("offerMappings", []):
                    if max_products and len(products) >= max_products:
                        next_page = False
                        break
                    
                    offer = it.get("offer", {})
                    mapping = it.get("mapping", {})
                    
                    product_name = offer.get("name", "").strip()
                    category_id = mapping.get("marketCategoryId")
                    category_name = mapping.get("marketCategoryName", "").strip()
                    
                    if product_name:
                        products.append({
                            "sku": offer.get("offerId"),
                            "product_name": product_name,
                            "category_id": category_id,
                            "category_name": category_name
                        })

                if next_page:
                    time.sleep(0.3)
        
        return products
    
    def _get_category_map(self) -> Dict[int, Dict[str, str]]:
        """Получение категорий"""
        response = requests.post(
            url=f"{self.url}/categories/tree",
            headers=self.headers,
            timeout=300
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Ошибка при получении категорий! Код: {response.status_code}")
        
        res = response.json()
        cat_tree = self._get_category_path(res)
        
        return cat_tree
    
    def _get_category_path(self, categories: Dict) -> Dict[int, Dict[str, str]]:
        """Построение дерева категорий рекурсией"""
        cat_tree = {}

        def recurse_cat(it, path):
            cat_id = it.get("id")

            if cat_id is None:
                return

            cat_name = it.get("name")
            current_path = f"{path} / {cat_name}" if path else cat_name

            cat_tree[cat_id] = {
                "name": cat_name,
                "path": current_path.lstrip(" / ")
            }

            for child in it.get("children", []):
                recurse_cat(child, current_path)

        recurse_cat(categories.get("result"), '')

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
            
            # Используем category_name из товара, если есть, иначе из дерева категорий
            category_name = prod.get('category_name') or cat_info.get("name", "Неизвестная категория")
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
        parser = YandexMarketParser()
        df = parser.collect_all_products(max_products=None)
        parser.save_to_csv(df, "src/data/raw/yandex_market_products_list.csv")
        print(f"✅ Готово! Собрано: {len(df)} товаров")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
