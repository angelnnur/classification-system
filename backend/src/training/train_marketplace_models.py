"""
Обучение отдельных моделей для каждого маркетплейса
"""
import numpy as np
from keras.utils import to_categorical
import os
from pathlib import Path
from ..config import Config
from .processed import preprocess_data, save_preprocessing_objects
from ..models.autoencoder_model import AutoencoderDL

# Рекомендуемые параметры для каждого маркетплейса (из анализа)
MARKETPLACE_CONFIG = {
    'wildberries': {
        'min_samples': 10,
        'csv_file': 'src/data/raw/wildberries_products_list.csv',
        'category_column': 'category_path',
        'max_features': 2500,
        'bottleneck_dim': 128
    },
    'ozon': {
        'min_samples': 30,
        'csv_file': 'src/data/raw/ozon_products_list.csv',
        'category_column': 'category_path',
        'max_features': 2500,
        'bottleneck_dim': 128
    },
    'yandex_market': {
        'min_samples': 10,
        'csv_file': 'src/data/raw/yandex_market_products_list.csv',
        'category_column': 'category_path',
        'max_features': 3000,  # Больше features для большего количества категорий
        'bottleneck_dim': 256  # Больший bottleneck для большего количества категорий
    }
}


def train_marketplace_model(marketplace_name: str, output_base_dir: str = None):
    """
    Обучение модели для конкретного маркетплейса
    
    Args:
        marketplace_name: название маркетплейса ('wildberries', 'ozon', 'yandex_market')
        output_base_dir: базовая директория для сохранения моделей (по умолчанию Config.MODELS_BIN)
    """
    if marketplace_name not in MARKETPLACE_CONFIG:
        raise ValueError(f"Неизвестный маркетплейс: {marketplace_name}. Доступные: {list(MARKETPLACE_CONFIG.keys())}")
    
    config = MARKETPLACE_CONFIG[marketplace_name]
    
    print(f"\n{'='*80}")
    print(f"🚀 ОБУЧЕНИЕ МОДЕЛИ ДЛЯ {marketplace_name.upper()}")
    print(f"{'='*80}")
    
    # 1. Определяем пути
    BASE_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == 'src' else BASE_DIR
    CSV_PATH = PROJECT_ROOT / config['csv_file']
    
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Файл не найден: {CSV_PATH}")
    
    # 2. Определяем директорию для сохранения модели
    if output_base_dir is None:
        output_base_dir = Config.MODELS_BIN
    
    model_dir = os.path.join(output_base_dir, marketplace_name)
    os.makedirs(model_dir, exist_ok=True)
    
    print(f"\n📁 Директория модели: {model_dir}")
    print(f"📄 CSV файл: {CSV_PATH}")
    
    # 3. Предобработка данных
    print(f"\n📊 Предобработка данных...")
    print(f"   min_samples_per_category: {config['min_samples']}")
    print(f"   category_column: {config['category_column']}")
    print(f"   max_features: {config['max_features']}")
    
    X, y, vectorizer, to_id, to_label = preprocess_data(
        csv_file=str(CSV_PATH),
        min_samples_per_category=config['min_samples'],
        max_features=config['max_features']
    )
    
    print(f"✅ После предобработки:")
    print(f"   X.shape: {X.shape}")
    print(f"   Количество классов: {len(to_id)}")
    
    # 4. Преобразование меток в категориальный формат
    y_cat = to_categorical(y)
    num_classes = y_cat.shape[1]
    
    # 5. Сохранение preprocessing объектов
    print(f"\n💾 Сохранение preprocessing объектов...")
    save_preprocessing_objects(vectorizer, to_id, to_label, output_dir=model_dir)
    
    # 6. Создание и обучение модели
    print(f"\n🧠 Создание модели...")
    model = AutoencoderDL(
        input_dim=X.shape[1],
        bottleneck_dim=config['bottleneck_dim'],
        num_classes=num_classes
    )
    
    # Определяем количество эпох в зависимости от размера датасета
    epochs = 50 if X.shape[0] < 30000 else 30
    
    print(f"\n🏋️ Обучение модели...")
    history = model.train_classifier(
        X, y_cat,
        epochs=epochs,
        batch_size=32,
        validation_split=0.2,
        use_early_stopping=True
    )
    
    # 7. Сохранение модели
    print(f"\n💾 Сохранение модели...")
    classifier_path = os.path.join(model_dir, 'classifier.h5')
    model.save(classifier_path)
    
    print(f"\n✅ МОДЕЛЬ ДЛЯ {marketplace_name.upper()} ОБУЧЕНА И СОХРАНЕНА!")
    print(f"   Путь: {classifier_path}")
    print(f"   Количество категорий: {num_classes}")
    print(f"   Товаров для обучения: {X.shape[0]:,}")
    
    return model, history


def train_all_marketplaces():
    """Обучение моделей для всех маркетплейсов"""
    print(f"\n{'='*80}")
    print("🚀 ОБУЧЕНИЕ МОДЕЛЕЙ ДЛЯ ВСЕХ МАРКЕТПЛЕЙСОВ")
    print(f"{'='*80}")
    
    results = {}
    
    for marketplace in MARKETPLACE_CONFIG.keys():
        try:
            model, history = train_marketplace_model(marketplace)
            results[marketplace] = {
                'status': 'success',
                'final_accuracy': history.history['accuracy'][-1] if 'accuracy' in history.history else None
            }
        except Exception as e:
            print(f"\n❌ Ошибка при обучении {marketplace}: {e}")
            import traceback
            traceback.print_exc()
            results[marketplace] = {'status': 'error', 'error': str(e)}
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*80}")
    
    for marketplace, result in results.items():
        if result['status'] == 'success':
            acc = result['final_accuracy']
            print(f"✅ {marketplace}: Обучена успешно (Accuracy: {acc*100:.1f}%)" if acc else f"✅ {marketplace}: Обучена успешно")
        else:
            print(f"❌ {marketplace}: Ошибка - {result.get('error', 'Unknown error')}")
    
    return results


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        marketplace_name = sys.argv[1]
        train_marketplace_model(marketplace_name)
    else:
        # Обучение всех маркетплейсов
        train_all_marketplaces()
