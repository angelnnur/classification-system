"""Переобучение модели по маркетплейсу (простая заглушка — просто запускает обучение)."""
import sys
from pathlib import Path

# Чтобы импорты (config, models, training) работали при вызове из потока Flask
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


def retrain_with_corrections(marketplace: str):
    """Запустить переобучение модели для маркетплейса."""
    try:
        from training.train import train_marketplace_model
        train_marketplace_model(marketplace)
        print(f"[RETRAIN] Готово: {marketplace}")
    except Exception as e:
        print(f"[RETRAIN] Ошибка для {marketplace}: {e}")
