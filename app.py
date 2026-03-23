from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
from config import Config
from models import db, Specialty, Group, Lesson, UploadLog, User, Location, Room, TimeSlot
from flask_migrate import Migrate
from flask_login import AnonymousUserMixin
import random
import os

# ==================== ИНИЦИАЛИЗАЦИЯ ПРИЛОЖЕНИЯ ====================
app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_week_start(date=None):
    if date is None:
        date = datetime.now().date()
    return date - timedelta(days=date.weekday())

def get_two_weeks_dates(start_date=None):
    if start_date is None:
        start_date = get_week_start()
    dates = []
    for week in range(2):
        for day in range(7):
            current = start_date + timedelta(weeks=week, days=day)
            dates.append(current)
    return dates

def get_last_update_time():
    last_lesson = Lesson.query.order_by(Lesson.uploaded_at.desc()).first()
    if last_lesson:
        return last_lesson.uploaded_at
    return None

def get_teachers_for_group(group_id):
    """Возвращает список преподавателей, которые могут вести данную группу"""
    group = Group.query.get(group_id)
    if not group:
        return []
    teachers = User.query.filter_by(role='teacher').all()
    return [t for t in teachers if t.can_teach_group(group)]

def generate_test_data():
    """Генерация тестовых данных: специальности, группы, занятия, локации, помещения, слоты"""
    print("Генерация тестовых данных...")
    
    # Очистка старых данных
    db.session.query(Lesson).delete()
    db.session.query(Group).delete()
    db.session.query(Specialty).delete()
    db.session.query(UploadLog).delete()
    db.session.query(Room).delete()
    db.session.query(Location).delete()
    db.session.query(TimeSlot).delete()
    db.session.commit()
    
    # Специальности
    specialties_data = [
        {'code': '09.03.01', 'name': 'Информатика и вычислительная техника'},
        {'code': '09.03.04', 'name': 'Программная инженерия'},
        {'code': '09.03.05', 'name': 'Искусственный интеллект и машинное обучение'},
        {'code': '10.03.01', 'name': 'Информационная безопасность'},
        {'code': '38.03.01', 'name': 'Экономика'},
        {'code': '38.03.02', 'name': 'Менеджмент'},
        {'code': '40.03.01', 'name': 'Юриспруденция'},
        {'code': '42.03.01', 'name': 'Реклама и связи с общественностью'}
    ]
    
    specs = {}
    for data in specialties_data:
        spec = Specialty(**data)
        db.session.add(spec)
        specs[data['code']] = spec
    db.session.commit()
    
    # Создаём временные слоты
    time_slots_data = [
        {'order': 1, 'name': '1-я пара', 'start_time': '08:30', 'end_time': '10:05'},
        {'order': 2, 'name': '2-я пара', 'start_time': '10:20', 'end_time': '11:55'},
        {'order': 3, 'name': '3-я пара', 'start_time': '12:10', 'end_time': '13:45'},
        {'order': 4, 'name': '4-я пара', 'start_time': '14:15', 'end_time': '15:50'},
        {'order': 5, 'name': '5-я пара', 'start_time': '16:05', 'end_time': '17:40'},
        {'order': 6, 'name': '6-я пара', 'start_time': '17:50', 'end_time': '19:25'},
    ]
    for slot_data in time_slots_data:
        slot = TimeSlot(
            order=slot_data['order'],
            name=slot_data['name'],
            start_time=datetime.strptime(slot_data['start_time'], '%H:%M').time(),
            end_time=datetime.strptime(slot_data['end_time'], '%H:%M').time()
        )
        db.session.add(slot)
    db.session.commit()
    
    all_slots = TimeSlot.query.order_by(TimeSlot.order).all()
    
    # Группы
    for spec_code, spec in specs.items():
        prefix = spec_code.split('.')[0]
        for course in [1, 2, 3, 4]:
            for num in range(1, 4):
                if prefix == '09':
                    prefix_name = 'ИВТ' if 'Информатика' in spec.name else 'ПИ' if 'Программная' in spec.name else 'ИИ'
                elif prefix == '10':
                    prefix_name = 'ИБ'
                elif prefix == '38':
                    prefix_name = 'ЭКО' if 'Экономика' in spec.name else 'МЕН'
                elif prefix == '40':
                    prefix_name = 'ЮР'
                else:
                    prefix_name = 'РК'
                group_name = f"{prefix_name}-{course}0{num}"
                group = Group(name=group_name, course=course, specialty_id=spec.id)
                db.session.add(group)
    db.session.commit()
    
    # Предметы по специальностям
    subjects_by_spec = {
        '09.03.01': ['Математический анализ', 'Программирование на C++', 'Архитектура ЭВМ',
                     'Дискретная математика', 'Физика', 'История', 'Английский язык', 'Электротехника'],
        '09.03.04': ['Объектно-ориентированное программирование', 'Базы данных', 'Веб-разработка',
                     'Алгоритмы и структуры данных', 'Java-программирование', 'Технический английский',
                     'Проектирование ПО', 'DevOps практики'],
        '09.03.05': ['Python для Data Science', 'Машинное обучение', 'Глубокое обучение',
                     'Обработка естественного языка', 'Компьютерное зрение', 'Статистика',
                     'Линейная алгебра', 'Big Data'],
        '10.03.01': ['Криптография', 'Сетевые технологии', 'Защита информации',
                     'Анализ уязвимостей', 'Правовые основы ИБ', 'Этический хакинг'],
        '38.03.01': ['Микроэкономика', 'Макроэкономика', 'Статистика', 'Бухгалтерский учет',
                     'Финансовый менеджмент', 'Эконометрика', 'Мировая экономика'],
        '38.03.02': ['Теория менеджмента', 'Маркетинг', 'Управление персоналом',
                     'Стратегический менеджмент', 'Логистика', 'Бизнес-планирование'],
        '40.03.01': ['Гражданское право', 'Уголовное право', 'Конституционное право',
                     'Административное право', 'Трудовое право', 'Судебная система'],
        '42.03.01': ['Теория коммуникаций', 'Медиапланирование', 'Креатив в рекламе',
                     'PR-технологии', 'Копирайтинг', 'SMM', 'Брендинг']
    }
    
    teachers = ['Проф. Иванов А.С.', 'Доц. Петрова М.В.', 'Старший преп. Сидоров К.Л.',
                'Проф. Смирнова Е.А.', 'Доц. Козлов Д.И.', 'Преп. Морозова Т.Н.',
                'Проф. Волков А.П.', 'Доц. Лебедева С.К.', 'Преп. Соловьев М.О.',
                'Проф. Новикова И.В.', 'Доц. Кузнецов Р.С.', 'Преп. Попова А.Д.']
    
    # Создаём локации
    locations_data = [
        {'name': 'Главный корпус', 'address': 'ул. Ленина, 1'},
        {'name': 'Лабораторный корпус', 'address': 'ул. Гагарина, 10'},
        {'name': 'ИТ-корпус', 'address': 'пр. Мира, 5'},
        {'name': 'Учебный корпус №2', 'address': 'ул. Строителей, 7'}
    ]
    locations = {}
    for loc_data in locations_data:
        loc = Location(**loc_data)
        db.session.add(loc)
        locations[loc_data['name']] = loc
    db.session.commit()
    
    # Создаём помещения
    rooms_data = [
        ('101', 'Главный корпус', 40, 'лекционная'),
        ('205', 'Главный корпус', 30, 'лекционная'),
        ('310', 'Главный корпус', 25, 'практическая'),
        ('401', 'Лабораторный корпус', 20, 'лабораторная'),
        ('502', 'Лабораторный корпус', 20, 'лабораторная'),
        ('303', 'ИТ-корпус', 35, 'компьютерный класс'),
        ('201', 'ИТ-корпус', 30, 'лабораторная'),
        ('405', 'ИТ-корпус', 25, 'компьютерный класс'),
        ('115', 'Учебный корпус №2', 50, 'лекционная'),
        ('220', 'Учебный корпус №2', 40, 'лекционная'),
    ]
    rooms = {}
    for name, loc_name, capacity, room_type in rooms_data:
        loc = locations[loc_name]
        room = Room(name=name, location_id=loc.id, capacity=capacity, type=room_type)
        db.session.add(room)
        rooms[f"{loc_name} {name}"] = room
    db.session.commit()
    
    today = datetime.now().date()
    start_week = get_week_start(today)
    lesson_types = ['Лекция', 'Практика', 'Лабораторная']
    now = datetime.now()
    
    for group in Group.query.all():
        spec_code = None
        for code, spec in specs.items():
            if group.specialty_id == spec.id:
                spec_code = code
                break
        subjects = subjects_by_spec.get(spec_code, ['Общий предмет 1', 'Общий предмет 2'])
        
        for week in range(2):
            for day in range(6):
                current_date = start_week + timedelta(weeks=week, days=day)
                num_lessons = random.randint(2, 4)
                daily_slots = random.sample(all_slots, num_lessons)
                daily_slots.sort(key=lambda x: x.start_time)
                
                for slot in daily_slots:
                    subject = random.choice(subjects)
                    lesson_type = random.choice(lesson_types)
                    teacher = random.choice(teachers)
                    room = random.choice(list(rooms.values()))
                    location_str = f"{room.location.name}, ауд. {room.name}"
                    
                    lesson = Lesson(
                        subject_name=subject,
                        lesson_type=lesson_type,
                        lesson_date=current_date,
                        start_time=slot.start_time,
                        end_time=slot.end_time,
                        location=location_str,
                        teacher=teacher,
                        group_id=group.id,
                        room_id=room.id,
                        time_slot_id=slot.id,
                        uploaded_at=now
                    )
                    db.session.add(lesson)
    
    db.session.commit()
    
    log = UploadLog(
        records_count=Lesson.query.count(),
        uploaded_by='system',
        status='success',
        message='Генерация тестовых данных'
    )
    db.session.add(log)
    db.session.commit()
    
    print(f"Создано: {Specialty.query.count()} специальностей, {Group.query.count()} групп, {Lesson.query.count()} занятий")

