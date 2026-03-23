# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Ассоциативная таблица для связи преподавателей и специальностей
teacher_specialties = db.Table('teacher_specialties',
    db.Column('teacher_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('specialty_id', db.Integer, db.ForeignKey('specialties.id'), primary_key=True)
)
class Location(db.Model):
    """Модель локации (здание, корпус)"""
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # "Главный корпус", "Лабораторный корпус"
    address = db.Column(db.String(200), nullable=True)             # Адрес
    rooms = db.relationship('Room', back_populates='location', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Location {self.name}>'


class Room(db.Model):
    """Модель помещения (аудитория, кабинет)"""
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)                # "101", "205", "Лаб. 401"
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    capacity = db.Column(db.Integer, nullable=True)                # Вместимость (опционально)
    type = db.Column(db.String(50), nullable=True)                 # Тип: "лекционная", "лабораторная", "компьютерный класс"
    location = db.relationship('Location', back_populates='rooms')
    lessons = db.relationship('Lesson', back_populates='room')     # связь с занятиями

    def __repr__(self):
        return f'<Room {self.name} ({self.location.name})>'

class Specialty(db.Model):
    """Модель специальности"""
    __tablename__ = 'specialties'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    # Связь с группами (каскадное удаление)
    groups = db.relationship('Group', backref='specialty', lazy=True, cascade='all, delete-orphan')
    # Связь с преподавателями, которые могут вести занятия по этой специальности
    teachers = db.relationship('User', secondary=teacher_specialties, back_populates='specialties')  # <-- добавлено

    def __repr__(self):
        return f'<Specialty {self.code}>'


class Group(db.Model):
    """Модель учебной группы"""
    __tablename__ = 'groups'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    course = db.Column(db.Integer, nullable=False, default=1)
    specialty_id = db.Column(db.Integer, db.ForeignKey('specialties.id'), nullable=False)
    student_count = db.Column(db.Integer, default=0, nullable=False)   # количество обучающихся

    lessons = db.relationship('Lesson', back_populates='group', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Group {self.name}>'


class User(db.Model):
    """Модель пользователя (админ, менеджер, преподаватель, студент)"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)  # Для студентов

    group = db.relationship('Group', backref='students')

    # Связь со специальностями, которые может вести преподаватель
    specialties = db.relationship('Specialty', secondary=teacher_specialties, back_populates='teachers')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def can_teach_group(self, group):
        """Проверяет, может ли преподаватель вести данную группу"""
        if not self.is_teacher():
            return False
        if not self.specialties:
            return True
        return group.specialty_id in [s.id for s in self.specialties]


    # Методы для Flask-Login
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

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

    def get_allowed_group_ids(self):
        """Возвращает список ID групп, которые может вести преподаватель.
           Если у преподавателя не указаны специальности, возвращает все группы (или пустой список?).
        """
        if not self.is_teacher():
            return []
        if not self.specialties:
            # Если специальности не заданы, преподаватель может вести любые группы
            # В зависимости от бизнес-логики, можно вернуть все группы или пустой список
            # Для простоты вернём все группы (это разрешит ему видеть все занятия)
            return [g.id for g in Group.query.all()]
        # Получаем все группы, которые относятся к специальностям преподавателя
        group_ids = []
        for spec in self.specialties:
            for group in spec.groups:
                group_ids.append(group.id)
        return list(set(group_ids))  # уникальные

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
    suggested_date = db.Column(db.Date, nullable=True)                 # Дата переноса занятия
    suggested_start_time = db.Column(db.Time, nullable=True)           # Время для переноса начало
    suggested_end_time = db.Column(db.Time, nullable=True)             # Время для переноса окончание
    uploaded_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)  # Время последнего обновления
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=True)  # новое поле
    room = db.relationship('Room', back_populates='lessons')
    time_slot_id = db.Column(db.Integer, db.ForeignKey('time_slots.id'), nullable=True) # Временной слот

    # Связи
    group = db.relationship('Group', back_populates='lessons')        # Двусторонняя связь с группой
    teacher_user = db.relationship('User', foreign_keys=[teacher_id], backref='lessons_teaching')  # Связь с преподавателем
    time_slot = db.relationship('TimeSlot', backref='lessons')
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
class TimeSlot(db.Model):
    __tablename__ = 'time_slots'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # например, "1-я пара"
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    order = db.Column(db.Integer, nullable=False)    # порядковый номер для сортировки

    def __repr__(self):
        return f'<TimeSlot {self.name} {self.start_time}-{self.end_time}>'

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