from flask import Blueprint, request, jsonify, send_file
import json
import os
import re
import pandas as pd
import numpy as np
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from database.models import User, db
from config import Config

api_bp = Blueprint('api', __name__)

@api_bp.route('/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Username и password обязательны'}), 400

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Incorrect data or user not found'}), 401

        access_token = create_access_token(identity=user.id,
                                           additional_claims={
                                               "username": user.username,
                                               "role": user.role,
                                               "sub": str(user.id)
                                           })

        return jsonify({
            'token': access_token,
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/auth/register', methods=['POST'])
@jwt_required() #для отправки запроса к данному методу, необходимо отправлять токен
def register():
    claims = get_jwt()
    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if not username or not password:
        return jsonify({'error': 'Username и password обязательны'}), 400

    # Проверим, что такого пользователя ещё нет:
    if User.query.filter_by(username=username).first():
        return jsonify({'error': f'Пользователь с логином {username} уже существует'}), 409

    # Создаём нового пользователя и хешируем пароль
    new_user = User(username=username, role=role)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': f'Пользователь {username} зарегистрирован!'}), 201

@api_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files['file']
    filename = secure_filename(file.filename)
    path = os.path.join(Config.UPLOAD_FOLDER, filename)
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    file.save(path)
    return jsonify({"filepath": path}), 200


@api_bp.route("/preprocess", methods=["POST"])
@jwt_required()
def preprocess():
    from tensorflow.keras.preprocessing.text import Tokenizer
    from tensorflow.keras.preprocessing.sequence import pad_sequences

    data = request.get_json()
    filepath = data.get('filepath')
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "No such file"}), 404

    df = pd.read_csv(filepath)
    df = df.drop_duplicates(subset=['product_name'])
    df = df[df['product_name'].str.strip() != ""]
    df['product_name'] = df['product_name'].fillna("").astype(str)

    texts = df['product_name'].fillna("").apply(str).tolist()

    # Tokenizer + pad_sequences (как при обучении)
    tokenizer = Tokenizer(num_words=10000)
    tokenizer.fit_on_texts(texts)
    X = pad_sequences(tokenizer.texts_to_sequences(texts), maxlen=50)

    proc_path = os.path.join(Config.PROCESSED_FOLDER, os.path.basename(filepath) + ".npy")
    os.makedirs(Config.PROCESSED_FOLDER, exist_ok=True)
    np.save(proc_path, X)

    return jsonify({"features": X.tolist(), "processed_path": proc_path}), 200

@api_bp.route("/predict", methods=["POST"])
@jwt_required()
def predict():
    from models.autoencoder_model import AutoencoderDL
    data = request.get_json()
    if "features" in data:
        X = np.array(data['features'])
    elif "processed_path" in data:
        X = np.load(data['processed_path'])
    else:
        return jsonify({"error":"No features"}), 400
    model_type = data.get("model_type", "autoencoder")
    weights_path = data.get("weights_path", os.path.join(Config.MODELS_BIN, "autoencoder_final.h5"))
    if model_type == "autoencoder":
        model = AutoencoderDL(input_dim=X.shape[1])
        model.load(weights_path)
        clusters, embeds = model.predict_clusters(X, n_clusters=data.get('n_clusters', 10))
        return jsonify({"clusters": clusters.tolist(), "embeddings": embeds.tolist()})
    else:
        return jsonify({"error": "Model type not supported in demo"}), 400

