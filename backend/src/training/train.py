import numpy as np
from keras.utils import to_categorical
import os
from config import Config
from training.processed import preprocess_data, save_preprocessing_objects
from models.autoencoder_model import AutoencoderDL

def main():
    # 1. Открытия файла для обучения
    BASE_DIR = os.path.dirname(__file__)
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))
    CSV_PATH = os.path.join(PROJECT_ROOT, 'src/training/products_data_for_train.csv')

    # 2. Создать директорию, если не существует
    os.makedirs(Config.MODELS_BIN, exist_ok=True)

    X, y, vectorizer, to_id, to_label = preprocess_data(CSV_PATH)
    print(f'X.shape[1]: {X.shape[1]}')

    y_cat = to_categorical(y)
    num_classes = y_cat.shape[1]

    save_preprocessing_objects(vectorizer, to_id, to_label, Config.MODELS_BIN)

    model = AutoencoderDL(
        input_dim=X.shape[1],
        bottleneck_dim=64,
        num_classes=num_classes
    )
    model.train_classifier(X, y_cat, epochs=50, batch_size=16)
    model.save(
        os.path.join(Config.MODELS_BIN, 'encoder.h5'),
        os.path.join(Config.MODELS_BIN, 'classifier.h5')
    )
    print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")

if __name__ == '__main__':
    main()