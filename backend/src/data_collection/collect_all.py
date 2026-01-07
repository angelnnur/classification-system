"""
Главный скрипт для сбора данных со всех маркетплейсов
"""
import os
import sys
from pathlib import Path

# Добавляем путь к src для импортов
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from data_collection.wildberries_parser import WildberriesParser
from data_collection.ozon_parser import OzonParser
from data_collection.yandex_market_parser import YandexMarketParser


def collect_wildberries(output_dir: str = "data/raw"):
    """Собрать данные с Wildberries"""
    print("=" * 60)
    print("🛒 СБОР ДАННЫХ С WILDBERRIES")
    print("=" * 60)
    
    parser = WildberriesParser()
    
    # Список категорий для сбора (нужно указать актуальные URL)
    categories = [
        "https://www.wildberries.ru/catalog/elektronika/telefony",
        "https://www.wildberries.ru/catalog/elektronika/noutbuki",
        "https://www.wildberries.ru/catalog/elektronika/planshety",
        # Добавьте другие категории по необходимости
    ]
    
    df = parser.collect_all_categories(categories, max_per_category=500)
    output_path = os.path.join(output_dir, "wildberries_products.csv")
    parser.save_to_csv(df, output_path)
    
    print(f"✅ Wildberries: собрано {len(df)} товаров")
    return df


def collect_ozon(output_dir: str = "data/raw"):
    """Собрать данные с Ozon"""
    print("=" * 60)
    print("🛒 СБОР ДАННЫХ С OZON")
    print("=" * 60)
    
    # Если есть API ключи, передайте их:
    # parser = OzonParser(api_key="your_key", client_id="your_id")
    parser = OzonParser()
    
    categories = [
        "https://www.ozon.ru/category/smartfony-15502/",
        "https://www.ozon.ru/category/noutbuki-11801/",
        "https://www.ozon.ru/category/planshety-11802/",
        # Добавьте другие категории
    ]
    
    df = parser.collect_all_categories(categories, max_per_category=500)
    output_path = os.path.join(output_dir, "ozon_products.csv")
    parser.save_to_csv(df, output_path)
    
    print(f"✅ Ozon: собрано {len(df)} товаров")
    return df


def collect_yandex_market(output_dir: str = "data/raw"):
    """Собрать данные с Яндекс Маркет"""
    print("=" * 60)
    print("🛒 СБОР ДАННЫХ С ЯНДЕКС МАРКЕТ")
    print("=" * 60)
    
    parser = YandexMarketParser()
    
    categories = [
        "https://market.yandex.ru/catalog--smartfony/",
        "https://market.yandex.ru/catalog--noutbuki/",
        "https://market.yandex.ru/catalog--planshety/",
        # Добавьте другие категории
    ]
    
    df = parser.collect_all_categories(categories, max_per_category=500)
    output_path = os.path.join(output_dir, "yandex_market_products.csv")
    parser.save_to_csv(df, output_path)
    
    print(f"✅ Яндекс Маркет: собрано {len(df)} товаров")
    return df


def collect_all(output_dir: str = "data/raw"):
    """
    Собрать данные со всех маркетплейсов
    
    :param output_dir: Директория для сохранения CSV файлов
    """
    print("\n" + "=" * 60)
    print("🚀 НАЧАЛО СБОРА ДАННЫХ СО ВСЕХ МАРКЕТПЛЕЙСОВ")
    print("=" * 60 + "\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    results = {}
    
    try:
        # Собираем данные с каждого маркетплейса
        results['wildberries'] = collect_wildberries(output_dir)
        print()
        
        results['ozon'] = collect_ozon(output_dir)
        print()
        
        results['yandex_market'] = collect_yandex_market(output_dir)
        print()
        
        # Итоговая статистика
        print("=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 60)
        total = 0
        for marketplace, df in results.items():
            count = len(df)
            total += count
            print(f"  {marketplace}: {count} товаров")
        print(f"\n  ВСЕГО: {total} товаров")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⚠️ Сбор данных прерван пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при сборе данных: {e}")
        import traceback
        traceback.print_exc()
    
    return results


if __name__ == "__main__":
    # Можно запустить сбор всех данных
    collect_all()
    
    # Или собрать данные только с одного маркетплейса:
    # collect_wildberries()
    # collect_ozon()
    # collect_yandex_market()

