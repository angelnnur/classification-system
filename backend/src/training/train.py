"""
Обучение отдельных моделей для каждого маркетплейса
"""
import numpy as np
from keras.utils import to_categorical
import os
from pathlib import Path
from src.config import Config
    

from .processed import preprocess_data, save_preprocessing_objects
from ..models.autoencoder_model import AutoencoderDL

MARKETPLACE_CONFIG = {
    'wildberries': {
        'csv_file': 'src/data/raw/wildberries_products_list.csv',
        'category_column': 'category_path',
        'min_samples': 10,
        'max_features': 3000,
        'bottleneck_dim': 128
    },
    'ozon': {
        'csv_file': 'src/data/raw/ozon_products_list.csv',
        'category_column': 'category_path',
        'min_samples': 10,
        'max_features': 3000,
        'bottleneck_dim': 64
    },
    'yandex_market': {
        'csv_file': 'src/data/raw/yandex_market_products_list.csv',
        'category_column': 'category_path',
        'min_samples': 10,
        'max_features': 3000,
        'bottleneck_dim': 256
    }
}

def train_marketplace_model(marketplace_name: str, output_base_dir: str = None):
    print(f"Запуск обучения {marketplace_name}")
    if marketplace_name not in MARKETPLACE_CONFIG:
        raise ValueError(f"Неизвестный маркетплейс: {marketplace_name}. Доступные: {list(MARKETPLACE_CONFIG.keys())}")
    
    config = MARKETPLACE_CONFIG[marketplace_name]
    
    BASE_DIR = Path(__file__).parent.parent
    BACKEND_DIR = BASE_DIR.parent
    CSV_PATH = BACKEND_DIR / config['csv_file']

    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Файл не найден: {CSV_PATH}")
    
    if output_base_dir is None:
        output_base_dir = str(BACKEND_DIR / Config.MODELS_BIN)
    
    model_dir = os.path.join(output_base_dir, marketplace_name)
    os.makedirs(model_dir, exist_ok=True)
    
    X, y, vectorizer, to_id, to_label = preprocess_data(
        csv_file=str(CSV_PATH),
        min_samples_per_category=config['min_samples'],
        max_features=config['max_features']
    )
    
    y_cat = to_categorical(y)
    num_classes = y_cat.shape[1]
    
    save_preprocessing_objects(vectorizer, to_id, to_label, output_dir=model_dir)

    if X.shape[0] < 30000:
        epochs = 50
    else:
        epochs = 30

    model = AutoencoderDL(
        input_dim=X.shape[1],
        bottleneck_dim=config['bottleneck_dim'],
        num_classes=num_classes
    )
    
    history = model.train_classifier(
        X, y_cat,
        epochs=epochs,
        batch_size=32,
        validation_split=0.2,
        use_early_stopping=True
    )
    classifier_path = os.path.join(model_dir, 'classifier.h5')
    model.save(classifier_path)
    
    return model, history


def train_all_marketplaces():
    results = {}
    
    for marketplace in MARKETPLACE_CONFIG.keys():
        try:
            model, history = train_marketplace_model(marketplace)
            results[marketplace] = {
                'status': 'success',
                'final_accuracy': history.history['accuracy'][-1] if 'accuracy' in history.history else None
            }
        except Exception as e:
            import traceback
            traceback.print_exc()
            results[marketplace] = {'status': 'error', 'error': str(e)}
    
    return results


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        marketplace_name = sys.argv[1]
        train_marketplace_model(marketplace_name)
    else:
        train_all_marketplaces()
