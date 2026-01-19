"""
Простая система обратной связи для исправления категорий
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import json
import os
from pathlib import Path
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__)

# Простое хранилище исправлений в JSON файле
FEEDBACK_FILE = "src/data/feedback_corrections.json"

def load_feedback():
    """Загрузить исправления из файла"""
    file_path = Path(FEEDBACK_FILE)
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_feedback(feedback_list):
    """Сохранить исправления в файл"""
    file_path = Path(FEEDBACK_FILE)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(feedback_list, f, ensure_ascii=False, indent=2)

@feedback_bp.route("/feedback/correct", methods=["POST"])
@jwt_required()
def correct_category():
    """Сохранить исправление категории"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        # Валидация
        required = ['product_name', 'marketplace', 'predicted_category', 'corrected_category']
        for field in required:
            if field not in data:
                return jsonify({'error': f'Отсутствует поле: {field}'}), 400
        
        # Загрузить существующие исправления
        feedback_list = load_feedback()
        
        # Добавить новое исправление
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
        
        # Автоматическое переобучение в фоне (если есть новые исправления)
        try:
            # Проверяем количество неиспользованных исправлений
            unused_count = sum(1 for f in feedback_list 
                             if f.get('marketplace') == marketplace 
                             and not f.get('used_for_training', False))
            
            # Если накопилось >= 10 исправлений, запускаем переобучение
            if unused_count >= 10:
                import threading
                from training.retrain_with_corrections import retrain_with_corrections
                
                def retrain_async():
                    try:
                        retrain_with_corrections(marketplace)
                    except Exception as e:
                        print(f"Ошибка при автоматическом переобучении: {e}")
                
                thread = threading.Thread(target=retrain_async, daemon=True)
                thread.start()
                
                return jsonify({
                    'message': 'Исправление сохранено',
                    'correction_id': correction['id'],
                    'note': f'Автоматическое переобучение запущено ({unused_count} исправлений)'
                }), 200
            else:
                return jsonify({
                    'message': 'Исправление сохранено',
                    'correction_id': correction['id'],
                    'note': f'Накоплено {unused_count}/10 исправлений для автоматического переобучения'
                }), 200
        except Exception as e:
            # Если переобучение не удалось, просто сохраняем исправление
            return jsonify({
                'message': 'Исправление сохранено',
                'correction_id': correction['id'],
                'note': f'Ошибка при попытке переобучения: {str(e)}'
            }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@feedback_bp.route("/feedback/list", methods=["GET"])
@jwt_required()
def list_feedback():
    """Получить список исправлений"""
    try:
        marketplace = request.args.get('marketplace')
        feedback_list = load_feedback()
        
        if marketplace:
            feedback_list = [f for f in feedback_list if f.get('marketplace') == marketplace]
        
        return jsonify({
            'feedback': feedback_list,
            'total': len(feedback_list)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
