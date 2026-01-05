import pandas as pd
import pickle
import os
from config import Config
from sklearn.feature_extraction.text import TfidfVectorizer

def preprocess_data(csv_file, min_samples_per_category=20):
    # 1. Открытие файла
    df = pd.read_csv(csv_file)

    # 2. Проверка на наличие полей
    if 'product_name' not in df.columns or 'category' not in df.columns:
        raise ValueError("В файле отсутствует информация о товарах или категория!")

    # 3. Очистка
    df = df.drop_duplicates(subset=['product_name']) # удаление дублей

    df['product_name'] = df['product_name'].fillna('').astype(str).str.strip() # удаление пустых строк
    df = df[df['product_name'] != '']

    category_counts = df['category'].value_counts()
    valid_categories = category_counts[category_counts >= min_samples_per_category].index
    df = df[df['category'].isin(valid_categories)] # удаление категорий, которые содержать меньше 20 товаров для исключения выбросов

    # 4. Векторизация
    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(df['product_name']).toarray()

    # 5. Создание словаря из категорий
    unique_categories = sorted(df['category'].unique())
    to_id = {cat: i for i, cat in enumerate(unique_categories)}
    to_label = {i: cat for cat, i in to_id.items()}

    y = df['category'].map(to_id).values

    return X, y, vectorizer, to_id, to_label


def save_preprocessing_objects(vectorizer, to_id, to_label, output_dir=Config.MODELS_BIN):
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'tokenizer.pkl'), 'wb') as f:
        pickle.dump(vectorizer, f)

    with open(os.path.join(output_dir, 'label2idx.pkl'), 'wb') as f:
        pickle.dump(to_id, f)

    with open(os.path.join(output_dir, 'idx2label.pkl'), 'wb') as f:
        pickle.dump(to_label, f)

def load_preprocessing_objects(output_dir=Config.MODELS_BIN):
    # Gunicorn запускается с --chdir src, поэтому рабочая директория /app/src
    # Файлы находятся в /app/src/data/models_bin/
    # Config.MODELS_BIN = "src/data/models_bin", но нужно "data/models_bin"
    
    # Пробуем разные варианты путей
    possible_paths = [
        output_dir,  # "src/data/models_bin" (для локального запуска без --chdir)
        output_dir.replace('src/', ''),  # "data/models_bin" (для Docker с --chdir src)
        os.path.join('backend', output_dir),  # "backend/src/data/models_bin" (для локальной разработки)
    ]
    
    found_path = None
    for path in possible_paths:
        tokenizer_path = os.path.join(path, 'tokenizer.pkl')
        if os.path.exists(tokenizer_path):
            found_path = path
            break
    
    if not found_path:
        # Показываем текущую рабочую директорию для отладки
        cwd = os.getcwd()
        raise FileNotFoundError(
            f"Не найдены файлы моделей.\n"
            f"Текущая рабочая директория: {cwd}\n"
            f"Пробовали пути: {possible_paths}\n"
            f"Ожидаемые файлы: tokenizer.pkl, label2idx.pkl, idx2label.pkl"
        )
    
    with open(os.path.join(found_path, 'tokenizer.pkl'), 'rb') as f:
        vectorizer = pickle.load(f)

    with open(os.path.join(found_path, 'label2idx.pkl'), 'rb') as f:
        to_id = pickle.load(f)

    with open(os.path.join(found_path, 'idx2label.pkl'), 'rb') as f:
        to_label = pickle.load(f)

    return vectorizer, to_id, to_label