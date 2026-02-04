"""
Улучшенное переобучение модели с учетом исправлений пользователей
- Использует веса для исправлений (высокий вес)
- Поддерживает fine-tuning вместо полного переобучения
- Дублирует исправления для увеличения их влияния
"""
import pandas as pd
import json
import os
import numpy as np
from pathlib import Path
from config import Config
from processed import preprocess_data, save_preprocessing_objects
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

def add_corrections_to_dataset(corrections, marketplace: str, duplicate_factor=3):
    """
    Добавить исправления в датасет с возможностью дублирования
    
    Args:
        corrections: список исправлений
        marketplace: название маркетплейса
        duplicate_factor: во сколько раз дублировать исправления (для увеличения влияния)
    
    Returns:
        DataFrame с исправлениями и флагом is_correction
    """
    if not corrections:
        return pd.DataFrame()
    
    data = []
    for corr in corrections:
        # Дублируем исправления для увеличения их влияния
        for dup_idx in range(duplicate_factor):
            data.append({
                'sku': f"correction_{corr['id']}_{dup_idx}",
                'product_name': corr['product_name'],
                'category_id': 0,  # Временный ID
                'category_name': corr['corrected_category'],  # Используем исправленную категорию
                'category_path': corr['corrected_category'],  # Для совместимости
                'is_correction': True,  # Флаг для идентификации исправлений
                'correction_id': corr['id'],
                'confidence': corr.get('confidence', 0.5)  # Сохраняем уверенность модели
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

def create_sample_weights_for_training(df_before_preprocessing, df_after_preprocessing, 
                                       correction_weight=5.0, low_confidence_penalty=0.5):
    """
    Создать веса для примеров после предобработки.
    Сопоставляет примеры до и после предобработки по product_name.
    
    Args:
        df_before_preprocessing: датасет до предобработки (с колонкой is_correction)
        df_after_preprocessing: датасет после предобработки (может быть меньше)
        correction_weight: вес для исправлений (рекомендуется 3-10)
        low_confidence_penalty: множитель для примеров с низкой уверенностью
    
    Returns:
        numpy array с весами для примеров после предобработки
    """
    # Создаем словарь: product_name -> вес
    weight_map = {}
    
    for idx, row in df_before_preprocessing.iterrows():
        product_name = str(row['product_name']).lower().strip()
        weight = 1.0
        
        # Высокий вес для исправлений
        if row.get('is_correction', False):
            weight = correction_weight
        
        # Уменьшенный вес для примеров с низкой уверенностью
        if 'confidence' in row and row['confidence'] < 0.5:
            weight *= low_confidence_penalty
        
        weight_map[product_name] = weight
    
    # Создаем веса для примеров после предобработки
    weights = []
    correction_count = 0
    
    for idx, row in df_after_preprocessing.iterrows():
        product_name = str(row['product_name']).lower().strip()
        weight = weight_map.get(product_name, 1.0)
        weights.append(weight)
        
        if weight >= correction_weight:
            correction_count += 1
    
    weights = np.array(weights)
    
    print(f"   Исправлений с высоким весом: {correction_count}")
    print(f"   Всего примеров: {len(weights)}")
    
    return weights


def retrain_with_corrections(marketplace: str, use_fine_tuning=True, correction_weight=5.0, 
                            duplicate_corrections=3):

    # 1. Загрузить исправления
    corrections = load_corrections(marketplace)
    print(f"\n📝 Найдено исправлений: {len(corrections)}")
    
    if not corrections:
        print("⚠️ Нет новых исправлений для переобучения")
        return None, None
    
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
    
    # Добавить флаг is_correction для существующих данных
    if 'is_correction' not in existing_df.columns:
        existing_df['is_correction'] = False
        existing_df['confidence'] = 1.0  # Высокая уверенность для существующих данных
    
    # 3. Добавить исправления (с дублированием)
    corrections_df = add_corrections_to_dataset(corrections, marketplace, duplicate_factor=duplicate_corrections)
    
    # Объединить датасеты
    if 'category_name' not in existing_df.columns and 'category_path' in existing_df.columns:
        existing_df['category_name'] = existing_df['category_path'].str.split('/').str[-1].str.strip()
    
    # Объединить
    combined_df = pd.concat([existing_df, corrections_df], ignore_index=True)
    
    # Удалить дубликаты по product_name (оставляем последний - исправленный)
    # Но сохраняем информацию о том, что это исправление
    combined_df = combined_df.sort_values('is_correction', ascending=False)  # Исправления в конце
    combined_df = combined_df.drop_duplicates(subset=['product_name'], keep='last')
    
    print(f"✅ После добавления исправлений: {len(combined_df)} товаров")
    print(f"   Исправлений (с дублированием): {len(corrections_df)}")
    print(f"   Уникальных исправлений: {len(corrections)}")
    
    # 4. Сохранить временный датасет
    temp_dataset = PROJECT_ROOT / f'src/data/raw/{marketplace}_with_corrections.csv'
    combined_df.to_csv(temp_dataset, index=False)
    
    # 5. Предобработка
    from train import MARKETPLACE_CONFIG
    config = MARKETPLACE_CONFIG[marketplace]
    
    print(f"\n📊 Предобработка данных...")
    
    # Сохраняем датасет до предобработки для создания весов
    df_before_preprocessing = combined_df.copy()
    
    X, y, vectorizer, to_id, to_label = preprocess_data(
        csv_file=str(temp_dataset),
        min_samples_per_category=config['min_samples'],
        max_features=config['max_features']
    )
    
    print(f"✅ После предобработки:")
    print(f"   X.shape: {X.shape}")
    print(f"   Количество категорий: {len(to_id)}")
    
    # 6. Загрузить датасет после предобработки для сопоставления
    # (preprocess_data может удалить некоторые примеры)
    df_after_preprocessing = pd.read_csv(temp_dataset)
    df_after_preprocessing = df_after_preprocessing[
        df_after_preprocessing['category_path'].isin(to_id.keys())
    ]
    
    # 6. Создать веса для примеров
    print(f"\n⚖️  Создание весов для примеров...")
    sample_weights = create_sample_weights_for_training(
        df_before_preprocessing,
        df_after_preprocessing,
        correction_weight=correction_weight
    )
    
    # Проверяем, что размеры совпадают
    if len(sample_weights) != len(X):
        print(f"⚠️  Размеры не совпадают: weights={len(sample_weights)}, X={len(X)}")
        # Обрезаем или дополняем до нужного размера
        if len(sample_weights) > len(X):
            sample_weights = sample_weights[:len(X)]
        else:
            sample_weights = np.pad(sample_weights, (0, len(X) - len(sample_weights)), constant_values=1.0)
    
    print(f"   Веса: min={sample_weights.min():.2f}, max={sample_weights.max():.2f}, mean={sample_weights.mean():.2f}")
    
    # 7. Обучение
    y_cat = to_categorical(y)
    num_classes = y_cat.shape[1]
    
    model_dir = os.path.join(Config.MODELS_BIN, marketplace)
    os.makedirs(model_dir, exist_ok=True)
    
    save_preprocessing_objects(vectorizer, to_id, to_label, output_dir=model_dir)
    
    classifier_path = os.path.join(model_dir, 'classifier.h5')
    
    if use_fine_tuning and os.path.exists(classifier_path):
        # Fine-tuning: загружаем существующую модель и дообучаем
        print(f"\n🔧 FINE-TUNING существующей модели...")
        
        # Загружаем существующую модель
        model = AutoencoderDL(
            input_dim=X.shape[1],
            bottleneck_dim=config['bottleneck_dim'],
            num_classes=num_classes
        )
        model.load_classifier(classifier_path)
        
        # Fine-tuning с меньшим learning rate
        epochs = 15  # Меньше эпох для fine-tuning
        history = model.fine_tune(
            X, y_cat,
            epochs=epochs,
            batch_size=32,
            validation_split=0.2,
            sample_weight=sample_weights,
            learning_rate=0.0001  # Меньший learning rate для аккуратного обучения
        )
    else:
        # Полное переобучение с нуля
        print(f"\n🏋️  Полное переобучение модели...")
        
        model = AutoencoderDL(
            input_dim=X.shape[1],
            bottleneck_dim=config['bottleneck_dim'],
            num_classes=num_classes
        )
        
        epochs = 50 if X.shape[0] < 30000 else 30
        history = model.train_classifier(
            X, y_cat,
            epochs=epochs,
            batch_size=32,
            validation_split=0.2,
            use_early_stopping=True,
            sample_weight=sample_weights
        )
    
    # 8. Сохранить модель
    model.save(classifier_path)
    
    # 9. Пометить исправления как использованные
    mark_corrections_as_used(marketplace)
    print(f"\n✅ Исправления помечены как использованные")
    
    print(f"\n✅ МОДЕЛЬ ПЕРЕОБУЧЕНА!")
    print(f"   Путь: {classifier_path}")
    print(f"   Категорий: {num_classes}")
    print(f"   Товаров: {X.shape[0]:,}")
    print(f"   Исправлений учтено: {len(corrections)}")
    
    return model, history

if __name__ == '__main__':
    import sys
    
    marketplace = sys.argv[1]
    retrain_with_corrections(marketplace)