# ==================== АУТЕНТИФИКАЦИЯ ====================
class AnonymousUser(AnonymousUserMixin):
    def is_admin(self): return False
    def is_manager(self): return False
    def is_teacher(self): return False
    def is_student(self): return False

login_manager.anonymous_user = AnonymousUser

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        group_id = request.form.get('group_id')
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким именем уже существует', 'danger')
        elif User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'danger')
        else:
            user = User(username=username, email=email, role='student')
            user.set_password(password)
            if group_id:
                user.group_id = int(group_id)
            db.session.add(user)
            db.session.commit()
            flash('Регистрация успешна! Теперь вы можете войти', 'success')
            return redirect(url_for('login'))
    groups = Group.query.order_by(Group.name).all()
    return render_template('register.html', groups=groups)

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.is_admin():
        return redirect(url_for('admin_panel'))
    elif current_user.is_manager():
        return redirect(url_for('manager_groups'))
    elif current_user.is_teacher():
        return redirect(url_for('teacher_lessons'))
    else:
        return redirect(url_for('schedule', group_id=current_user.group_id))

# ==================== СТРАНИЦЫ ПО РОЛЯМ ====================
@app.route('/teacher/lessons')
@login_required
def teacher_lessons():
    if not current_user.is_teacher():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    lessons = Lesson.query.filter_by(teacher_id=current_user.id).order_by(Lesson.lesson_date, Lesson.start_time).all()
    return render_template('teacher_lessons.html', lessons=lessons)

