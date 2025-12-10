import os
# 🎯 ייבוא רכיבים חדשים עבור מודל Task
from sqlalchemy import create_engine, Column, Integer, String, Boolean 
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 🎯 שחזור: הגדרת משתני סביבה (השמות DB_USER, DB_PASSWORD וכו' מוגדרים כאן)
DB_USER = os.getenv("POSTGRES_USER", "user")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "mydb")
DB_HOST = os.getenv("DB_HOST", "localhost") 
# הערה: ב-docker-compose.yaml, משתנה DB_HOST נדרס לערך "postgres"

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 🎯 מודל חדש: טבלת משימות (Todo App)
class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    is_completed = Column(Boolean, default=False)
    
# 🎯 פונקציה ליצירת הטבלאות
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