@api_bp.route("/predict_category", methods=["POST"])
@jwt_required()
def predict_category():
    from training.processed import load_preprocessing_objects
    from models.autoencoder_model import AutoencoderDL

    data = request.get_json()
    product_name = data.get('product_name', '').strip()
    marketplace = data.get('marketplace', 'wildberries').strip().lower()  # По умолчанию wildberries

    if not product_name:
        return jsonify({'error': 'product_name не указано'}), 400

    valid_marketplaces = ['wildberries', 'ozon', 'yandex_market']
    if marketplace not in valid_marketplaces:
        return jsonify({'error': f'Неверный маркетплейс. Доступные: {", ".join(valid_marketplaces)}'}), 400

    product_name_normalized = product_name.lower().strip()
    product_name_normalized = re.sub(r'\s+', ' ', product_name_normalized)

    model_dir = os.path.join(Config.MODELS_BIN, marketplace)
    vectorizer, to_id, to_label = load_preprocessing_objects(model_dir)

    X = vectorizer.transform([product_name_normalized]).toarray()
    input_dim = X.shape[1]
    num_classes = len(to_id)
    

    bottleneck_dims = {
        'wildberries': 128,
        'ozon': 128,
        'yandex_market': 256
    }
    bottleneck_dim = bottleneck_dims[marketplace]
    
    possible_paths = [
        os.path.join(model_dir, 'classifier.h5'),
        os.path.join(model_dir.replace('src/', ''), 'classifier.h5'),
        os.path.join('backend', model_dir, 'classifier.h5'),
    ]
    
    classifier_path = None
    for path in possible_paths:
        if os.path.exists(path):
            classifier_path = path
            break
    
    if not classifier_path:
        return jsonify({'error': f'Не найдена модель для маркетплейса {marketplace}. Пробовали пути: {possible_paths}'}), 500
    
    # Загружаем модель
    model = AutoencoderDL(input_dim=input_dim, bottleneck_dim=bottleneck_dim, num_classes=num_classes)
    model.load_classifier(classifier_path)

    pred_labels, pred_probs = model.predict_class(X)
    pred_label = pred_labels[0]
    confidence = float(pred_probs[0].max())

    top_3_indices = pred_probs[0].argsort()[-3:][::-1]
    top_3 = [
        {
            'category': to_label.get(idx, f'Category_{idx}'),
            'confidence': float(pred_probs[0][idx])
        }
        for idx in top_3_indices
    ]

    category_path = to_label.get(pred_label, f'Category_{pred_label}')
    
    hierarchy = [level.strip() for level in category_path.split('/')]
    category_name = hierarchy[-1] if hierarchy else category_path

    return json.dumps({
        'product_name': product_name,
        'marketplace': marketplace,
        'category': category_name,
        'category_path': category_path,
        'hierarchy': hierarchy,
        'confidence': confidence,
        'top_3': top_3
    }, ensure_ascii=False, indent=2), 200


