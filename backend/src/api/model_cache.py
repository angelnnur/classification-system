"""
Кэш для моделей ML - загружает модели один раз и переиспользует их
Это экономит память и ускоряет работу
"""
import os
# Убеждаемся, что GPU отключен перед импортом TensorFlow
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from functools import lru_cache
from training.processed import load_preprocessing_objects as _load_preprocessing_objects
from config import Config

# Глобальный кэш для моделей
_model_cache = {}
_vectorizer_cache = None
_label_mappings_cache = None

def get_preprocessing_objects():
    """Получить vectorizer и маппинги категорий (кэшируется)"""
    global _vectorizer_cache, _label_mappings_cache
    
    if _vectorizer_cache is None or _label_mappings_cache is None:
        vectorizer, to_id, to_label = _load_preprocessing_objects(Config.MODELS_BIN)
        _vectorizer_cache = vectorizer
        _label_mappings_cache = (to_id, to_label)
        print("✅ Preprocessing objects загружены в кэш")
    
    return _vectorizer_cache, _label_mappings_cache[0], _label_mappings_cache[1]

def get_model_key(input_dim, bottleneck_dim, num_classes, classifier_path):
    """Создать ключ для кэша модели"""
    return f"{input_dim}_{bottleneck_dim}_{num_classes}_{classifier_path}"

def get_cached_model(input_dim, bottleneck_dim, num_classes, classifier_path):
    """Получить модель из кэша или загрузить новую"""
    from models.autoencoder_model import AutoencoderDL
    
    model_key = get_model_key(input_dim, bottleneck_dim, num_classes, classifier_path)
    
    if model_key not in _model_cache:
        print(f"📦 Загрузка модели в кэш: {model_key}")
        model = AutoencoderDL(input_dim=input_dim, bottleneck_dim=bottleneck_dim, num_classes=num_classes)
        model.load_classifier(classifier_path)
        _model_cache[model_key] = model
        print(f"✅ Модель загружена в кэш")
    else:
        print(f"♻️  Использование модели из кэша")
    
    return _model_cache[model_key]

def clear_cache():
    """Очистить кэш моделей (для тестирования)"""
    global _model_cache, _vectorizer_cache, _label_mappings_cache
    _model_cache.clear()
    _vectorizer_cache = None
    _label_mappings_cache = None
    print("🗑️  Кэш моделей очищен")

