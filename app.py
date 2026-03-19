from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime, timedelta, time
from config import Config
from models import db, Specialty, Group, Lesson, UploadLog
import random
import os

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


def get_week_start(date=None):
    """Получить понедельник текущей недели"""
    if date is None:
        date = datetime.now().date()
    return date - timedelta(days=date.weekday())


def get_two_weeks_dates(start_date=None):
    """Получить список дат на 2 недели"""
    if start_date is None:
        start_date = get_week_start()
    
    dates = []
    for week in range(2):
        for day in range(7):
            current = start_date + timedelta(weeks=week, days=day)
            dates.append(current)
    return dates


def get_last_update_time():
    """Получить время последнего обновления расписания"""
    last_lesson = Lesson.query.order_by(Lesson.uploaded_at.desc()).first()
    if last_lesson:
        return last_lesson.uploaded_at
    return None


def generate_test_data():
    """Генерация тестовых данных"""
    print("Генерация тестовых данных...")
    
    # Очистка старых данных
    db.session.query(Lesson).delete()
    db.session.query(Group).delete()
    db.session.query(Specialty).delete()
    db.session.query(UploadLog).delete()
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
    
    # Группы
    groups_data = []
    group_id_counter = 1
    
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
                groups_data.append(group)
                group_id_counter += 1
    
    db.session.commit()
    
    # Предметы
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
    
    locations = ['Главный корпус, ауд. 101', 'Главный корпус, ауд. 205', 'Главный корпус, ауд. 310',
                 'Лабораторный корпус, каб. 401', 'Лабораторный корпус, каб. 502',
                 'ИТ-корпус, ауд. 303', 'ИТ-корпус, лаб. 201', 'ИТ-корпус, лаб. 405',
                 'Учебный корпус №2, ауд. 115', 'Учебный корпус №2, ауд. 220',
                 'Онлайн (Zoom)', 'Онлайн (Teams)']
    
    time_slots = [('08:30', '10:05'), ('10:20', '11:55'), ('12:10', '13:45'),
                   ('14:15', '15:50'), ('16:05', '17:40'), ('17:50', '19:25')]
    
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
                daily_slots = random.sample(time_slots, num_lessons)
                daily_slots.sort(key=lambda x: x[0])
                
                for start_str, end_str in daily_slots:
                    subject = random.choice(subjects)
                    lesson_type = random.choice(lesson_types)
                    
                    location = random.choice(locations) if lesson_type != 'Лекция' else \
                        random.choice([l for l in locations if 'ауд' in l])
                    
                    teacher = random.choice(teachers)
                    
                    start_t = datetime.strptime(start_str, '%H:%M').time()
                    end_t = datetime.strptime(end_str, '%H:%M').time()
                    
                    lesson = Lesson(
                        subject_name=subject,
                        lesson_type=lesson_type,
                        lesson_date=current_date,
                        start_time=start_t,
                        end_time=end_t,
                        location=location,
                        teacher=teacher,
                        group_id=group.id,
                        uploaded_at=now
                    )
                    db.session.add(lesson)
    
    db.session.commit()
    
    # Лог
    log = UploadLog(
        records_count=Lesson.query.count(),
        uploaded_by='system',
        status='success',
        message='Генерация тестовых данных'
    )
    db.session.add(log)
    db.session.commit()
    
    print(f"Создано: {Specialty.query.count()} специальностей, {Group.query.count()} групп, {Lesson.query.count()} занятий")


# ==================== WEB ROUTES ====================

@app.route('/')
def index():
    """Главная страница"""
    specialties = Specialty.query.order_by(Specialty.code).all()
    last_update = get_last_update_time()
    
    return render_template('index.html', 
                         specialties=specialties,
                         last_update=last_update)


@app.route('/get_groups/<int:specialty_id>')
def get_groups(specialty_id):
    """API: получить группы по специальности"""
    groups = Group.query.filter_by(specialty_id=specialty_id).order_by(Group.course, Group.name).all()
    return jsonify([{
        'id': g.id,
        'name': g.name,
        'course': g.course,
        'full_name': f"{g.name} ({g.course} курс)"
    } for g in groups])


@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    """Страница расписания"""
    if request.method == 'POST':
        group_id = request.form.get('group_id')
        if group_id:
            session['group_id'] = int(group_id)
            return redirect(url_for('schedule'))
    
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


# ==================== API ROUTES ====================

@app.route('/api/schedule/<int:group_id>')
def api_schedule(group_id):
    """API: расписание группы в JSON"""
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
            'end': dates[-1].strftime('%Y-%m-%m-%d')
        },
        'last_update': get_last_update_time().strftime('%Y-%m-%d %H:%M:%S') if get_last_update_time() else None,
        'lessons_count': len(lessons),
        'lessons': [l.to_dict() for l in lessons]
    })


@app.route('/api/lessons/upload', methods=['POST'])
def api_upload_lessons():
    """
    API: загрузка занятий (JSON)
    Пример:
    [
        {
            "subject_name": "Математика",
            "lesson_type": "Лекция",
            "lesson_date": "2026-03-20",
            "start_time": "09:00",
            "end_time": "10:30",
            "location": "Ауд. 101",
            "teacher": "Проф. Иванов",
            "group_id": 1
        }
    ]
    """
    try:
        data = request.get_json()
        
        if not data or not isinstance(data, list):
            return jsonify({
                'success': False,
                'error': 'Ожидается массив занятий'
            }), 400
        
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/lessons/bulk-update', methods=['POST'])
def api_bulk_update():
    """API: массовое обновление расписания группы"""
    try:
        data = request.get_json()
        
        group_id = data.get('group_id')
        lessons_data = data.get('lessons', [])
        period_start = data.get('period_start')
        period_end = data.get('period_end')
        
        if not group_id or not lessons_data:
            return jsonify({
                'success': False,
                'error': 'Требуются group_id и lessons'
            }), 400
        
        group = Group.query.get(group_id)
        if not group:
            return jsonify({
                'success': False,
                'error': f'Группа {group_id} не найдена'
            }), 404
        
        now = datetime.now()
        
        # Удаляем старые если указан период
        deleted_count = 0
        if period_start and period_end:
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
            
            deleted_count = Lesson.query.filter(
                Lesson.group_id == group_id,
                Lesson.lesson_date >= start_date,
                Lesson.lesson_date <= end_date
            ).delete(synchronize_session=False)
        
        # Добавляем новые
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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/lessons/<int:lesson_id>', methods=['PUT', 'DELETE'])
def api_lesson_item(lesson_id):
    """API: обновление или удаление одного занятия"""
    lesson = Lesson.query.get_or_404(lesson_id)
    
    if request.method == 'DELETE':
        db.session.delete(lesson)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Занятие {lesson_id} удалено',
            'deleted_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # PUT - обновление
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
        
        return jsonify({
            'success': True,
            'lesson': lesson.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/upload-history')
def api_upload_history():
    """API: история загрузок"""
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
    """API: статистика системы"""
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


# ==================== CLI COMMANDS ====================

@app.cli.command('init-db')
def init_db_command():
    """Команда: flask init-db"""
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
    """Команда: flask reset-db"""
    with app.app_context():
        db.drop_all()
        db.create_all()
        generate_test_data()
        print("База пересоздана")


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Specialty.query.first():
            generate_test_data()
    
    app.run(debug=True, host='0.0.0.0', port=5000)