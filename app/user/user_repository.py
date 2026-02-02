from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.user.user_schema import User

class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        query = text("SELECT email, password, username FROM users WHERE email = :email")
        result = self.db.execute(query, {"email": email}).fetchone()
        
        if result:
            return User(email=result[0], password=result[1], username=result[2])
        return None

    def save_user(self, user: User) -> User:
        existing_user = self.get_user_by_email(user.email)
        
        if existing_user:
            query = text("""
                UPDATE users 
                SET password = :password, username = :username 
                WHERE email = :email
            """)
        else:
            query = text("""
                INSERT INTO users (email, password, username) 
                VALUES (:email, :password, :username)
            """)
            
        self.db.execute(query, {
            "email": user.email,
            "password": user.password,
            "username": user.username
        })
        self.db.commit()
        return user

    def delete_user(self, user: User) -> User:
        query = text("DELETE FROM users WHERE email = :email")
        self.db.execute(query, {"email": user.email})
        self.db.commit()
        return user