@app.route('/teacher/lesson/<int:lesson_id>/confirm', methods=['POST'])
@login_required
def confirm_lesson(lesson_id):
    if not current_user.is_teacher():
        return jsonify({'error': 'Forbidden'}), 403
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != current_user.id:
        return jsonify({'error': 'Not your lesson'}), 403
    lesson.status = 'confirmed'
    db.session.commit()
    return redirect(url_for('teacher_lessons'))

@app.route('/teacher/lesson/<int:lesson_id>/request-reschedule', methods=['GET', 'POST'])
@login_required
def request_reschedule(lesson_id):
    if not current_user.is_teacher():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    lesson = Lesson.query.get_or_404(lesson_id)
    if lesson.teacher_id != current_user.id:
        flash('Это не ваше занятие', 'danger')
        return redirect(url_for('teacher_lessons'))
    if request.method == 'POST':
        suggested_date = datetime.strptime(request.form.get('suggested_date'), '%Y-%m-%d').date()
        suggested_start = datetime.strptime(request.form.get('suggested_start'), '%H:%M').time()
        suggested_end = datetime.strptime(request.form.get('suggested_end'), '%H:%M').time()
        lesson.suggested_date = suggested_date
        lesson.suggested_start_time = suggested_start
        lesson.suggested_end_time = suggested_end
        lesson.status = 'needs_reschedule'
        db.session.commit()
        flash('Запрос на перенос отправлен менеджеру', 'success')
        return redirect(url_for('teacher_lessons'))
    return render_template('teacher_reschedule.html', lesson=lesson)

