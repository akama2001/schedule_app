from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Specialty(db.Model):
    __tablename__ = 'specialties'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    
    groups = db.relationship('Group', backref='specialty', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Specialty {self.code}>'


class Group(db.Model):
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    course = db.Column(db.Integer, nullable=False, default=1)
    specialty_id = db.Column(db.Integer, db.ForeignKey('specialties.id'), nullable=False)
    
    lessons = db.relationship('Lesson', backref='group', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Group {self.name}>'


class Lesson(db.Model):
    __tablename__ = 'lessons'
    
    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(200), nullable=False)
    lesson_type = db.Column(db.String(50), nullable=False)
    lesson_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    teacher = db.Column(db.String(100), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    
    # Дата загрузки/обновления
    uploaded_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    def __repr__(self):
        return f'<Lesson {self.subject_name} {self.lesson_date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject_name,
            'type': self.lesson_type,
            'date': self.lesson_date.strftime('%Y-%m-%d'),
            'start': self.start_time.strftime('%H:%M'),
            'end': self.end_time.strftime('%H:%M'),
            'location': self.location,
            'teacher': self.teacher or 'Не указан',
            'day_of_week': self.get_day_name(),
            'short_date': self.lesson_date.strftime('%d.%m'),
            'uploaded_at': self.uploaded_at.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_day_name(self):
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return days[self.lesson_date.weekday()]
    
    def get_type_color(self):
        colors = {
            'Лекция': '#3b82f6',
            'Практика': '#10b981',
            'Лабораторная': '#f59e0b'
        }
        return colors.get(self.lesson_type, '#6b7280')


class UploadLog(db.Model):
    """Лог загрузок данных"""
    __tablename__ = 'upload_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=True)
    records_count = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.now, nullable=False)
    uploaded_by = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), default='success')
    message = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<UploadLog {self.uploaded_at}>'