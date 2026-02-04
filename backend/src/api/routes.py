from flask import Blueprint, request, jsonify
import json
import os
import re
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.utils import secure_filename
from database.models import User, db
from config import Config

api_bp = Blueprint('api', __name__)

VALID_MARKETPLACES = ['wildberries', 'ozon', 'yandex_market']
BOTTLENECK_DIMS = {'wildberries': 128, 'ozon': 128, 'yandex_market': 256}


def _load_model_for_marketplace(marketplace):
    """Загрузить модель и preprocessing для маркетплейса. Возвращает (model, vectorizer, to_id, to_label, expected_dim)."""
    from training.processed import load_preprocessing_objects
    from models.autoencoder_model import AutoencoderDL

    model_dir = os.path.join(Config.MODELS_BIN, marketplace)
    vectorizer, to_id, to_label = load_preprocessing_objects(model_dir)
    num_classes = len(to_id)
    bottleneck_dim = BOTTLENECK_DIMS[marketplace]

    possible_paths = [
        os.path.join(model_dir, 'classifier.h5'),
        os.path.join(model_dir.replace('src/', ''), 'classifier.h5'),
        os.path.join('backend', model_dir, 'classifier.h5'),
    ]
    classifier_path = None
    for p in possible_paths:
        if os.path.exists(p):
            classifier_path = p
            break
    if not classifier_path:
        raise FileNotFoundError(f'Не найдена модель для маркетплейса {marketplace}')

    sample_X = vectorizer.transform(['sample']).toarray()
    input_dim = sample_X.shape[1]
    model = AutoencoderDL(input_dim=input_dim, bottleneck_dim=bottleneck_dim, num_classes=num_classes)
    model.load_classifier(classifier_path)
    expected_dim = model.classifier.input_shape[-1]
    return model, vectorizer, to_id, to_label, expected_dim

FEEDBACK_FILE = "src/data/feedback_corrections.json"


def _dataset_path(marketplace):
    """Путь к сырому датасету маркетплейса."""
    base = Path(__file__).parent.parent
    project = base.parent if base.name == 'src' else base
    return project / f'src/data/raw/{marketplace}_products_list.csv'


def build_category_tree_from_dataset(csv_file):
    """Построить дерево категорий из CSV (category_id, category_name, category_path)."""
    if not Path(csv_file).exists():
        return {"categories": [], "tree": {}, "roots": []}
    df = pd.read_csv(csv_file)
    if 'category_path' not in df.columns:
        return {"categories": [], "tree": {}, "roots": []}
    if 'category_name' in df.columns and 'category_id' in df.columns:
        unique_cats = df[['category_id', 'category_name', 'category_path']].drop_duplicates()
    else:
        unique_cats = df[['category_path']].drop_duplicates()
        unique_cats['category_name'] = unique_cats['category_path'].str.split('/').str[-1].str.strip()
        unique_cats['category_id'] = range(len(unique_cats))
    tree_nodes = {}
    for _, row in unique_cats.iterrows():
        category_id = str(row.get('category_id', ''))
        category_name = row.get('category_name', '')
        category_path = str(row['category_path'])
        path_parts = [p.strip() for p in category_path.split('/') if p.strip()]
        if not path_parts:
            continue
        for i in range(len(path_parts)):
            node_name = path_parts[i]
            parent_name = path_parts[i - 1] if i > 0 else None
            if node_name not in tree_nodes:
                tree_nodes[node_name] = {
                    "id": category_id if i == len(path_parts) - 1 else None,
                    "name": node_name,
                    "parent": parent_name,
                    "children": [],
                    "level": i,
                    "full_path": '/'.join(path_parts[:i + 1])
                }
            if i == len(path_parts) - 1:
                tree_nodes[node_name]["id"] = category_id
                tree_nodes[node_name]["full_path"] = category_path
            if parent_name and parent_name in tree_nodes:
                if node_name not in tree_nodes[parent_name]["children"]:
                    tree_nodes[parent_name]["children"].append(node_name)
    roots = [n for n, node in tree_nodes.items() if node["parent"] is None]
    return {"categories": list(tree_nodes.values()), "tree": tree_nodes, "roots": roots}