@app.route('/manager/lesson/<int:lesson_id>/accept-suggest', methods=['POST'])
@login_required
def manager_accept_suggest(lesson_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    lesson = Lesson.query.get_or_404(lesson_id)
    if not lesson.suggested_date:
        flash('Нет предложенной даты', 'danger')
        return redirect(url_for('manager_pending'))
    lesson.lesson_date = lesson.suggested_date
    lesson.start_time = lesson.suggested_start_time
    lesson.end_time = lesson.suggested_end_time
    lesson.status = 'scheduled'
    lesson.suggested_date = None
    lesson.suggested_start_time = None
    lesson.suggested_end_time = None
    lesson.uploaded_at = datetime.now()
    db.session.commit()
    flash('Занятие перенесено согласно предложению преподавателя', 'success')
    return redirect(url_for('manager_pending'))

@app.route('/manager/pending')
@login_required
def manager_pending():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    pending_lessons = Lesson.query.filter_by(status='needs_reschedule').order_by(Lesson.lesson_date).all()
    return render_template('manager_pending.html', lessons=pending_lessons)

@app.route('/manager/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def manager_edit_lesson(lesson_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    lesson = Lesson.query.get_or_404(lesson_id)
    if request.method == 'POST':
        # Получаем данные из формы
        new_group_id = int(request.form.get('group_id'))
        new_lesson_date = datetime.strptime(request.form.get('lesson_date'), '%Y-%m-%d').date()
        new_start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
        new_end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
        new_teacher_id = request.form.get('teacher_id')
        new_room_id = request.form.get('room_id')
        time_slot_id = request.form.get('time_slot_id')

        # Проверка временного слота
        if time_slot_id:
            slot = TimeSlot.query.get(int(time_slot_id))
            if slot:
                if new_start_time != slot.start_time or new_end_time != slot.end_time:
                    flash('Время начала/окончания не соответствует выбранному слоту', 'danger')
                    return redirect(request.url)
                lesson.time_slot_id = slot.id
            else:
                lesson.time_slot_id = None
        else:
            lesson.time_slot_id = None

        # Проверка доступности (исключаем текущее занятие)
        available, error = check_availability(
            new_lesson_date, new_start_time, new_end_time,
            group_id=new_group_id,
            room_id=new_room_id,
            teacher_id=new_teacher_id,
            exclude_lesson_id=lesson.id
        )
        if not available:
            flash(error, 'danger')
            return redirect(url_for('manager_edit_lesson', lesson_id=lesson.id))
        
        # Обновляем занятие
        lesson.subject_name = request.form.get('subject_name')
        lesson.lesson_type = request.form.get('lesson_type')
        lesson.lesson_date = new_lesson_date
        lesson.start_time = new_start_time
        lesson.end_time = new_end_time
        lesson.group_id = new_group_id
        
        if new_teacher_id:
            teacher = User.query.get(int(new_teacher_id))
            lesson.teacher_id = teacher.id
            lesson.teacher = teacher.username
        else:
            lesson.teacher_id = None
            lesson.teacher = None
        
        if new_room_id:
            lesson.room_id = int(new_room_id)
            room = Room.query.get(lesson.room_id)
            lesson.location = f"{room.location.name}, ауд. {room.name}"
        else:
            lesson.room_id = None
            lesson.location = "Не указано"
        
        lesson.status = 'scheduled'
        lesson.uploaded_at = datetime.now()
        db.session.commit()
        flash('Занятие обновлено', 'success')
        return redirect(url_for('manager_schedule', group_id=lesson.group_id))
    
    # GET: передаём в шаблон
    teachers = get_teachers_for_group(lesson.group_id)
    groups = Group.query.order_by(Group.name).all()
    locations = Location.query.all()
    rooms = Room.query.all()
    time_slots = TimeSlot.query.order_by(TimeSlot.order).all()
    return render_template('manager_edit_lesson.html', 
                           lesson=lesson, 
                           teachers=teachers,
                           groups=groups,
                           locations=locations,
                           rooms=rooms,
                           time_slots=time_slots)

# ==================== УПРАВЛЕНИЕ ЛОКАЦИЯМИ И ПОМЕЩЕНИЯМИ ====================
@app.route('/manager/locations')
@login_required
def manager_locations():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    locations = Location.query.order_by(Location.name).all()
    return render_template('manager_locations.html', locations=locations)

@app.route('/manager/location/create', methods=['GET', 'POST'])
@login_required
def manager_location_create():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        location = Location(name=name, address=address)
        db.session.add(location)
        db.session.commit()
        flash('Локация создана', 'success')
        return redirect(url_for('manager_locations'))
    return render_template('manager_location_form.html', location=None)

@app.route('/manager/location/<int:location_id>/edit', methods=['GET', 'POST'])
@login_required
def manager_location_edit(location_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    location = Location.query.get_or_404(location_id)
    if request.method == 'POST':
        location.name = request.form.get('name')
        location.address = request.form.get('address')
        db.session.commit()
        flash('Локация обновлена', 'success')
        return redirect(url_for('manager_locations'))
    return render_template('manager_location_form.html', location=location)

@app.route('/manager/location/<int:location_id>/delete', methods=['POST'])
@login_required
def manager_location_delete(location_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    location = Location.query.get_or_404(location_id)
    db.session.delete(location)
    db.session.commit()
    flash('Локация и все её помещения удалены', 'success')
    return redirect(url_for('manager_locations'))

@app.route('/manager/rooms')
@login_required
def manager_rooms():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    location_id = request.args.get('location_id')
    if location_id:
        rooms = Room.query.filter_by(location_id=location_id).order_by(Room.name).all()
        location = Location.query.get(location_id)
    else:
        rooms = Room.query.order_by(Room.name).all()
        location = None
    locations = Location.query.order_by(Location.name).all()
    return render_template('manager_rooms.html', rooms=rooms, location=location, locations=locations)

@app.route('/manager/room/create', methods=['GET', 'POST'])
@login_required
def manager_room_create():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name')
        capacity = request.form.get('capacity')
        room_type = request.form.get('type')
        location_id = request.form.get('location_id')
        room = Room(name=name, capacity=capacity, type=room_type, location_id=location_id)
        db.session.add(room)
        db.session.commit()
        flash('Помещение создано', 'success')
        return redirect(url_for('manager_rooms'))
    locations = Location.query.order_by(Location.name).all()
    return render_template('manager_room_form.html', room=None, locations=locations)

@app.route('/manager/room/<int:room_id>/edit', methods=['GET', 'POST'])
@login_required
def manager_room_edit(room_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        room.name = request.form.get('name')
        room.capacity = request.form.get('capacity')
        room.type = request.form.get('type')
        room.location_id = request.form.get('location_id')
        db.session.commit()
        flash('Помещение обновлено', 'success')
        return redirect(url_for('manager_rooms'))
    locations = Location.query.order_by(Location.name).all()
    return render_template('manager_room_form.html', room=room, locations=locations)

@app.route('/manager/room/<int:room_id>/delete', methods=['POST'])
@login_required
def manager_room_delete(room_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    flash('Помещение удалено', 'success')
    return redirect(url_for('manager_rooms'))

# ==================== АДМИН-ПАНЕЛЬ ====================
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    users = User.query.all()
    groups = Group.query.all()
    specialties = Specialty.query.all()
    return render_template('admin.html', users=users, groups=groups, specialties=specialties)

@app.route('/admin/user/create', methods=['POST'])
@login_required
def admin_create_user():
    if not current_user.is_admin():
        return jsonify({'error': 'Forbidden'}), 403
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    role = request.form.get('role')
    group_id = request.form.get('group_id')
    specialty_ids = request.form.getlist('specialty_ids')
    user = User(username=username, email=email, role=role)
    user.set_password(password)
    if role == 'student' and group_id:
        user.group_id = int(group_id)
    elif role == 'teacher' and specialty_ids:
        specs = Specialty.query.filter(Specialty.id.in_(specialty_ids)).all()
        user.specialties = specs
    db.session.add(user)
    db.session.commit()
    flash('Пользователь создан', 'success')
    return redirect(url_for('admin_panel'))

# ==================== WEB-МАРШРУТЫ ====================
@app.route('/')
def index():
    specialties = Specialty.query.order_by(Specialty.code).all()
    last_update = get_last_update_time()
    return render_template('index.html', specialties=specialties, last_update=last_update)

@app.route('/get_groups/<int:specialty_id>')
def get_groups(specialty_id):
    groups = Group.query.filter_by(specialty_id=specialty_id).order_by(Group.course, Group.name).all()
    return jsonify([{
        'id': g.id,
        'name': g.name,
        'course': g.course,
        'full_name': f"{g.name} ({g.course} курс)"
    } for g in groups])

@app.route('/schedule', methods=['GET', 'POST'])
@login_required
def schedule():
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        if group_id:
            session['group_id'] = int(group_id)
            return redirect(url_for('schedule'))
    if current_user.is_student():
        group_id = current_user.group_id
    else:
        group_id = request.args.get('group_id') or session.get('group_id')
    if not group_id:
        flash('Пожалуйста, выберите группу', 'warning')
        return redirect(url_for('index'))
    group = Group.query.get_or_404(group_id)
    specialty = Specialty.query.get(group.specialty_id)
    dates = get_two_weeks_dates()
    start_date = dates[0]
    end_date = dates[-1]
    lessons = Lesson.query.filter(
        Lesson.group_id == group_id,
        Lesson.lesson_date >= start_date,
        Lesson.lesson_date <= end_date
    ).order_by(Lesson.lesson_date, Lesson.start_time).all()
    last_update = db.session.query(db.func.max(Lesson.uploaded_at)).filter(
        Lesson.group_id == group_id
    ).scalar()
    schedule_by_day = {}
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        day_lessons = [l for l in lessons if l.lesson_date == date]
        schedule_by_day[date_str] = {
            'date': date,
            'day_name': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][date.weekday()],
            'full_day_name': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][date.weekday()],
            'lessons': day_lessons,
            'is_today': date == datetime.now().date()
        }
    week1 = dates[:7]
    week2 = dates[7:]
    return render_template('schedule.html',
                           group=group,
                           specialty=specialty,
                           schedule=schedule_by_day,
                           week1=week1,
                           week2=week2,
                           start_date=start_date,
                           end_date=end_date,
                           today=datetime.now().date(),
                           last_update=last_update)

# ==================== API-МАРШРУТЫ ====================
@app.route('/api/schedule/<int:group_id>')
@login_required
def api_schedule(group_id):
    if current_user.is_student() and current_user.group_id != group_id:
        return jsonify({'error': 'Access denied'}), 403
    dates = get_two_weeks_dates()
    lessons = Lesson.query.filter(
        Lesson.group_id == group_id,
        Lesson.lesson_date >= dates[0],
        Lesson.lesson_date <= dates[-1]
    ).order_by(Lesson.lesson_date, Lesson.start_time).all()
    group = Group.query.get(group_id)
    return jsonify({
        'group_id': group_id,
        'group_name': group.name if group else None,
        'period': {
            'start': dates[0].strftime('%Y-%m-%d'),
            'end': dates[-1].strftime('%Y-%m-%d')
        },
        'last_update': get_last_update_time().strftime('%Y-%m-%d %H:%M:%S') if get_last_update_time() else None,
        'lessons_count': len(lessons),
        'lessons': [l.to_dict() for l in lessons]
    })

@app.route('/api/check-availability', methods=['POST'])
def api_check_availability():
    data = request.get_json()
    lesson_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
    start_time = datetime.strptime(data['start'], '%H:%M').time()
    end_time = datetime.strptime(data['end'], '%H:%M').time()
    group_id = data.get('group_id')
    room_id = data.get('room_id')
    teacher_id = data.get('teacher_id')
    lesson_id = data.get('lesson_id')
    
    available, error_msg = check_availability(
        lesson_date, start_time, end_time,
        group_id=group_id,
        room_id=room_id,
        teacher_id=teacher_id,
        exclude_lesson_id=lesson_id
    )
    return jsonify({'available': available, 'message': error_msg})

@app.route('/api/lessons/upload', methods=['POST'])
def api_upload_lessons():
    try:
        data = request.get_json()
        if not data or not isinstance(data, list):
            return jsonify({'success': False, 'error': 'Ожидается массив занятий'}), 400
        uploaded_count = 0
        errors = []
        now = datetime.now()
        for idx, item in enumerate(data):
            try:
                required = ['subject_name', 'lesson_type', 'lesson_date', 'start_time', 'end_time', 'location', 'group_id']
                missing = [f for f in required if f not in item]
                if missing:
                    errors.append(f'Запись {idx}: отсутствуют поля {missing}')
                    continue
                group = Group.query.get(item['group_id'])
                if not group:
                    errors.append(f'Запись {idx}: группа {item["group_id"]} не найдена')
                    continue
                lesson_date = datetime.strptime(item['lesson_date'], '%Y-%m-%d').date()
                start_time = datetime.strptime(item['start_time'], '%H:%M').time()
                end_time = datetime.strptime(item['end_time'], '%H:%M').time()
                lesson = Lesson(
                    subject_name=item['subject_name'],
                    lesson_type=item['lesson_type'],
                    lesson_date=lesson_date,
                    start_time=start_time,
                    end_time=end_time,
                    location=item['location'],
                    teacher=item.get('teacher', ''),
                    group_id=item['group_id'],
                    uploaded_at=now
                )
                db.session.add(lesson)
                uploaded_count += 1
            except Exception as e:
                errors.append(f'Запись {idx}: {str(e)}')
        db.session.commit()
        log = UploadLog(
            records_count=uploaded_count,
            uploaded_by=request.headers.get('X-User', 'api'),
            status='partial' if errors else 'success',
            message=f'Загружено: {uploaded_count}, ошибок: {len(errors)}'
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({
            'success': True,
            'uploaded': uploaded_count,
            'errors_count': len(errors),
            'errors': errors[:10],
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/lessons/bulk-update', methods=['POST'])
def api_bulk_update():
    try:
        data = request.get_json()
        group_id = data.get('group_id')
        lessons_data = data.get('lessons', [])
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        if not group_id or not lessons_data:
            return jsonify({'success': False, 'error': 'Требуются group_id и lessons'}), 400
        group = Group.query.get(group_id)
        if not group:
            return jsonify({'success': False, 'error': f'Группа {group_id} не найдена'}), 404
        now = datetime.now()
        deleted_count = 0
        if period_start and period_end:
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
            deleted_count = Lesson.query.filter(
                Lesson.group_id == group_id,
                Lesson.lesson_date >= start_date,
                Lesson.lesson_date <= end_date
            ).delete(synchronize_session=False)
        uploaded_count = 0
        for item in lessons_data:
            lesson_date = datetime.strptime(item['lesson_date'], '%Y-%m-%d').date()
            start_time = datetime.strptime(item['start_time'], '%H:%M').time()
            end_time = datetime.strptime(item['end_time'], '%H:%M').time()
            lesson = Lesson(
                subject_name=item['subject_name'],
                lesson_type=item['lesson_type'],
                lesson_date=lesson_date,
                start_time=start_time,
                end_time=end_time,
                location=item['location'],
                teacher=item.get('teacher', ''),
                group_id=group_id,
                uploaded_at=now
            )
            db.session.add(lesson)
            uploaded_count += 1
        db.session.commit()
        log = UploadLog(
            records_count=uploaded_count,
            uploaded_by=request.headers.get('X-User', 'api'),
            status='success',
            message=f'Обновление группы {group.name}: удалено {deleted_count}, добавлено {uploaded_count}'
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({
            'success': True,
            'group_id': group_id,
            'group_name': group.name,
            'deleted_old': deleted_count,
            'uploaded_new': uploaded_count,
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/lessons/<int:lesson_id>', methods=['PUT', 'DELETE'])
def api_lesson_item(lesson_id):
    lesson = Lesson.query.get_or_404(lesson_id)
    if request.method == 'DELETE':
        db.session.delete(lesson)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Занятие {lesson_id} удалено',
            'deleted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    try:
        data = request.get_json()
        if 'subject_name' in data:
            lesson.subject_name = data['subject_name']
        if 'lesson_type' in data:
            lesson.lesson_type = data['lesson_type']
        if 'lesson_date' in data:
            lesson.lesson_date = datetime.strptime(data['lesson_date'], '%Y-%m-%d').date()
        if 'start_time' in data:
            lesson.start_time = datetime.strptime(data['start_time'], '%H:%M').time()
        if 'end_time' in data:
            lesson.end_time = datetime.strptime(data['end_time'], '%H:%M').time()
        if 'location' in data:
            lesson.location = data['location']
        if 'teacher' in data:
            lesson.teacher = data['teacher']
        lesson.uploaded_at = datetime.now()
        db.session.commit()
        return jsonify({'success': True, 'lesson': lesson.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/upload-history')
def api_upload_history():
    logs = UploadLog.query.order_by(UploadLog.uploaded_at.desc()).limit(50).all()
    return jsonify([{
        'id': log.id,
        'filename': log.filename,
        'records_count': log.records_count,
        'uploaded_at': log.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
        'uploaded_by': log.uploaded_by,
        'status': log.status,
        'message': log.message
    } for log in logs])

@app.route('/api/stats')
def api_stats():
    from sqlalchemy import func
    total_lessons = Lesson.query.count()
    total_groups = Group.query.count()
    total_specialties = Specialty.query.count()
    last_update = db.session.query(func.max(Lesson.uploaded_at)).scalar()
    type_stats = db.session.query(
        Lesson.lesson_type,
        func.count(Lesson.id)
    ).group_by(Lesson.lesson_type).all()
    return jsonify({
        'total_lessons': total_lessons,
        'total_groups': total_groups,
        'total_specialties': total_specialties,
        'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else None,
        'lesson_types': {t: c for t, c in type_stats}
    })

# ==================== CLI-КОМАНДЫ ====================
@app.cli.command('init-db')
def init_db_command():
    with app.app_context():
        db.create_all()
        print("Таблицы созданы")
        if not Specialty.query.first():
            generate_test_data()
            print("Тестовые данные созданы")
        else:
            print("База уже содержит данные")

@app.cli.command('reset-db')
def reset_db_command():
    with app.app_context():
        db.drop_all()
        db.create_all()
        generate_test_data()
        print("База пересоздана")

@app.cli.command('create-admin')
def create_admin():
    username = input('Username: ')
    email = input('Email: ')
    password = input('Password: ')
    admin = User(username=username, email=email, role='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f'Admin {username} created.')

# ==================== МЕНЕДЖЕР: УПРАВЛЕНИЕ РАСПИСАНИЕМ ====================
@app.route('/manager/groups')
@login_required
def manager_groups():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    specialties = Specialty.query.order_by(Specialty.code).all()
    return render_template('manager_groups.html', specialties=specialties)

# ==================== УПРАВЛЕНИЕ ВРЕМЕННЫМИ СЛОТАМИ ====================
@app.route('/manager/time-slots')
@login_required
def manager_time_slots():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    slots = TimeSlot.query.order_by(TimeSlot.order).all()
    return render_template('manager_time_slots.html', slots=slots)

@app.route('/manager/time-slot/create', methods=['GET', 'POST'])
@login_required
def manager_time_slot_create():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        name = request.form.get('name')
        start = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
        end = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
        order = int(request.form.get('order'))
        slot = TimeSlot(name=name, start_time=start, end_time=end, order=order)
        db.session.add(slot)
        db.session.commit()
        flash('Временной слот создан', 'success')
        return redirect(url_for('manager_time_slots'))
    return render_template('manager_time_slot_form.html', slot=None)

@app.route('/manager/time-slot/<int:slot_id>/edit', methods=['GET', 'POST'])
@login_required
def manager_time_slot_edit(slot_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    slot = TimeSlot.query.get_or_404(slot_id)
    if request.method == 'POST':
        slot.name = request.form.get('name')
        slot.start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
        slot.end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
        slot.order = int(request.form.get('order'))
        db.session.commit()
        flash('Временной слот обновлён', 'success')
        return redirect(url_for('manager_time_slots'))
    return render_template('manager_time_slot_form.html', slot=slot)

@app.route('/manager/time-slot/<int:slot_id>/delete', methods=['POST'])
@login_required
def manager_time_slot_delete(slot_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    slot = TimeSlot.query.get_or_404(slot_id)
    db.session.delete(slot)
    db.session.commit()
    flash('Временной слот удалён', 'success')
    return redirect(url_for('manager_time_slots'))

# ==================== ДАШБОРД РАСПИСАНИЯ ПО ПОМЕЩЕНИЯМ ====================
@app.route('/manager/rooms-schedule')
@login_required
def manager_rooms_schedule():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    location_id = request.args.get('location_id', type=int)
    if location_id:
        rooms = Room.query.filter_by(location_id=location_id).order_by(Room.name).all()
        selected_location = Location.query.get(location_id)
    else:
        rooms = Room.query.order_by(Room.name).all()
        selected_location = None
    locations = Location.query.order_by(Location.name).all()
    return render_template('manager_rooms_schedule.html',
                           rooms=rooms,
                           locations=locations,
                           selected_location=selected_location)

@app.route('/api/room-schedule/<int:room_id>')
@login_required
def api_room_schedule(room_id):
    dates = get_two_weeks_dates()
    slots = TimeSlot.query.order_by(TimeSlot.order).all()
    lessons = Lesson.query.filter(
        Lesson.room_id == room_id,
        Lesson.lesson_date >= dates[0],
        Lesson.lesson_date <= dates[-1]
    ).all()

    schedule = {}
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        schedule[date_str] = {slot.id: None for slot in slots}
        for lesson in lessons:
            if lesson.lesson_date == date:
                # Используем явный time_slot_id
                slot_id = lesson.time_slot_id
                if not slot_id:
                    # fallback: поиск по времени
                    for slot in slots:
                        if lesson.start_time >= slot.start_time and lesson.end_time <= slot.end_time:
                            slot_id = slot.id
                            break
                if slot_id:
                    schedule[date_str][slot_id] = lesson.id

    return jsonify({
        'dates': [d.strftime('%Y-%m-%d') for d in dates],
        'slots': [{'id': s.id, 'name': s.name, 'start': s.start_time.strftime('%H:%M'), 'end': s.end_time.strftime('%H:%M')} for s in slots],
        'schedule': schedule,
        'lessons_details': {l.id: l.to_dict() for l in lessons}
    })

# ==================== МЕНЕДЖЕР: РАСПИСАНИЕ ГРУППЫ ====================
@app.route('/manager/schedule/<int:group_id>')
@login_required
def manager_schedule(group_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    group = Group.query.get_or_404(group_id)
    dates = get_two_weeks_dates()
    start_date = dates[0]
    end_date = dates[-1]
    lessons = Lesson.query.filter(
        Lesson.group_id == group_id,
        Lesson.lesson_date >= start_date,
        Lesson.lesson_date <= end_date
    ).order_by(Lesson.lesson_date, Lesson.start_time).all()
    schedule_by_day = {}
    for date in dates:
        date_str = date.strftime('%Y-%m-%d')
        day_lessons = [l for l in lessons if l.lesson_date == date]
        schedule_by_day[date_str] = {
            'date': date,
            'day_name': ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][date.weekday()],
            'full_day_name': ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'][date.weekday()],
            'lessons': day_lessons,
            'is_today': date == datetime.now().date()
        }
    week1 = dates[:7]
    week2 = dates[7:]
    teachers = get_teachers_for_group(group_id)
    return render_template('manager_schedule.html',
                           group=group,
                           schedule=schedule_by_day,
                           week1=week1,
                           week2=week2,
                           start_date=start_date,
                           end_date=end_date,
                           today=datetime.now().date(),
                           teachers=teachers)

@app.route('/manager/lesson/create', methods=['GET', 'POST'])
@login_required
def manager_create_lesson():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        subject_name = request.form.get('subject_name')
        lesson_type = request.form.get('lesson_type')
        lesson_date = datetime.strptime(request.form.get('lesson_date'), '%Y-%m-%d').date()
        start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
        end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
        teacher_id = request.form.get('teacher_id')
        room_id = request.form.get('room_id')
        time_slot_id = request.form.get('time_slot_id')
        
        # Проверка доступности
        available, error = check_availability(
            lesson_date, start_time, end_time,
            group_id=group_id, room_id=room_id, teacher_id=teacher_id
        )
        if not available:
            flash(error, 'danger')
            return redirect(url_for('manager_create_lesson', group_id=group_id))
        
        group = Group.query.get_or_404(group_id)
        lesson = Lesson(
            subject_name=subject_name,
            lesson_type=lesson_type,
            lesson_date=lesson_date,
            start_time=start_time,
            end_time=end_time,
            group_id=group.id,
            uploaded_at=datetime.now(),
            status='scheduled'
        )
        if teacher_id:
            teacher = User.query.get(int(teacher_id))
            lesson.teacher_id = teacher.id
            lesson.teacher = teacher.username
        if room_id:
            lesson.room_id = int(room_id)
            room = Room.query.get(lesson.room_id)
            lesson.location = f"{room.location.name}, ауд. {room.name}"
        else:
            lesson.room_id = None
            lesson.location = "Не указано"
        if time_slot_id:
            lesson.time_slot_id = int(time_slot_id)
        else:
            lesson.time_slot_id = None
        
        db.session.add(lesson)
        db.session.commit()
        flash('Занятие создано', 'success')
        return redirect(url_for('manager_schedule', group_id=group_id))
    
    # GET: показать форму
    group_id = request.args.get('group_id')
    group = Group.query.get_or_404(group_id) if group_id else None
    teachers = get_teachers_for_group(group_id) if group_id else User.query.filter_by(role='teacher').all()
    locations = Location.query.all()
    rooms = Room.query.all()
    time_slots = TimeSlot.query.order_by(TimeSlot.order).all()
    return render_template('manager_lesson_form.html',
                           lesson=None,
                           group=group,
                           teachers=teachers,
                           locations=locations,
                           rooms=rooms,
                           time_slots=time_slots)

@app.route('/manager/lesson/<int:lesson_id>/delete', methods=['POST'])
@login_required
def manager_delete_lesson(lesson_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    lesson = Lesson.query.get_or_404(lesson_id)
    group_id = lesson.group_id
    db.session.delete(lesson)
    db.session.commit()
    flash('Занятие удалено', 'success')
    return redirect(url_for('manager_schedule', group_id=group_id))

# ==================== УПРАВЛЕНИЕ ПРЕПОДАВАТЕЛЯМИ ====================
@app.route('/manager/teachers')
@login_required
def manager_teachers():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    teachers = User.query.filter_by(role='teacher').order_by(User.username).all()
    return render_template('manager_teachers.html', teachers=teachers)

@app.route('/manager/teacher/<int:user_id>/specialties', methods=['GET', 'POST'])
@login_required
def manager_teacher_specialties(user_id):
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    teacher = User.query.get_or_404(user_id)
    if teacher.role != 'teacher':
        flash('Этот пользователь не преподаватель', 'danger')
        return redirect(url_for('manager_teachers'))
    if request.method == 'POST':
        specialty_ids = request.form.getlist('specialty_ids')
        teacher.specialties = Specialty.query.filter(Specialty.id.in_(specialty_ids)).all()
        db.session.commit()
        flash(f'Специальности преподавателя {teacher.username} обновлены', 'success')
        return redirect(url_for('manager_teachers'))
    specialties = Specialty.query.order_by(Specialty.code).all()
    selected_ids = [s.id for s in teacher.specialties]
    return render_template('teacher_specialties.html',
                           teacher=teacher,
                           specialties=specialties,
                           selected_ids=selected_ids,
                           return_url=url_for('manager_teachers'))

@app.route('/admin/teacher/<int:user_id>/specialties', methods=['GET', 'POST'])
@login_required
def admin_teacher_specialties(user_id):
    if not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    teacher = User.query.get_or_404(user_id)
    if teacher.role != 'teacher':
        flash('Этот пользователь не преподаватель', 'danger')
        return redirect(url_for('admin_panel'))
    if request.method == 'POST':
        specialty_ids = request.form.getlist('specialty_ids')
        teacher.specialties = Specialty.query.filter(Specialty.id.in_(specialty_ids)).all()
        db.session.commit()
        flash(f'Специальности преподавателя {teacher.username} обновлены', 'success')
        return redirect(url_for('admin_panel'))
    specialties = Specialty.query.order_by(Specialty.code).all()
    selected_ids = [s.id for s in teacher.specialties]
    return render_template('teacher_specialties.html',
                           teacher=teacher,
                           specialties=specialties,
                           selected_ids=selected_ids,
                           return_url=url_for('admin_panel'))

# ==================== УПРАВЛЕНИЕ ГРУППАМИ ====================
@app.route('/manager/groups-list')
@login_required
def manager_groups_list():
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    specialty_id = request.args.get('specialty_id', type=int)
    query = Group.query
    if specialty_id:
        query = query.filter_by(specialty_id=specialty_id)
    groups = query.order_by(Group.name).all()
    all_specialties = Specialty.query.order_by(Specialty.code).all()
    return render_template('manager_groups_list.html',
                           groups=groups,
                           all_specialties=all_specialties,
                           selected_specialty_id=specialty_id)
        
@app.route('/manager/group/<int:group_id>/edit', methods=['GET', 'POST'])
@login_required
def manager_group_edit(group_id):
    """Редактирование группы (название, курс, специальность, количество студентов)"""
    if not current_user.is_manager() and not current_user.is_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('index'))
    group = Group.query.get_or_404(group_id)
    if request.method == 'POST':
        group.name = request.form.get('name')
        group.course = int(request.form.get('course'))
        group.specialty_id = int(request.form.get('specialty_id'))
        group.student_count = int(request.form.get('student_count', 0))
        db.session.commit()
        flash('Данные группы обновлены', 'success')
        return redirect(url_for('manager_groups_list'))
    specialties = Specialty.query.order_by(Specialty.code).all()
    return render_template('manager_group_edit.html', group=group, specialties=specialties)    

# ==================== ПРОВЕРКА КОНФЛИКТОВ РАСПИСАНИЯ ====================
def check_group_availability(group_id, lesson_date, start_time, end_time, exclude_lesson_id=None):
    """Проверяет, свободна ли группа в указанное время"""
    query = Lesson.query.filter(
        Lesson.group_id == group_id,
        Lesson.lesson_date == lesson_date,
        Lesson.start_time < end_time,
        Lesson.end_time > start_time
    )
    if exclude_lesson_id:
        query = query.filter(Lesson.id != exclude_lesson_id)
    return query.first() is None

def check_room_availability(room_id, lesson_date, start_time, end_time, exclude_lesson_id=None):
    """Проверяет, свободно ли помещение в указанное время"""
    if not room_id:
        return True
    query = Lesson.query.filter(
        Lesson.room_id == room_id,
        Lesson.lesson_date == lesson_date,
        Lesson.start_time < end_time,
        Lesson.end_time > start_time
    )
    if exclude_lesson_id:
        query = query.filter(Lesson.id != exclude_lesson_id)
    return query.first() is None

def check_teacher_availability(teacher_id, lesson_date, start_time, end_time, exclude_lesson_id=None):
    """Проверяет, свободен ли преподаватель в указанное время"""
    if not teacher_id:
        return True
    query = Lesson.query.filter(
        Lesson.teacher_id == teacher_id,
        Lesson.lesson_date == lesson_date,
        Lesson.start_time < end_time,
        Lesson.end_time > start_time
    )
    if exclude_lesson_id:
        query = query.filter(Lesson.id != exclude_lesson_id)
    return query.first() is None

def check_availability(lesson_date, start_time, end_time, group_id=None, room_id=None, teacher_id=None, exclude_lesson_id=None):
    """Проверяет доступность группы, помещения и преподавателя"""
    messages = []
    if group_id:
        if not check_group_availability(group_id, lesson_date, start_time, end_time, exclude_lesson_id):
            messages.append("Группа уже занята в это время")
    if room_id:
        if not check_room_availability(room_id, lesson_date, start_time, end_time, exclude_lesson_id):
            messages.append("Помещение уже занято")
    if teacher_id:
        if not check_teacher_availability(teacher_id, lesson_date, start_time, end_time, exclude_lesson_id):
            messages.append("Преподаватель уже занят")
    if messages:
        return False, "; ".join(messages)
    return True, None

# ==================== ЗАПУСК ПРИЛОЖЕНИЯ ====================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Specialty.query.first():
            generate_test_data()
    app.run(debug=True, host='0.0.0.0', port=5000)