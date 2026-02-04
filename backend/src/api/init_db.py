"""
Скрипт для инициализации БД (запускать отдельно, не при старте приложения)
"""
from api.app import create_app
from database.models import db, User

def init_db():
    """Создать таблицы и добавить начального пользователя"""
    app = create_app()
    with app.app_context():
        # Создать таблицы
        db.create_all()
        print("✅ Таблицы БД созданы")
        
        # Проверить, есть ли уже пользователи
        if User.query.count() == 0:
            # Создать админа по умолчанию
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')  # Изменить в продакшене!
            db.session.add(admin)
            db.session.commit()
            print("✅ Создан пользователь admin/admin123")
        else:
            print("ℹ️ Пользователи уже существуют")

if __name__ == '__main__':
    init_db()