@api_bp.route("/predict_category_from_file", methods=["POST"])
@jwt_required()
def predict_category_from_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        marketplace = request.form.get('marketplace', 'wildberries').strip().lower()  # Получаем из form-data

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are supported'}), 400

        # Валидация маркетплейса
        valid_marketplaces = ['wildberries', 'ozon', 'yandex_market']
        if marketplace not in valid_marketplaces:
            return jsonify({'error': f'Неверный маркетплейс. Доступные: {", ".join(valid_marketplaces)}'}), 400

        filename = secure_filename(file.filename)
        temp_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file.save(temp_path)

        try:
            df = pd.read_csv(temp_path)
        except Exception as e:
            return jsonify({'error': f'Failed to read CSV: {str(e)}'}), 400

        if 'product_name' not in df.columns:
            return jsonify({'error': 'CSV must have a "product_name" column'}), 400

        # Очищаем данные
        df = df[df['product_name'].notna()]
        df['product_name'] = df['product_name'].astype(str).str.lower().str.strip()
        df['product_name'] = df['product_name'].str.replace(r'\s+', ' ', regex=True)  # множественные пробелы -> один
        df = df[df['product_name'] != '']

        if df.empty:
            return jsonify({'error': 'No valid product names in file'}), 400

        # Загружаем preprocessing objects
        from training.processed import load_preprocessing_objects
        from models.autoencoder_model import AutoencoderDL
        
        # Путь к модели для конкретного маркетплейса
        model_dir = os.path.join(Config.MODELS_BIN, marketplace)
        vectorizer, to_id, to_label = load_preprocessing_objects(model_dir)
        num_classes = len(to_id)

        # Получаем размерность из первого примера
        sample_X = vectorizer.transform([df['product_name'].iloc[0]]).toarray()
        input_dim = sample_X.shape[1]
        
        # Определяем bottleneck_dim
        bottleneck_dims = {
            'wildberries': 128,
            'ozon': 128,
            'yandex_market': 256
        }
        bottleneck_dim = bottleneck_dims[marketplace]
        
        # Путь к модели
        possible_paths = [
            os.path.join(model_dir, 'classifier.h5'),
            os.path.join(model_dir.replace('src/', ''), 'classifier.h5'),
            os.path.join('backend', model_dir, 'classifier.h5'),
        ]
        
        classifier_path = None
        for path in possible_paths:
            if os.path.exists(path):
                classifier_path = path
                break
        
        if not classifier_path:
            return jsonify({'error': f'Не найдена модель для маркетплейса {marketplace}. Пробовали пути: {possible_paths}'}), 500
        
        # Загружаем модель
        model = AutoencoderDL(input_dim=input_dim, bottleneck_dim=bottleneck_dim, num_classes=num_classes)
        model.load_classifier(classifier_path)

        results = []
        for idx, product_name in enumerate(df['product_name'].values):
            try:
                X = vectorizer.transform([product_name]).toarray()
                pred_labels, pred_probs = model.predict_class(X)

                pred_label = pred_labels[0]
                confidence = float(pred_probs[0].max())
                category_path = to_label.get(pred_label, f'Category_{pred_label}')

                # Разбираем путь на уровни иерархии
                hierarchy = [level.strip() for level in category_path.split('/')]
                category_name = hierarchy[-1] if hierarchy else category_path

                # Получаем топ-3
                top_3_indices = pred_probs[0].argsort()[-3:][::-1]
                top_3 = [
                    {
                        'category': to_label.get(int(idx), f'Category_{int(idx)}'),
                        'confidence': float(pred_probs[0][int(idx)])
                    }
                    for idx in top_3_indices
                ]

                results.append({
                    'product_name': product_name,
                    'category': category_name,
                    'category_path': category_path,
                    'hierarchy': hierarchy,
                    'confidence': (confidence * 100),
                    'top_3': top_3
                })
            except Exception as e:
                # Если ошибка для одного товара - добавляем в результаты с ошибкой
                results.append({
                    'product_name': product_name,
                    'category': 'Error',
                    'confidence': 0,
                    'top_3': [],
                    'error': str(e)
                })

        # Очищаем временный файл
        try:
            (os.
             remove(temp_path))
        except:
            pass

        return jsonify({
            'marketplace': marketplace,
            'results': results,
            'total': len(results),
            'success': len([r for r in results if 'error' not in r])
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route("/metrics/plot", methods=["POST"])
@jwt_required()
def get_plot():
    import os
    import matplotlib.pyplot as plt
    from sklearn.manifold import TSNE

    # Определяем абсолютные пути для сохранения и выдачи файла
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..', '..'))
    plot_dir = os.path.join(PROJECT_ROOT, "data", "plots")
    os.makedirs(plot_dir, exist_ok=True)
    plot_path = os.path.join(plot_dir, "tsne.png")

    data = request.get_json()
    embeddings = np.array(data['embeddings'])
    clusters = np.array(data['clusters'])
    tsne = TSNE(n_components=2, random_state=0)
    X_2d = tsne.fit_transform(embeddings)
    plt.figure(figsize=(6,5))
    plt.scatter(X_2d[:,0], X_2d[:,1], c=clusters, cmap='tab10', s=6)
    plt.title("Кластеры товаров")
    plt.savefig(plot_path)
    plt.close()
    return send_file(plot_path, mimetype="image/png")

@api_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    """Получить список всех пользователей (только админы)"""
    claims = get_jwt()

    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    try:
        users = User.query.all()
        users_data = [{
            'id': user.id,
            'username': user.username,
            'role': user.role,
            'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') else None
        } for user in users]

        return jsonify({'users': users_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Удалить пользователя (только админы)"""
    claims = get_jwt()
    current_user_id = get_jwt_identity()

    if claims.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403

    try:
        # Защита от удаления самого себя
        if int(current_user_id) == user_id:
            return jsonify({'error': 'Вы не можете удалить собственный аккаунт'}), 400

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        db.session.delete(user)
        db.session.commit()

        return jsonify({'message': f'Пользователь {user.username} удалён'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Получить информацию о текущем пользователе"""
    user_id = get_jwt_identity()
    claims = get_jwt()

    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'id': user.id,
            'username': user.username,
            'role': user.role
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

