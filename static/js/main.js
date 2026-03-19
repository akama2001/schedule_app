document.addEventListener('DOMContentLoaded', function() {
    
    // Цвета фона для типов занятий
    const typeColors = {
        'Лекция': '#f0fdf4',      // зелёный
        'Практика': '#eff6ff',    // голубой
        'Лабораторная': '#fffbeb' // жёлтый
    };
    
    // Применяем цвета фона к day-content
    function applyDayContentColors() {
        document.querySelectorAll('.day-content').forEach(dayContent => {
            const lessonsCount = parseInt(dayContent.dataset.lessonsCount) || 0;
            
            if (lessonsCount === 0) {
                dayContent.style.background = '#ffffff';
                return;
            }
            
            const firstLesson = dayContent.querySelector('.lesson-card');
            if (!firstLesson) {
                dayContent.style.background = '#ffffff';
                return;
            }
            
            const lessonType = firstLesson.dataset.lessonType;
            const bgColor = typeColors[lessonType] || '#ffffff';
            
            dayContent.style.background = bgColor;
            dayContent.style.transition = 'background-color 0.3s ease';
        });
    }
    
    // Логика вкладок
    function initTabs() {
        const tabs = document.querySelectorAll('.week-tab');
        const panels = document.querySelectorAll('.week-panel');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const targetTab = this.dataset.tab;
                
                // Убираем активность со всех вкладок
                tabs.forEach(t => t.classList.remove('active'));
                panels.forEach(p => p.classList.remove('active'));
                
                // Активируем выбранную
                this.classList.add('active');
                document.getElementById(targetTab).classList.add('active');
                
                // Переприменяем цвета для новой активной панели
                setTimeout(applyDayContentColors, 50);
            });
        });
    }
    
    // Запускаем
    applyDayContentColors();
    initTabs();
    
    // Анимация появления
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.day-column').forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        observer.observe(el);
    });
    
    // Подсветка текущего занятия
    function highlightCurrentLesson() {
        const now = new Date();
        const currentHour = now.getHours();
        const currentMinute = now.getMinutes();
        const currentTime = currentHour * 60 + currentMinute;
        
        document.querySelectorAll('.day-column.today .lesson-card').forEach(card => {
            const timeText = card.querySelector('.time-start')?.textContent;
            if (!timeText) return;
            
            const [hours, minutes] = timeText.split(':').map(Number);
            const lessonStart = hours * 60 + minutes;
            const lessonEnd = lessonStart + 95;
            
            if (currentTime >= lessonStart && currentTime <= lessonEnd) {
                card.style.boxShadow = '0 0 0 3px rgba(79, 70, 229, 0.3)';
                card.style.transform = 'scale(1.02)';
            }
        });
    }
    
    highlightCurrentLesson();
});