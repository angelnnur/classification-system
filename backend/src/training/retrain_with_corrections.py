"""
Простое переобучение модели с учетом исправлений пользователей
"""
import pandas as pd
import json
import os
from pathlib import Path
from config import Config
from training.processed import preprocess_data, save_preprocessing_objects
from models.autoencoder_model import AutoencoderDL
from keras.utils import to_categorical

FEEDBACK_FILE = "src/data/feedback_corrections.json"

def load_corrections(marketplace: str):
    """Загрузить исправления для маркетплейса"""
    file_path = Path(FEEDBACK_FILE)
    if not file_path.exists():
        return []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        all_corrections = json.load(f)
    
    # Фильтруем по маркетплейсу и неиспользованным
    corrections = [
        c for c in all_corrections 
        if c.get('marketplace') == marketplace and not c.get('used_for_training', False)
    ]
    
    return corrections

def add_corrections_to_dataset(corrections, marketplace: str):
    """
    Добавить исправления в датасет
    
    Args:
        corrections: список исправлений
        marketplace: название маркетплейса
    
    Returns:
        DataFrame с исправлениями
    """
    if not corrections:
        return pd.DataFrame()
    
    data = []
    for corr in corrections:
        data.append({
            'sku': f"correction_{corr['id']}",
            'product_name': corr['product_name'],
            'category_id': 0,  # Временный ID
            'category_name': corr['corrected_category'],  # Используем исправленную категорию
            'category_path': corr['corrected_category']  # Для совместимости
        })
    
    return pd.DataFrame(data)

def mark_corrections_as_used(marketplace: str):
    """Пометить исправления как использованные"""
    file_path = Path(FEEDBACK_FILE)
    if not file_path.exists():
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        corrections = json.load(f)
    
    # Пометить как использованные
    for corr in corrections:
        if corr.get('marketplace') == marketplace:
            corr['used_for_training'] = True
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(corrections, f, ensure_ascii=False, indent=2)

def retrain_with_corrections(marketplace: str):
    """
    Переобучить модель с учетом исправлений
    
    Args:
        marketplace: название маркетплейса (wildberries, ozon, yandex_market)
    """
    print(f"\n{'='*80}")
    print(f"🔄 ПЕРЕОБУЧЕНИЕ МОДЕЛИ ДЛЯ {marketplace.upper()}")
    print(f"{'='*80}")
    
    # 1. Загрузить исправления
    corrections = load_corrections(marketplace)
    print(f"\n📝 Найдено исправлений: {len(corrections)}")
    
    if corrections:
        for corr in corrections[:5]:  # Показать первые 5
            print(f"  - {corr['product_name'][:50]}...")
            print(f"    Было: {corr['predicted_category']} → Стало: {corr['corrected_category']}")
    
    # 2. Загрузить существующий датасет
    BASE_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == 'src' else BASE_DIR
    dataset_path = PROJECT_ROOT / f'src/data/raw/{marketplace}_products_list.csv'
    
    if not dataset_path.exists():
        raise FileNotFoundError(f"Датасет не найден: {dataset_path}")
    
    existing_df = pd.read_csv(dataset_path)
    print(f"\n📊 Существующий датасет: {len(existing_df)} товаров")
    
    # 3. Добавить исправления
    corrections_df = add_corrections_to_dataset(corrections, marketplace)
    
    if len(corrections_df) > 0:
        # Объединить датасеты
        # Если в существующем датасете есть category_name, используем его
        if 'category_name' not in existing_df.columns and 'category_path' in existing_df.columns:
            existing_df['category_name'] = existing_df['category_path'].str.split('/').str[-1].str.strip()
        
        # Объединить
        combined_df = pd.concat([existing_df, corrections_df], ignore_index=True)
        
        # Удалить дубликаты по product_name (оставляем последний - исправленный)
        combined_df = combined_df.drop_duplicates(subset=['product_name'], keep='last')
        
        print(f"✅ После добавления исправлений: {len(combined_df)} товаров")
        print(f"   Добавлено новых: {len(corrections_df)}")
    else:
        combined_df = existing_df
        print("⚠️ Нет новых исправлений для добавления")
    
    # 4. Сохранить временный датасет
    temp_dataset = PROJECT_ROOT / f'src/data/raw/{marketplace}_with_corrections.csv'
    combined_df.to_csv(temp_dataset, index=False)
    
    # 5. Предобработка и обучение
    from training.train_marketplace_models import MARKETPLACE_CONFIG
    config = MARKETPLACE_CONFIG[marketplace]
    
    print(f"\n📊 Предобработка данных...")
    print(f"   Используем category_name (дочерняя категория)")
    
    X, y, vectorizer, to_id, to_label = preprocess_data(
        csv_file=str(temp_dataset),
        min_samples_per_category=config['min_samples'],
        category_column='category_name',
        max_features=config['max_features']
    )
    
    print(f"✅ После предобработки:")
    print(f"   X.shape: {X.shape}")
    print(f"   Количество категорий: {len(to_id)}")
    
    # 6. Обучение
    y_cat = to_categorical(y)
    num_classes = y_cat.shape[1]
    
    model_dir = os.path.join(Config.MODELS_BIN, marketplace)
    os.makedirs(model_dir, exist_ok=True)
    
    save_preprocessing_objects(vectorizer, to_id, to_label, output_dir=model_dir)
    
    model = AutoencoderDL(
        input_dim=X.shape[1],
        bottleneck_dim=config['bottleneck_dim'],
        num_classes=num_classes
    )
    
    epochs = 50 if X.shape[0] < 30000 else 30
    
    print(f"\n🏋️ Обучение модели...")
    history = model.train_classifier(
        X, y_cat,
        epochs=epochs,
        batch_size=32,
        validation_split=0.2,
        use_early_stopping=True
    )
    
    # 7. Сохранить модель
    classifier_path = os.path.join(model_dir, 'classifier.h5')
    model.save(classifier_path)
    
    # 8. Пометить исправления как использованные
    if corrections:
        mark_corrections_as_used(marketplace)
        print(f"\n✅ Исправления помечены как использованные")
    
    print(f"\n✅ МОДЕЛЬ ПЕРЕОБУЧЕНА!")
    print(f"   Путь: {classifier_path}")
    print(f"   Категорий: {num_classes}")
    print(f"   Товаров: {X.shape[0]:,}")
    
    return model, history

if __name__ == '__main__':
    import sys
    
    marketplace = sys.argv[1] if len(sys.argv) > 1 else 'wildberries'
    retrain_with_corrections(marketplace)
