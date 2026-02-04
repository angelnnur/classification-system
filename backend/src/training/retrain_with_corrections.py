import sys
from pathlib import Path

_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))


def retrain_with_corrections(marketplace: str):
    from training.train import train_marketplace_model
    train_marketplace_model(marketplace)
    print(f"[RETRAIN] Готово: {marketplace}")
    