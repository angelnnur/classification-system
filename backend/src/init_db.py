"""
Скрипт для инициализации базы данных
Запустите этот скрипт после первого деплоя для создания таблиц и первого админа
"""
from api.app import create_app
from database.models import db, User
import os

def init_database():
    app = create_app()
    
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("✅ Таблицы созданы")
        
        # Проверяем, есть ли уже админ
        admin = User.query.filter_by(username='admin').first()
        
        if not admin:
            # Создаем первого админа
            admin = User(username='admin', role='admin')
            # Пароль по умолчанию - измените его после первого входа!
            default_password = os.getenv('ADMIN_DEFAULT_PASSWORD', 'admin123')
            admin.set_password(default_password)
            db.session.add(admin)
            db.session.commit()
            print(f"✅ Админ создан (username: admin, password: {default_password})")
            print("⚠️  ВАЖНО: Измените пароль после первого входа!")
        else:
            print("ℹ️  Админ уже существует")
        
        # Показываем всех пользователей
        users = User.query.all()
        print(f"\n📊 Всего пользователей: {len(users)}")
        for user in users:
            print(f"  - {user.username} ({user.role})")

if __name__ == '__main__':
    init_database()

