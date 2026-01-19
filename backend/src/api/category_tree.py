"""
API для получения дерева категорий маркетплейса
"""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
import pandas as pd
from pathlib import Path
from typing import Dict, List

category_tree_bp = Blueprint('category_tree', __name__)

def build_category_tree_from_dataset(csv_file: str) -> Dict:
    """
    Построить дерево категорий из датасета
    
    Returns:
        {
            "categories": [
                {
                    "id": "category_id",
                    "name": "category_name",
                    "path": "Родитель/Дочерняя",
                    "parent": "Родитель",
                    "children": [],
                    "level": 0,
                    "full_path": "Родитель/Дочерняя"
                }
            ],
            "tree": {
                "Родитель": {
                    "children": ["Дочерняя1", "Дочерняя2"]
                }
            }
        }
    """
    if not Path(csv_file).exists():
        return {"categories": [], "tree": {}}
    
    df = pd.read_csv(csv_file)
    
    if 'category_path' not in df.columns:
        return {"categories": [], "tree": {}}
    
    # Получаем уникальные комбинации category_path, category_name, category_id
    if 'category_name' in df.columns and 'category_id' in df.columns:
        unique_cats = df[['category_id', 'category_name', 'category_path']].drop_duplicates()
    else:
        # Если нет category_name, извлекаем из пути
        unique_cats = df[['category_path']].drop_duplicates()
        unique_cats['category_name'] = unique_cats['category_path'].str.split('/').str[-1].str.strip()
        unique_cats['category_id'] = range(len(unique_cats))
    
    tree_nodes = {}  # name -> node info
    root_nodes = []
    
    for _, row in unique_cats.iterrows():
        category_id = str(row.get('category_id', ''))
        category_name = row.get('category_name', '')
        category_path = str(row['category_path'])
        
        # Разбираем путь на уровни
        path_parts = [p.strip() for p in category_path.split('/') if p.strip()]
        
        if not path_parts:
            continue
        
        # Строим иерархию снизу вверх
        for i in range(len(path_parts)):
            node_name = path_parts[i]
            parent_name = path_parts[i - 1] if i > 0 else None
            
            # Создаем или обновляем узел
            if node_name not in tree_nodes:
                tree_nodes[node_name] = {
                    "id": category_id if i == len(path_parts) - 1 else None,
                    "name": node_name,
                    "parent": parent_name,
                    "children": [],
                    "level": i,
                    "full_path": '/'.join(path_parts[:i+1])
                }
            
            # Обновляем ID для конечной категории
            if i == len(path_parts) - 1:
                tree_nodes[node_name]["id"] = category_id
                tree_nodes[node_name]["full_path"] = category_path
            
            # Добавляем в children родителя
            if parent_name and parent_name in tree_nodes:
                if node_name not in tree_nodes[parent_name]["children"]:
                    tree_nodes[parent_name]["children"].append(node_name)
    
    # Находим корневые узлы (без родителей)
    root_nodes = [name for name, node in tree_nodes.items() if node["parent"] is None]
    
    # Преобразуем в список для фронтенда
    categories_list = list(tree_nodes.values())
    
    return {
        "categories": categories_list,
        "tree": tree_nodes,
        "roots": root_nodes
    }

@category_tree_bp.route("/categories/tree", methods=["GET"])
@jwt_required()
def get_category_tree():
    """Получить дерево категорий для маркетплейса"""
    from flask import request
    from config import Config
    
    marketplace = request.args.get('marketplace', 'wildberries').strip().lower()
    
    valid_marketplaces = ['wildberries', 'ozon', 'yandex_market']
    if marketplace not in valid_marketplaces:
        return jsonify({'error': f'Неверный маркетплейс. Доступные: {", ".join(valid_marketplaces)}'}), 400
    
    # Путь к датасету
    BASE_DIR = Path(__file__).parent.parent
    PROJECT_ROOT = BASE_DIR.parent if BASE_DIR.name == 'src' else BASE_DIR
    dataset_path = PROJECT_ROOT / f'src/data/raw/{marketplace}_products_list.csv'
    
    if not dataset_path.exists():
        return jsonify({'error': f'Датасет для {marketplace} не найден'}), 404
    
    try:
        tree_data = build_category_tree_from_dataset(str(dataset_path))
        return jsonify({
            'marketplace': marketplace,
            **tree_data
        }), 200
    except Exception as e:
        return jsonify({'error': f'Ошибка при построении дерева: {str(e)}'}), 500
