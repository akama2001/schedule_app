# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class Specialty(db.Model):
    """Модель специальности"""
    __tablename__ = 'specialties'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)      # Код специальности
    name = db.Column(db.String(200), nullable=False)                  # Название

    # Связь с группами (каскадное удаление)
    groups = db.relationship('Group', backref='specialty', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Specialty {self.code}>'


class Group(db.Model):
    """Модель учебной группы"""
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)                   # Название группы
    course = db.Column(db.Integer, nullable=False, default=1)         # Курс
    specialty_id = db.Column(db.Integer, db.ForeignKey('specialties.id'), nullable=False)

    # Связь с занятиями (каскадное удаление). Используем back_populates для двусторонней связи
    lessons = db.relationship('Lesson', back_populates='group', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Group {self.name}>'


class User(db.Model):
    """Модель пользователя (админ, менеджер, преподаватель, студент)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)   # Логин
    email = db.Column(db.String(120), unique=True, nullable=False)     # Email
    password_hash = db.Column(db.String(200), nullable=False)          # Хеш пароля
    role = db.Column(db.String(20), nullable=False, default='student') # Роль: admin/manager/teacher/student
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)  # Для студентов

    # Связь с группой (для студентов)
    group = db.relationship('Group', backref='students')

    def set_password(self, password):
        """Установка пароля (хеширование)"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Проверка пароля"""
        return check_password_hash(self.password_hash, password)

    # Методы, необходимые для Flask-Login
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    # Проверки ролей
    def has_role(self, role):
        return self.role == role

    def is_admin(self):
        return self.role == 'admin'

    def is_manager(self):
        return self.role == 'manager'

    def is_teacher(self):
        return self.role == 'teacher'

    def is_student(self):
        return self.role == 'student'

    def __repr__(self):
        return f'<User {self.username}>'


class Lesson(db.Model):
    """Модель занятия (урока, пары)"""
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    subject_name = db.Column(db.String(200), nullable=False)          # Название предмета
    lesson_type = db.Column(db.String(50), nullable=False)            # Тип: Лекция, Практика, Лабораторная
    lesson_date = db.Column(db.Date, nullable=False, index=True)      # Дата проведения
    start_time = db.Column(db.Time, nullable=False)                   # Время начала
    end_time = db.Column(db.Time, nullable=False)                     # Время окончания
    location = db.Column(db.String(100), nullable=False)              # Аудитория
    teacher = db.Column(db.String(100), nullable=True)                # ФИО преподавателя (строковое поле для совместимости)
    teacher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Ссылка на преподавателя (пользователя)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)  # Группа
    status = db.Column(db.String(20), default='scheduled', nullable=False)        # Статус: scheduled/confirmed/needs_reschedule/cancelled
    uploaded_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)  # Время последнего обновления

    # Связи
    group = db.relationship('Group', back_populates='lessons')        # Двусторонняя связь с группой
    teacher_user = db.relationship('User', foreign_keys=[teacher_id], backref='lessons_teaching')  # Связь с преподавателем

    def __repr__(self):
        return f'<Lesson {self.subject_name} {self.lesson_date}>'

    def to_dict(self):
        """Преобразование занятия в словарь для JSON"""
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
        """Возвращает название дня недели"""
        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        return days[self.lesson_date.weekday()]

    def get_type_color(self):
        """Возвращает цвет для типа занятия (для стилизации)"""
        colors = {
            'Лекция': '#3b82f6',
            'Практика': '#10b981',
            'Лабораторная': '#f59e0b'
        }
        return colors.get(self.lesson_type, '#6b7280')


class UploadLog(db.Model):
    """Лог загрузок/обновлений расписания"""
    __tablename__ = 'upload_logs'

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=True)               # Имя файла (если загружали файлом)
    records_count = db.Column(db.Integer, default=0)                  # Количество записей
    uploaded_at = db.Column(db.DateTime, default=datetime.now, nullable=False)  # Дата и время загрузки
    uploaded_by = db.Column(db.String(100), nullable=True)            # Кто загрузил (имя пользователя или 'system')
    status = db.Column(db.String(50), default='success')              # Статус: success, error, partial
    message = db.Column(db.Text, nullable=True)                       # Сообщение (ошибки или описание)

    def __repr__(self):
        return f'<UploadLog {self.uploaded_at}>'