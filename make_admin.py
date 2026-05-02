"""
Скрипт для установки администратора в системе.
"""

import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User


def main():
    db: Session = SessionLocal()
    
    # Список всех пользователей
    users = db.query(User).all()
    
    if not users:
        print("В системе нет пользователей. Сначала создайте пользователя через регистрацию.")
        db.close()
        return
    
    print("\nСписок пользователей в системе:\n")
    for user in users:
        admin_status = "✅ АДМИНИСТРАТОР" if user.is_admin else "❌ обычный"
        print(f"  ID: {user.id:2d} | {user.username:15s} | {user.email:30s} | {admin_status}")
    
    print("\n" + "="*70)
    user_id = input("\nВведите ID пользователя, которого сделать администратором: ").strip()
    
    try:
        user_id = int(user_id)
    except ValueError:
        print("Ошибка: ID должен быть числом.")
        db.close()
        return
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        print(f"Пользователь с ID {user_id} не найден.")
        db.close()
        return
    
    if user.is_admin:
        print(f"Пользователь {user.username} уже администратор.")
    else:
        user.is_admin = True
        db.add(user)
        db.commit()
        print(f"Пользователь {user.username} теперь администратор!")
    
    db.close()


if __name__ == "__main__":
    main()