def load_feedback():
    path = Path(FEEDBACK_FILE)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_feedback(feedback_list):
    path = Path(FEEDBACK_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(feedback_list, f, ensure_ascii=False, indent=2)

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


@api_bp.route("/predict_category", methods=["POST"])
@jwt_required()
def predict_category():
    data = request.get_json()
    product_name = data.get('product_name', '').strip()
    marketplace = data.get('marketplace', 'wildberries').strip().lower()

    if not product_name:
        return jsonify({'error': 'product_name не указано'}), 400

    if marketplace not in VALID_MARKETPLACES:
        return jsonify({'error': f'Неверный маркетплейс. Доступные: {", ".join(VALID_MARKETPLACES)}'}), 400

    product_name_normalized = re.sub(r'\s+', ' ', product_name.lower().strip())

    try:
        model, vectorizer, to_id, to_label, expected_dim = _load_model_for_marketplace(marketplace)
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({'error': f'Ошибка загрузки модели: {str(e)}'}), 500

    X = vectorizer.transform([product_name_normalized]).toarray()
    if X.shape[1] != expected_dim:
        if X.shape[1] > expected_dim:
            X = X[:, :expected_dim].astype(X.dtype)
        else:
            pad = np.zeros((X.shape[0], expected_dim - X.shape[1]), dtype=X.dtype)
            X = np.hstack([X, pad])

    pred_labels, pred_probs = model.predict_class(X)
    pred_label = pred_labels[0]
    confidence = float(pred_probs[0].max())

    top_3_raw = [
        {'category': to_label.get(idx, f'Category_{idx}'), 'confidence': float(pred_probs[0][idx])}
        for idx in pred_probs[0].argsort()[-3:][::-1]
    ]
    top_3 = [c for c in top_3_raw if c['confidence'] >= 0.5]

    if confidence < 0.5:
        category_name = 'Другая категория'
        category_path = 'Другая категория'
        hierarchy = ['Другая категория']
        category_id = None
        warning = f"Низкая уверенность ({confidence*100:.1f}%). Выберите категорию вручную."
    else:
        category_name = to_label.get(pred_label, f'Category_{pred_label}')
        dataset_path = _dataset_path(marketplace)
        category_path = category_name
        hierarchy = [category_name]
        category_id = None
        if dataset_path.exists():
            try:
                tree_data = build_category_tree_from_dataset(str(dataset_path))
                for cat in tree_data.get('categories', []):
                    if cat['name'] == category_name:
                        category_path = cat.get('full_path', category_name)
                        category_id = cat.get('id')
                        if '/' in category_path:
                            hierarchy = [level.strip() for level in category_path.split('/')]
                        else:
                            hierarchy = [category_name]
                        break
            except Exception as e:
                category_path = category_name
                hierarchy = [category_name]
        warning = None
        if confidence < 0.7:
            warning = f"Средняя уверенность ({confidence*100:.1f}%). Рекомендуется проверить результат."

    return json.dumps({
        'product_name': product_name,
        'marketplace': marketplace,
        'category': category_name,
        'category_path': category_path,
        'category_id': category_id,
        'hierarchy': hierarchy,
        'confidence': confidence,
        'top_3': top_3,
        'warning': warning
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

        if marketplace not in VALID_MARKETPLACES:
            return jsonify({'error': f'Неверный маркетплейс. Доступные: {", ".join(VALID_MARKETPLACES)}'}), 400

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

        df = df[df['product_name'].notna()]
        df['product_name'] = df['product_name'].astype(str).str.lower().str.strip()
        df['product_name'] = df['product_name'].str.replace(r'\s+', ' ', regex=True)
        df = df[df['product_name'] != '']
        if df.empty:
            return jsonify({'error': 'No valid product names in file'}), 400

        try:
            model, vectorizer, to_id, to_label, expected_dim = _load_model_for_marketplace(marketplace)
        except FileNotFoundError as e:
            return jsonify({'error': str(e)}), 500
        except Exception as e:
            return jsonify({'error': f'Ошибка загрузки модели: {str(e)}'}), 500

        path_to_id = {}
        dataset_path = _dataset_path(marketplace)
        if dataset_path.exists():
            try:
                tree_data = build_category_tree_from_dataset(str(dataset_path))
                path_to_id = {c['full_path']: c['id'] for c in tree_data.get('categories', []) if c.get('id')}
            except Exception:
                pass

        results = []
        for idx, product_name in enumerate(df['product_name'].values):
            try:
                X = vectorizer.transform([product_name]).toarray()
                if X.shape[1] != expected_dim:
                    if X.shape[1] > expected_dim:
                        X = X[:, :expected_dim].astype(X.dtype)
                    else:
                        pad = np.zeros((X.shape[0], expected_dim - X.shape[1]), dtype=X.dtype)
                        X = np.hstack([X, pad])
                pred_labels, pred_probs = model.predict_class(X)

                pred_label = pred_labels[0]
                confidence = float(pred_probs[0].max())
                category_path = to_label.get(pred_label, f'Category_{pred_label}')
                top_3_raw = [
                    {'category': to_label.get(int(idx), f'Category_{int(idx)}'), 'confidence': float(pred_probs[0][int(idx)])}
                    for idx in pred_probs[0].argsort()[-3:][::-1]
                ]
                top_3 = [c for c in top_3_raw if c['confidence'] >= 0.5]

                if confidence < 0.5:
                    category_name = 'Другая категория'
                    category_path = 'Другая категория'
                    hierarchy = ['Другая категория']
                    category_id = None
                else:
                    category_id = path_to_id.get(category_path)
                    hierarchy = [level.strip() for level in category_path.split('/')]
                    category_name = hierarchy[-1] if hierarchy else category_path

                results.append({
                    'product_name': product_name,
                    'category': category_name,
                    'category_path': category_path,
                    'category_id': category_id,
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


@api_bp.route("/categories/tree", methods=["GET"])
@jwt_required()
def get_category_tree():
    """Дерево категорий маркетплейса (для выбора категории на фронте)."""
    marketplace = request.args.get('marketplace', 'wildberries').strip().lower()
    if marketplace not in VALID_MARKETPLACES:
        return jsonify({'error': f'Неверный маркетплейс. Доступные: {", ".join(VALID_MARKETPLACES)}'}), 400
    dataset_path = _dataset_path(marketplace)
    if not dataset_path.exists():
        return jsonify({'error': f'Датасет для {marketplace} не найден'}), 404
    try:
        tree_data = build_category_tree_from_dataset(str(dataset_path))
        return jsonify({'marketplace': marketplace, **tree_data}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route("/feedback/correct", methods=["POST"])
@jwt_required()
def correct_category():
    """Сохранить исправление категории. Переобучение запускается автоматически при накоплении >= 10 исправлений по маркетплейсу."""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        required = ['product_name', 'marketplace', 'predicted_category', 'corrected_category']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Отсутствует поле: {field}'}), 400
        feedback_list = load_feedback()
        correction = {
            'id': len(feedback_list) + 1,
            'user_id': user_id,
            'product_name': data['product_name'],
            'marketplace': data['marketplace'],
            'predicted_category': data['predicted_category'],
            'corrected_category': data['corrected_category'],
            'confidence': data.get('confidence', 0),
            'timestamp': datetime.now().isoformat(),
            'used_for_training': False
        }
        feedback_list.append(correction)
        save_feedback(feedback_list)
        marketplace = data['marketplace']
        unused_count = sum(1 for f in feedback_list if f.get('marketplace') == marketplace and not f.get('used_for_training', False))
        if unused_count >= 1:
            import threading
            try:
                from training.retrain_with_corrections import retrain_with_corrections
                def retrain_async(mp_name):
                    try:
                        retrain_with_corrections(mp_name)
                    except Exception as e:
                        print(f"[RETRAIN ERROR] {e}")
                thread = threading.Thread(target=retrain_async, args=(marketplace,), daemon=True)
                thread.start()
                return jsonify({
                    'message': 'Исправление сохранено',
                    'correction_id': correction['id'],
                    'note': f'Автоматическое переобучение запущено ({unused_count} исправлений)'
                }), 200
            except ImportError:
                pass
        return jsonify({
            'message': 'Исправление сохранено',
            'correction_id': correction['id'],
            'note': f'Накоплено {unused_count} исправлений; переобучение запускается при каждом новом исправлении'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
