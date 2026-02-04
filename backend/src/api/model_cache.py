"""
Кэш моделей и дерева категорий по маркетплейсу.
Снижает повторную загрузку с диска при частых запросах.
"""
from threading import Lock

_models = {}  # marketplace -> (model, vectorizer, to_id, to_label, expected_dim)
_tree_cache = {}  # marketplace -> tree_data
_lock = Lock()


def get_cached_model(marketplace):
    """Вернуть закэшированную модель и препроцессинг или None."""
    with _lock:
        return _models.get(marketplace)


def set_cached_model(marketplace, model, vectorizer, to_id, to_label, expected_dim):
    """Сохранить модель в кэш."""
    with _lock:
        _models[marketplace] = (model, vectorizer, to_id, to_label, expected_dim)


def get_cached_tree(marketplace):
    """Вернуть закэшированное дерево категорий или None."""
    with _lock:
        return _tree_cache.get(marketplace)


def set_cached_tree(marketplace, tree_data):
    """Сохранить дерево в кэш."""
    with _lock:
        _tree_cache[marketplace] = tree_data


def invalidate_model(marketplace):
    """Сбросить кэш модели (например после переобучения)."""
    with _lock:
        _models.pop(marketplace, None)


def invalidate_tree(marketplace):
    """Сбросить кэш дерева."""
    with _lock:
        _tree_cache.pop(marketplace, None)
