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
    output_dir = 'backend/' + output_dir
    with open(os.path.join(output_dir, 'tokenizer.pkl'), 'rb') as f:
        vectorizer = pickle.load(f)

    with open(os.path.join(output_dir, 'label2idx.pkl'), 'rb') as f:
        to_id = pickle.load(f)

    with open(os.path.join(output_dir, 'idx2label.pkl'), 'rb') as f:
        to_label = pickle.load(f)

    return vectorizer, to_id, to_label