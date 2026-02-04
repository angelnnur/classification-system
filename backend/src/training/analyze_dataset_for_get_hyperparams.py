import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

def get_params(csv_path):
    df = pd.read_csv(csv_path)
    
    df = df.drop_duplicates(subset=['product_name'])
    df['product_name'] = df['product_name'].fillna('').astype(str)
    df['product_name'] = df['product_name'].str.lower().str.strip()
    df['product_name'] = df['product_name'].str.replace(r'\s+', ' ', regex=True)
    df = df[df['product_name'] != '']
    df = df[df['category_path'].notna()]

    # 1. min_samples
    category_counts = df['category_path'].value_counts()
    
    for min_samples in [5, 10, 15, 20, 30, 50]:
        valid_categories = category_counts[category_counts >= min_samples]
        if len(valid_categories) / len(category_counts) >= 0.8:
            best_min_samples = min_samples
            break
        else:
            best_min_samples = 10
    
    # 2. max_features
    vectorizer_all = TfidfVectorizer(max_features=None, lowercase=False)
    vectorizer_all.fit(df['product_name'])
    all_words = len(vectorizer_all.vocabulary_)
    
    if all_words < 2000:
        best_max_features = all_words
    else:
        best_max_features = min(3000, int(all_words * 0.8))

    # 3. bottleneck_dim
    valid_categories = category_counts[category_counts >= best_min_samples]
    count_categories = len(valid_categories)

    if count_categories < 50:
        bottleneck_dim = 64
    elif count_categories < 200:
        bottleneck_dim = 128
    elif count_categories < 500:
        bottleneck_dim = 256
    else:
        bottleneck_dim = 512
    
    if bottleneck_dim >= count_categories:
        bottleneck_dim = max(64, count_categories // 2)
    
    return {
        'min_samples': best_min_samples,
        'max_features': best_max_features,
        'bottleneck_dim': bottleneck_dim
    }

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python get_params.py путь/к/файлу.csv")
        sys.exit(1)
    
    result = get_params(sys.argv[1])
    print(f"min_samples: {result['min_samples']}")
    print(f"max_features: {result['max_features']}")
    print(f"bottleneck_dim: {result['bottleneck_dim']}")
