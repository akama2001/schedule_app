import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-2026'
    
    # SQLite (простая альтернатива MySQL)
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(BASE_DIR, "schedule.db")}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки расписания
    SCHEDULE_WEEKS = 2
    LESSON_TYPES = ['Лекция', 'Практика', 'Лабораторная']