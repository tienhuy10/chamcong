from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
import sqlite3
import os
import base64
import uuid
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from email_validator import validate_email, EmailNotValidError
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'static/photos'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Giới hạn 16MB

# Khởi tạo Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Xử lý lỗi RequestEntityTooLarge
@app.errorhandler(RequestEntityTooLarge)
def handle_request_entity_too_large(error):
    flash('Dữ liệu gửi lên quá lớn. Vui lòng thử lại với ảnh có kích thước nhỏ hơn.', 'danger')
    return redirect(url_for('checkin'))

# Kết nối cơ sở dữ liệu
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Hàm phân tích thời gian linh hoạt
def parse_timestamp(timestamp_str):
    try:
        # Thử định dạng với microsecond và múi giờ
        return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f%z')
    except ValueError:
        try:
            # Thử định dạng với microsecond, không có múi giờ
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                # Thử định dạng không có microsecond, có múi giờ
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S%z')
            except ValueError:
                try:
                    # Thử định dạng không có microsecond, không có múi giờ
                    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    raise ValueError(f"Không thể phân tích thời gian: {timestamp_str}")

# Khởi tạo cơ sở dữ liệu
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tạo bảng users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT,
            role TEXT NOT NULL,
            department TEXT,
            position TEXT,
            phone TEXT,
            email TEXT,
            address TEXT,
            created_at DATETIME,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Tạo bảng time_records với cột note
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            timestamp DATETIME,
            type TEXT,
            photo_path TEXT,
            note TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng leave_requests
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            leave_date DATE,
            leave_period TEXT,
            reason TEXT,
            status TEXT,
            timestamp DATETIME
        )
    ''')
    
    # Tạo bảng campaigns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            start_date DATE,
            end_date DATE,
            description TEXT
        )
    ''')
    
    # Tạo bảng campaign_assignments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            user_id INTEGER,
            task_description TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng campaign_progress
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER,
            user_id INTEGER,
            progress INTEGER,
            status TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng notifications
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            message TEXT,
            timestamp DATETIME,
            is_read BOOLEAN,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message TEXT,
            timestamp DATETIME,
            is_read BOOLEAN,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng surveys
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            question TEXT,
            response TEXT,
            timestamp DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng training_courses
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            duration INTEGER,
            created_at DATETIME
        )
    ''')
    
    # Tạo bảng training_progress
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            course_id INTEGER,
            progress INTEGER,
            status TEXT,
            completed_at DATETIME,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (course_id) REFERENCES training_courses (id)
        )
    ''')
    
    # Tạo bảng hybrid_schedules
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hybrid_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE,
            location TEXT,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng peer_recognitions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS peer_recognitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message TEXT,
            timestamp DATETIME,
            points INTEGER,
            FOREIGN KEY (sender_id) REFERENCES users (id),
            FOREIGN KEY (receiver_id) REFERENCES users (id)
        )
    ''')
    
    # Tạo bảng shared_links
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shared_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE,
            period TEXT,
            created_at DATETIME,
            expires_at DATETIME
        )
    ''')
    
    # Tạo bảng settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL
        )
    ''')
    
    # Thêm chỉ mục
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active)')
    
    # Thêm dữ liệu mẫu
    hashed_password = generate_password_hash('password123', method='pbkdf2:sha256')
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, full_name, role, department, position, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('admin', hashed_password, 'Admin User', 'admin', 'HR', 'Manager', datetime.now(), 1))
    cursor.execute('''
        INSERT OR IGNORE INTO users (username, password, full_name, role, department, position, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('employee1', hashed_password, 'John Doe', 'employee', 'IT', 'Developer', datetime.now(), 1))
    
    cursor.execute('''
        INSERT OR IGNORE INTO campaigns (name, start_date, end_date, description)
        VALUES (?, ?, ?, ?)
    ''', ('Chiến dịch 1', '2025-05-01', '2025-05-31', 'Chiến dịch phát triển sản phẩm mới'))
    
    cursor.execute('''
        INSERT OR IGNORE INTO training_courses (title, description, duration, created_at)
        VALUES (?, ?, ?, ?)
    ''', ('Khóa học Python', 'Học lập trình Python cơ bản', 20, datetime.now()))
    
    # Thêm giá trị mặc định cho settings
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value)
        VALUES (?, ?)
    ''', ('checkin_morning', '08:00:00'))
    cursor.execute('''
        INSERT OR IGNORE INTO settings (key, value)
        VALUES (?, ?)
    ''', ('checkout_afternoon', '17:00:00'))
    
    conn.commit()
    conn.close()

# Lớp User cho Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role, is_active):
        self.id = id
        self.username = username
        self.role = role
        self._is_active = is_active
    
    def is_active(self):
        return self._is_active == 1

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['role'], user['is_active'])
    return None

# Route: Trang chính
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('employee_dashboard'))
    return redirect(url_for('login'))

# Route: Đăng nhập
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            if user['is_active'] == 0:
                flash('Tài khoản của bạn đã bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.', 'danger')
                return redirect(url_for('login'))
            user_obj = User(user['id'], user['username'], user['role'], user['is_active'])
            login_user(user_obj)
            flash('Đăng nhập thành công!', 'success')
            return redirect(url_for('index'))
        flash('Tên đăng nhập hoặc mật khẩu không đúng!', 'danger')
    return render_template('login.html')

# Route: Đăng xuất
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Đăng xuất thành công!', 'success')
    return redirect(url_for('login'))

# Route: Trang chủ nhân viên
@app.route('/employee/dashboard')
@login_required
def employee_dashboard():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    # Thống kê chấm công
    today = date.today()
    month_start = today.replace(day=1)
    time_records = conn.execute('''
        SELECT * FROM time_records 
        WHERE user_id = ? AND timestamp >= ?
    ''', (current_user.id, month_start)).fetchall()
    
    days_worked = 0
    days_absent = 0
    for day in range(1, today.day + 1):
        day_records = []
        for r in time_records:
            try:
                timestamp = parse_timestamp(r['timestamp'])
                if timestamp.date().day == day:
                    day_records.append(r)
            except ValueError:
                continue
        
        if len(day_records) == 4:  # Đầy đủ 4 lần chấm công
            days_worked += 1
        elif len(day_records) > 0:
            days_worked += 0.5
        else:
            days_absent += 1
    
    # Lấy bản ghi chấm công hôm nay
    today_records = conn.execute('''
        SELECT type, timestamp, note 
        FROM time_records 
        WHERE user_id = ? AND date(timestamp) = ?
        ORDER BY timestamp
    ''', (current_user.id, today)).fetchall()
    
    checkin_times = {
        'Vào Sáng': {'time': 'Chưa chấm', 'note': None},
        'Ra Sáng': {'time': 'Chưa chấm', 'note': None},
        'Vào Chiều': {'time': 'Chưa chấm', 'note': None},
        'Ra Chiều': {'time': 'Chưa chấm', 'note': None}
    }
    for record in today_records:
        try:
            timestamp = parse_timestamp(record['timestamp'])
            checkin_times[record['type']] = {
                'time': timestamp.strftime('%H:%M:%S'),
                'note': record['note']
            }
        except ValueError:
            continue
    
    # Thống kê chiến dịch
    campaigns = conn.execute('''
        SELECT c.*, cp.progress, cp.status 
        FROM campaigns c 
        JOIN campaign_assignments ca ON c.id = ca.campaign_id 
        JOIN campaign_progress cp ON c.id = cp.campaign_id 
        WHERE ca.user_id = ? AND cp.user_id = ?
    ''', (current_user.id, current_user.id)).fetchall()
    
    # Đơn xin nghỉ
    leave_requests = conn.execute('''
        SELECT * FROM leave_requests 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 5
    ''', (current_user.id,)).fetchall()
    
    # Khảo sát
    surveys = conn.execute('''
        SELECT * FROM surveys 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    ''', (current_user.id,)).fetchone()
    
    # Lịch làm việc hybrid
    schedules = conn.execute('''
        SELECT * FROM hybrid_schedules 
        WHERE user_id = ? AND date >= ? 
        ORDER BY date
    ''', (current_user.id, today)).fetchall()
    
    conn.close()
    return render_template('employee_dashboard.html', 
                         days_worked=days_worked, 
                         days_absent=days_absent,
                         time_records=time_records[-7:],
                         checkin_times=checkin_times,
                         campaigns=campaigns[:5],
                         leave_requests=leave_requests,
                         survey=surveys,
                         schedules=schedules)

# Route: Chấm công
@app.route('/checkin', methods=['GET', 'POST'])
@login_required
def checkin():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    today = date.today()
    current_time = datetime.now()
    is_morning = current_time.hour < 12  # Trước 12h là buổi sáng
    
    # Lấy giờ chấm công từ settings
    checkin_morning = conn.execute('SELECT value FROM settings WHERE key = "checkin_morning"').fetchone()
    checkin_morning = checkin_morning['value'] if checkin_morning else '08:00:00'
    checkin_morning_time = datetime.strptime(checkin_morning, '%H:%M:%S').time()
    
    # Lấy bản ghi chấm công hôm nay
    time_records = conn.execute('''
        SELECT type FROM time_records 
        WHERE user_id = ? AND date(timestamp) = ?
        ORDER BY timestamp DESC
    ''', (current_user.id, today)).fetchall()
    
    checkin_type = None
    is_late = False
    note = ''
    if not time_records:
        checkin_type = 'Vào Sáng' if is_morning else 'Vào Chiều'
        # Kiểm tra muộn
        if checkin_type == 'Vào Sáng' and current_time.time() > checkin_morning_time:
            minutes_late = int((current_time - datetime.combine(current_time.date(), checkin_morning_time)).total_seconds() / 60)
            is_late = True
            note = f'Muộn {minutes_late} phút'
        elif checkin_type == 'Vào Chiều' and current_time.hour >= 13:
            is_late = True
            note = 'Muộn'
    else:
        last_type = time_records[0]['type']
        if is_morning:
            if last_type == 'Vào Sáng':
                checkin_type = 'Ra Sáng'
            else:
                checkin_type = 'Vào Sáng'
                if current_time.time() > checkin_morning_time:
                    minutes_late = int((current_time - datetime.combine(current_time.date(), checkin_morning_time)).total_seconds() / 60)
                    is_late = True
                    note = f'Muộn {minutes_late} phút'
        else:
            if last_type == 'Vào Chiều':
                checkin_type = 'Ra Chiều'
            elif last_type == 'Ra Sáng':
                checkin_type = 'Vào Chiều'
                if current_time.hour >= 13:
                    is_late = True
                    note = 'Muộn'
            else:
                checkin_type = 'Ra Chiều'
    
    if request.method == 'POST':
        try:
            photo_data = request.form['photo_data']
            user_note = request.form.get('note', '')
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            photo_filename = f"{current_user.id}_{timestamp}.png"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            
            # Lưu ảnh
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            with open(photo_path, 'wb') as f:
                f.write(base64.b64decode(photo_data.split(',')[1]))
            
            # Lưu bản ghi chấm công
            conn.execute('''
                INSERT INTO time_records (user_id, timestamp, type, photo_path, note)
                VALUES (?, ?, ?, ?, ?)
            ''', (current_user.id, datetime.now(), checkin_type, photo_path, note or user_note))
            conn.commit()
            
            flash(f'Chấm công {checkin_type} thành công!', 'success')
            return redirect(url_for('employee_dashboard'))
        except RequestEntityTooLarge:
            flash('Ảnh quá lớn. Vui lòng thử lại với ảnh nhỏ hơn.', 'danger')
            return redirect(url_for('checkin'))
        except Exception as e:
            print(f"Checkin error: {str(e)}")
            flash(f'Lỗi khi chấm công: {str(e)}', 'danger')
            return redirect(url_for('checkin'))
        finally:
            conn.close()
    
    conn.close()
    return render_template('checkin.html', checkin_type=checkin_type, is_late=is_late)

# Route: Xin nghỉ phép
@app.route('/leave_request', methods=['GET', 'POST'])
@login_required
def leave_request():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        leave_date = request.form['leave_date']
        leave_period = request.form['leave_period']
        reason = request.form['reason']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO leave_requests (user_id, leave_date, leave_period, reason, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (current_user.id, leave_date, leave_period, reason, 'Đang chờ', datetime.now()))
        conn.commit()
        conn.close()
        
        flash('Gửi đơn xin nghỉ thành công!', 'success')
        return redirect(url_for('employee_dashboard'))
    
    return render_template('leave_request.html')

# Route: Báo cáo công việc
@app.route('/work_report', methods=['GET', 'POST'])
@login_required
def work_report():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        report_content = request.form['report_content']
        flash('Gửi báo cáo thành công!', 'success')
        return redirect(url_for('employee_dashboard'))
    
    return render_template('work_report.html')

# Route: Chiến dịch
@app.route('/employee_campaigns')
@login_required
def employee_campaigns():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    campaigns = conn.execute('''
        SELECT c.*, cp.progress, cp.status 
        FROM campaigns c 
        JOIN campaign_assignments ca ON c.id = ca.campaign_id 
        JOIN campaign_progress cp ON c.id = cp.campaign_id 
        WHERE ca.user_id = ? AND cp.user_id = ?
    ''', (current_user.id, current_user.id)).fetchall()
    conn.close()
    
    return render_template('employee_campaigns.html', campaigns=campaigns)

# Route: Gửi tin nhắn
@app.route('/send_message', methods=['GET', 'POST'])
@login_required
def send_message():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT id, username FROM users WHERE id != ? AND is_active = 1', (current_user.id,)).fetchall()
    
    if request.method == 'POST':
        receiver_id = request.form['receiver_id']
        message = request.form['message']
        
        conn.execute('''
            INSERT INTO messages (sender_id, receiver_id, message, timestamp, is_read)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.id, receiver_id, message, datetime.now(), False))
        conn.commit()
        flash('Gửi tin nhắn thành công!', 'success')
        return redirect(url_for('employee_dashboard'))
    
    conn.close()
    return render_template('send_message.html', users=users)

# Route: Khảo sát
@app.route('/employee/survey', methods=['GET', 'POST'])
@login_required
def employee_survey():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        question = request.form['question']
        response = request.form['response']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO surveys (user_id, question, response, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (current_user.id, question, response, datetime.now()))
        conn.commit()
        conn.close()
        
        flash('Gửi khảo sát thành công!', 'success')
        return redirect(url_for('employee_dashboard'))
    
    return render_template('survey.html')

# Route: Đào tạo
@app.route('/employee/training')
@login_required
def employee_training():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    courses = conn.execute('''
        SELECT tc.*, tp.progress, tp.status 
        FROM training_courses tc 
        JOIN training_progress tp ON tc.id = tp.course_id 
        WHERE tp.user_id = ?
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return render_template('training.html', courses=courses)

# Route: Lịch làm việc hybrid
@app.route('/employee/hybrid_schedule', methods=['GET', 'POST'])
@login_required
def employee_hybrid_schedule():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        date = request.form['date']
        location = request.form['location']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO hybrid_schedules (user_id, date, location, status)
            VALUES (?, ?, ?, ?)
        ''', (current_user.id, date, location, 'Đang chờ'))
        conn.commit()
        conn.close()
        
        flash('Yêu cầu lịch làm việc thành công!', 'success')
        return redirect(url_for('employee_dashboard'))
    
    conn = get_db_connection()
    schedules = conn.execute('''
        SELECT * FROM hybrid_schedules 
        WHERE user_id = ? 
        ORDER BY date
    ''', (current_user.id,)).fetchall()
    conn.close()
    
    return render_template('hybrid_schedule.html', schedules=schedules)

# Route: Công nhận đồng nghiệp
@app.route('/mark_recognition', methods=['GET', 'POST'])
@login_required
def mark_recognition():
    if current_user.role != 'employee':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    users = conn.execute('SELECT id, username FROM users WHERE id != ? AND is_active = 1', (current_user.id,)).fetchall()
    
    if request.method == 'POST':
        receiver_id = request.form['receiver_id']
        message = request.form['message']
        points = int(request.form['points'])
        
        conn.execute('''
            INSERT INTO peer_recognitions (sender_id, receiver_id, message, timestamp, points)
            VALUES (?, ?, ?, ?, ?)
        ''', (current_user.id, receiver_id, message, datetime.now(), points))
        conn.commit()
        flash('Gửi lời công nhận thành công!', 'success')
        return redirect(url_for('employee_dashboard'))
    
    conn.close()
    return render_template('mark_recognition.html', users=users)

# Route: Trang chủ quản trị viên
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    total_employees = conn.execute('SELECT COUNT(*) FROM users WHERE role = "employee" AND is_active = 1').fetchone()[0]
    campaigns = conn.execute('SELECT * FROM campaigns').fetchall()
    surveys = conn.execute('SELECT * FROM surveys GROUP BY question').fetchall()
    conn.close()
    
    return render_template('admin_dashboard.html', total_employees=total_employees, campaigns=campaigns, surveys=surveys)

# Route: Quản lý nhân viên
@app.route('/admin_employees', methods=['GET'])
@login_required
def admin_employees():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    if not current_user.is_active:
        flash('Tài khoản của bạn đã bị vô hiệu hóa!', 'danger')
        return redirect(url_for('logout'))
    
    try:
        conn = get_db_connection()
        employees = conn.execute('SELECT * FROM users').fetchall()  # Lấy tất cả, kể cả is_active = 0
        conn.close()
        return render_template('admin_employees.html', employees=employees)
    except sqlite3.Error as e:
        print(f"Database error in admin_employees: {e}")
        flash('Lỗi khi lấy danh sách nhân viên!', 'danger')
        return render_template('admin_employees.html', employees=[])

# Route: Thêm nhân viên
@app.route('/admin_add_employee', methods=['POST'])
@login_required
def admin_add_employee():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    if not current_user.is_active:
        return jsonify({'error': 'Tài khoản của bạn đã bị vô hiệu hóa!'}), 403
    
    username = request.form.get('username')
    password = request.form.get('password')
    full_name = request.form.get('full_name')
    department = request.form.get('department')
    position = request.form.get('position')
    phone = request.form.get('phone')
    email = request.form.get('email')
    address = request.form.get('address')
    role = request.form.get('role')
    is_active = 1 if request.form.get('is_active') == '1' else 0
    
    # Kiểm tra bắt buộc
    if not all([username, password, full_name, role]):
        return jsonify({'error': 'Vui lòng điền đầy đủ thông tin bắt buộc!'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Mật khẩu phải có ít nhất 6 ký tự!'}), 400
    if role not in ['admin', 'employee']:
        return jsonify({'error': 'Vai trò không hợp lệ!'}), 400
    
    # Kiểm tra email
    if email:
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError as e:
            return jsonify({'error': f'Email không hợp lệ: {str(e)}'}), 400
    
    # Kiểm tra số điện thoại
    if phone and not re.match(r'^\d{10,12}$', phone):
        return jsonify({'error': 'Số điện thoại phải có 10-12 số!'}), 400
    
    conn = get_db_connection()
    try:
        # Kiểm tra trùng username
        existing_user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if existing_user:
            return jsonify({'error': 'Tên đăng nhập đã tồn tại!'}), 400
        
        # Kiểm tra trùng email (tùy chọn)
        if email:
            existing_email = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
            if existing_email:
                return jsonify({'error': 'Email đã được sử dụng!'}), 400
        
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        conn.execute('''
            INSERT INTO users (username, password, full_name, role, department, position, phone, email, address, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (username, hashed_password, full_name, role, department, position, phone, email, address, datetime.now(), is_active))
        conn.commit()
        
        return jsonify({'success': 'Thêm nhân viên thành công!'})
    except sqlite3.Error as e:
        print(f"Database error in admin_add_employee: {e}")
        return jsonify({'error': f'Lỗi cơ sở dữ liệu: {str(e)}'}), 500
    finally:
        conn.close()

# Route: Sửa nhân viên
@app.route('/admin_edit_employee', methods=['POST'])
@login_required
def admin_edit_employee():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    if not current_user.is_active:
        return jsonify({'error': 'Tài khoản của bạn đã bị vô hiệu hóa!'}), 403
    
    user_id = request.form.get('user_id')
    full_name = request.form.get('full_name')
    department = request.form.get('department')
    position = request.form.get('position')
    phone = request.form.get('phone')
    email = request.form.get('email')
    address = request.form.get('address')
    role = request.form.get('role')
    is_active = 1 if request.form.get('is_active') == '1' else 0
    password = request.form.get('password')
    
    # Kiểm tra bắt buộc
    if not all([user_id, full_name, role]):
        return jsonify({'error': 'Vui lòng điền đầy đủ thông tin bắt buộc!'}), 400
    if role not in ['admin', 'employee']:
        return jsonify({'error': 'Vai trò không hợp lệ!'}), 400
    
    # Kiểm tra không vô hiệu hóa chính mình
    if user_id == str(current_user.id) and is_active == 0:
        return jsonify({'error': 'Không thể vô hiệu hóa tài khoản của chính bạn!'}), 400
    
    # Kiểm tra email
    if email:
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError as e:
            return jsonify({'error': f'Email không hợp lệ: {str(e)}'}), 400
    
    # Kiểm tra số điện thoại
    if phone and not re.match(r'^\d{10,12}$', phone):
        return jsonify({'error': 'Số điện thoại phải có 10-12 số!'}), 400
    
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'Nhân viên không tồn tại!'}), 404
        
        # Kiểm tra trùng email
        if email and email != user['email']:
            existing_email = conn.execute('SELECT * FROM users WHERE email = ? AND id != ?', (email, user_id)).fetchone()
            if existing_email:
                return jsonify({'error': 'Email đã được sử dụng!'}), 400
        
        if password and len(password) < 6:
            return jsonify({'error': 'Mật khẩu mới phải có ít nhất 6 ký tự!'}), 400
        
        if password:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            conn.execute('''
                UPDATE users 
                SET username = ?, full_name = ?, role = ?, department = ?, position = ?, phone = ?, email = ?, address = ?, password = ?, is_active = ?
                WHERE id = ?
            ''', (user['username'], full_name, role, department, position, phone, email, address, hashed_password, is_active, user_id))
        else:
            conn.execute('''
                UPDATE users 
                SET username = ?, full_name = ?, role = ?, department = ?, position = ?, phone = ?, email = ?, address = ?, is_active = ?
                WHERE id = ?
            ''', (user['username'], full_name, role, department, position, phone, email, address, is_active, user_id))
        
        conn.commit()
        return jsonify({'success': 'Cập nhật nhân viên thành công!'})
    except sqlite3.Error as e:
        print(f"Database error in admin_edit_employee: {e}")
        return jsonify({'error': f'Lỗi cơ sở dữ liệu: {str(e)}'}), 500
    finally:
        conn.close()

# Route: Xóa nhân viên (chỉ xóa cứng)
@app.route('/admin_delete_employee', methods=['POST'])
@login_required
def admin_delete_employee():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    if not current_user.is_active:
        return jsonify({'error': 'Tài khoản của bạn đã bị vô hiệu hóa!'}), 403
    
    user_id = request.form.get('user_id')
    
    if not user_id:
        print(f"Error: Missing user_id in admin_delete_employee")
        return jsonify({'error': 'Thiếu ID nhân viên!'}), 400
    
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            print(f"Error: User not found, user_id: {user_id}")
            return jsonify({'error': 'Nhân viên không tồn tại!'}), 404
        if user_id == str(current_user.id):
            print(f"Error: Attempt to delete self, user_id: {user_id}")
            return jsonify({'error': 'Không thể xóa tài khoản của chính bạn!'}), 400
        if user['role'] == 'admin':
            print(f"Error: Attempt to delete admin, user_id: {user_id}")
            return jsonify({'error': 'Không thể xóa tài khoản admin!'}), 400
        
        print(f"Performing hard delete for user_id: {user_id}")
        # Xóa tất cả dữ liệu liên quan
        conn.execute('DELETE FROM time_records WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM leave_requests WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM campaign_assignments WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM campaign_progress WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM notifications WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?', (user_id, user_id))
        conn.execute('DELETE FROM surveys WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM training_progress WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM hybrid_schedules WHERE user_id = ?', (user_id,))
        conn.execute('DELETE FROM peer_recognitions WHERE sender_id = ? OR receiver_id = ?', (user_id, user_id))
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        print(f"Successfully deleted user_id: {user_id}")
        return jsonify({'success': 'Xóa nhân viên thành công!'})
    except sqlite3.Error as e:
        print(f"Database error in admin_delete_employee: {e}")
        return jsonify({'error': f'Lỗi cơ sở dữ liệu: {str(e)}'}), 500
    finally:
        conn.close()

# Route: Toggle kích hoạt nhân viên
@app.route('/admin_toggle_active', methods=['POST'])
@login_required
def admin_toggle_active():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    if not current_user.is_active:
        return jsonify({'error': 'Tài khoản của bạn đã bị vô hiệu hóa!'}), 403
    
    user_id = request.form.get('user_id')
    if not user_id:
        print(f"Error: Missing user_id in admin_toggle_active")
        return jsonify({'error': 'Thiếu ID nhân viên!'}), 400
    if user_id == str(current_user.id):
        print(f"Error: Attempt to toggle self, user_id: {user_id}")
        return jsonify({'error': 'Không thể thay đổi trạng thái của chính bạn!'}), 400
    
    conn = get_db_connection()
    try:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        if not user:
            print(f"Error: User not found, user_id: {user_id}")
            return jsonify({'error': 'Nhân viên không tồn tại!'}), 404
        
        new_status = 0 if user['is_active'] else 1
        conn.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        conn.commit()
        print(f"Successfully toggled user_id: {user_id} to is_active: {new_status}")
        return jsonify({'success': 'Cập nhật trạng thái thành công!', 'is_active': new_status})
    except sqlite3.Error as e:
        print(f"Database error in admin_toggle_active: {e}")
        return jsonify({'error': f'Lỗi cơ sở dữ liệu: {str(e)}'}), 500
    finally:
        conn.close()

# Route: Quản lý chấm công
@app.route('/admin_attendance', methods=['GET', 'POST'])
@login_required
def admin_attendance():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    employees = conn.execute('SELECT id, full_name FROM users WHERE role = "employee" AND is_active = 1').fetchall()
    
    # Lấy giờ chấm công từ settings
    checkin_morning = conn.execute('SELECT value FROM settings WHERE key = "checkin_morning"').fetchone()
    checkin_morning = checkin_morning['value'] if checkin_morning else '08:00:00'
    
    # Xác định khoảng thời gian
    period = request.form.get('period', 'week') if request.method == 'POST' else 'week'
    today = date.today()
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())  # Thứ Hai
        end_date = start_date + timedelta(days=6)  # Chủ Nhật
    else:
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    
    dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    
    # Lấy bản ghi chấm công và đơn xin nghỉ
    time_records = conn.execute('''
        SELECT tr.*, u.full_name 
        FROM time_records tr 
        JOIN users u ON tr.user_id = u.id
        WHERE date(tr.timestamp) >= ? AND date(tr.timestamp) <= ? AND u.is_active = 1
    ''', (start_date, end_date)).fetchall()
    
    leave_requests = conn.execute('''
        SELECT lr.*, u.full_name 
        FROM leave_requests lr 
        JOIN users u ON lr.user_id = u.id
        WHERE lr.leave_date >= ? AND lr.leave_date <= ? AND lr.status = 'Đã duyệt' AND u.is_active = 1
    ''', (start_date, end_date)).fetchall()
    
    # Tổng hợp dữ liệu (ngày là hàng, nhân viên là cột)
    attendance_data = {}
    for d in dates:
        date_str = d.strftime('%Y-%m-%d')
        attendance_data[date_str] = {
            'date': d,
            'records': {e['id']: {'status': 'Chưa chấm', 'leave_reason': None, 'hours_worked': 0, 'note': None} for e in employees}
        }
    
    # Tính trạng thái và số tiếng làm việc
    for record in time_records:
        try:
            record_date = parse_timestamp(record['timestamp']).date()
            user_id = record['user_id']
            if record_date in [d for d in dates]:
                date_str = record_date.strftime('%Y-%m-%d')
                if attendance_data[date_str]['records'][user_id]['status'] == 'Chưa chấm':
                    attendance_data[date_str]['records'][user_id]['status'] = 'Thiếu'
                
                # Kiểm tra đi muộn
                if record['type'] == 'Vào Sáng':
                    record_time = parse_timestamp(record['timestamp']).time()
                    late_threshold_time = datetime.strptime(checkin_morning, '%H:%M:%S').time()
                    if record_time > late_threshold_time:
                        record_dt = datetime.combine(record_date, record_time)
                        threshold_dt = datetime.combine(record_date, late_threshold_time)
                        minutes_late = int((record_dt - threshold_dt).total_seconds() / 60)
                        attendance_data[date_str]['records'][user_id]['note'] = f'Muộn {minutes_late} phút'
                
                if len([r for r in time_records if r['user_id'] == user_id and parse_timestamp(r['timestamp']).date() == record_date]) >= 4:
                    attendance_data[date_str]['records'][user_id]['status'] = 'Đầy đủ'
                
                # Tính số tiếng làm việc
                day_records = [r for r in time_records if r['user_id'] == user_id and parse_timestamp(r['timestamp']).date() == record_date]
                checkin_times = {r['type']: parse_timestamp(r['timestamp']) for r in day_records}
                if 'Vào Sáng' in checkin_times and 'Ra Chiều' in checkin_times:
                    hours = (checkin_times['Ra Chiều'] - checkin_times['Vào Sáng']).total_seconds() / 3600
                    attendance_data[date_str]['records'][user_id]['hours_worked'] = round(hours, 1)
                elif 'Vào Sáng' in checkin_times and 'Vào Chiều' in checkin_times:
                    hours = (checkin_times['Vào Chiều'] - checkin_times['Vào Sáng']).total_seconds() / 3600
                    attendance_data[date_str]['records'][user_id]['hours_worked'] = round(hours, 1)
        except ValueError:
            continue
    
    for leave in leave_requests:
        leave_date = datetime.strptime(leave['leave_date'], '%Y-%m-%d').date()
        if leave_date in [d for d in dates]:
            user_id = leave['user_id']
            date_str = leave_date.strftime('%Y-%m-%d')
            attendance_data[date_str]['records'][user_id]['status'] = 'Nghỉ'
            attendance_data[date_str]['records'][user_id]['leave_reason'] = leave['reason']
    
    # Tổng hợp số ngày công và ngày nghỉ
    summary_data = {e['id']: {'days_worked': 0, 'days_absent': 0, 'full_name': e['full_name']} for e in employees}
    for date_str, data in attendance_data.items():
        for emp_id in summary_data:
            status = data['records'][emp_id]['status']
            day_records = [r for r in time_records if r['user_id'] == emp_id and parse_timestamp(r['timestamp']).date() == data['date']]
            if status == 'Đầy đủ':
                summary_data[emp_id]['days_worked'] += 1
            elif status == 'Thiếu' and len(day_records) > 0:
                summary_data[emp_id]['days_worked'] += 0.5
            elif status == 'Nghỉ':
                summary_data[emp_id]['days_absent'] += 1
    
    conn.close()
    
    return render_template('admin_attendance.html', 
                         attendance_data=attendance_data, 
                         employees=employees, 
                         period=period,
                         summary_data=summary_data)

# Route: Chi tiết chấm công
@app.route('/admin_attendance_details', methods=['POST'])
@login_required
def admin_attendance_details():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    user_id = request.form.get('user_id')
    date = request.form.get('date')
    
    conn = get_db_connection()
    records = conn.execute('''
        SELECT id, type, timestamp, photo_path, note 
        FROM time_records 
        WHERE user_id = ? AND date(timestamp) = ?
        ORDER BY timestamp
    ''', (user_id, date)).fetchall()
    
    details = {
        'Vào Sáng': {'time': 'Chưa chấm', 'record_id': None, 'photo': None, 'note': None},
        'Ra Sáng': {'time': 'Chưa chấm', 'record_id': None, 'photo': None, 'note': None},
        'Vào Chiều': {'time': 'Chưa chấm', 'record_id': None, 'photo': None, 'note': None},
        'Ra Chiều': {'time': 'Chưa chấm', 'record_id': None, 'photo': None, 'note': None},
        'hours_worked': 0,
        'photos': []
    }
    
    checkin_times = {}
    for record in records:
        try:
            timestamp = parse_timestamp(record['timestamp'])
            time_str = timestamp.strftime('%H:%M:%S')
            details[record['type']] = {
                'time': time_str,
                'record_id': record['id'],
                'photo': url_for('serve_photo', filename=os.path.basename(record['photo_path'])) if record['photo_path'] else None,
                'note': record['note']
            }
            checkin_times[record['type']] = timestamp
            if record['photo_path']:
                details['photos'].append(url_for('serve_photo', filename=os.path.basename(record['photo_path'])))
        except ValueError:
            continue
    
    # Tính số giờ làm việc
    if 'Vào Sáng' in checkin_times and 'Ra Chiều' in checkin_times:
        hours = (checkin_times['Ra Chiều'] - checkin_times['Vào Sáng']).total_seconds() / 3600
        details['hours_worked'] = round(hours, 1)
    elif 'Vào Sáng' in checkin_times and 'Vào Chiều' in checkin_times:
        hours = (checkin_times['Vào Chiều'] - checkin_times['Vào Sáng']).total_seconds() / 3600
        details['hours_worked'] = round(hours, 1)
    
    conn.close()
    return jsonify(details)

# Route: Danh sách bản ghi chấm công
@app.route('/admin_attendance_records', methods=['POST'])
@login_required
def admin_attendance_records():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    user_id = request.form.get('user_id', 'all')
    period = request.form.get('period', 'week')
    
    today = date.today()
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())  # Thứ Hai
        end_date = start_date + timedelta(days=6)  # Chủ Nhật
    else:
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    
    conn = get_db_connection()
    query = '''
        SELECT tr.id, tr.user_id, tr.timestamp, tr.type, tr.photo_path, tr.note, u.full_name
        FROM time_records tr
        JOIN users u ON tr.user_id = u.id
        WHERE date(tr.timestamp) >= ? AND date(tr.timestamp) <= ? AND u.is_active = 1
    '''
    params = [start_date, end_date]
    if user_id != 'all':
        query += ' AND tr.user_id = ?'
        params.append(user_id)
    
    records = conn.execute(query, params).fetchall()
    
    # Tính tổng giờ làm mỗi ngày
    records_by_date = {}
    for record in records:
        try:
            record_date = parse_timestamp(record['timestamp']).date()
            user_id = record['user_id']
            date_str = record_date.strftime('%Y-%m-%d')
            if date_str not in records_by_date:
                records_by_date[date_str] = {}
            if user_id not in records_by_date[date_str]:
                records_by_date[date_str][user_id] = []
            records_by_date[date_str][user_id].append(record)
        except ValueError:
            continue
    
    result = []
    for record in records:
        try:
            timestamp = parse_timestamp(record['timestamp'])
            record_date = timestamp.date()
            date_str = record_date.strftime('%Y-%m-%d')
            user_id = record['user_id']
            
            hours_worked = 0
            day_records = records_by_date.get(date_str, {}).get(user_id, [])
            checkin_times = {r['type']: parse_timestamp(r['timestamp']) for r in day_records}
            if 'Vào Sáng' in checkin_times and 'Ra Chiều' in checkin_times:
                hours = (checkin_times['Ra Chiều'] - checkin_times['Vào Sáng']).total_seconds() / 3600
                hours_worked = round(hours, 1)
            elif 'Vào Sáng' in checkin_times and 'Vào Chiều' in checkin_times:
                hours = (checkin_times['Vào Chiều'] - checkin_times['Vào Sáng']).total_seconds() / 3600
                hours_worked = round(hours, 1)
            
            result.append({
                'id': record['id'],
                'user_id': record['user_id'],
                'full_name': record['full_name'],
                'date': date_str,
                'type': record['type'],
                'time': timestamp.strftime('%H:%M:%S'),
                'photo': url_for('serve_photo', filename=os.path.basename(record['photo_path'])) if record['photo_path'] else None,
                'hours_worked': hours_worked,
                'note': record['note']
            })
        except ValueError:
            continue
    
    conn.close()
    return jsonify({'records': result})

# Route: Chỉnh sửa chấm công
@app.route('/admin_edit_attendance', methods=['POST'])
@login_required
def admin_edit_attendance():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    record_id = request.form.get('record_id')
    timestamp = request.form.get('timestamp')
    checkin_type = request.form.get('type')
    photo_data = request.form.get('photo_data')
    note = request.form.get('note', '')
    
    conn = get_db_connection()
    try:
        # Kiểm tra record_id
        record = conn.execute('SELECT * FROM time_records WHERE id = ?', (record_id,)).fetchone()
        if not record:
            return jsonify({'error': 'Bản ghi không tồn tại!'}), 404
        
        # Xử lý ảnh mới (nếu có)
        photo_path = record['photo_path']
        if photo_data and photo_data.startswith('data:image'):
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            photo_filename = f"{record['user_id']}_{timestamp_str}.png"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            with open(photo_path, 'wb') as f:
                f.write(base64.b64decode(photo_data.split(',')[1]))
        
        # Cập nhật bản ghi
        conn.execute('''
            UPDATE time_records 
            SET timestamp = ?, type = ?, photo_path = ?, note = ?
            WHERE id = ?
        ''', (timestamp, checkin_type, photo_path, note, record_id))
        conn.commit()
        
        return jsonify({'success': 'Cập nhật chấm công thành công!'})
    except Exception as e:
        print(f"Edit attendance error: {e}")
        return jsonify({'error': f'Lỗi khi cập nhật: {str(e)}'}), 500
    finally:
        conn.close()

# Route: Thêm chấm công
@app.route('/admin_add_attendance', methods=['POST'])
@login_required
def admin_add_attendance():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    user_id = request.form.get('user_id')
    date = request.form.get('date')
    timestamp = request.form.get('timestamp')
    checkin_type = request.form.get('type')
    photo_data = request.form.get('photo_data')
    note = request.form.get('note', '')
    
    conn = get_db_connection()
    try:
        # Kiểm tra định dạng timestamp
        full_timestamp = f"{date} {timestamp}"
        parse_timestamp(full_timestamp)  # Kiểm tra hợp lệ
        
        # Kiểm tra user_id
        user = conn.execute('SELECT * FROM users WHERE id = ? AND is_active = 1', (user_id,)).fetchone()
        if not user:
            return jsonify({'error': 'Nhân viên không tồn tại hoặc đã bị vô hiệu hóa!'}), 404
        
        # Kiểm tra đi muộn nếu là Vào Sáng
        if checkin_type == 'Vào Sáng':
            checkin_morning = conn.execute('SELECT value FROM settings WHERE key = "checkin_morning"').fetchone()
            checkin_morning = checkin_morning['value'] if checkin_morning else '08:00:00'
            record_time = datetime.strptime(timestamp, '%H:%M:%S').time()
            late_threshold_time = datetime.strptime(checkin_morning, '%H:%M:%S').time()
            if record_time > late_threshold_time:
                record_dt = datetime.strptime(full_timestamp, '%Y-%m-%d %H:%M:%S')
                threshold_dt = datetime.combine(record_dt.date(), late_threshold_time)
                minutes_late = int((record_dt - threshold_dt).total_seconds() / 60)
                note = f'Muộn {minutes_late} phút'
        
        # Xử lý ảnh (nếu có)
        photo_path = None
        if photo_data and photo_data.startswith('data:image'):
            timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            photo_filename = f"{user_id}_{timestamp_str}.png"
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], photo_filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            with open(photo_path, 'wb') as f:
                f.write(base64.b64decode(photo_data.split(',')[1]))
        
        # Thêm bản ghi
        conn.execute('''
            INSERT INTO time_records (user_id, timestamp, type, photo_path, note)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, full_timestamp, checkin_type, photo_path, note))
        conn.commit()
        
        return jsonify({'success': 'Thêm chấm công thành công!'})
    except ValueError as e:
        return jsonify({'error': f'Định dạng thời gian không hợp lệ: {str(e)}'}), 400
    except Exception as e:
        print(f"Add attendance error: {e}")
        return jsonify({'error': f'Lỗi khi thêm: {str(e)}'}), 500
    finally:
        conn.close()

# Route: Tạo link chia sẻ
@app.route('/share_attendance', methods=['POST'])
@login_required
def share_attendance():
    if current_user.role != 'admin':
        return jsonify({'error': 'Bạn không có quyền truy cập!'}), 403
    
    period = request.form.get('period', 'week')
    token = str(uuid.uuid4())
    created_at = datetime.now()
    expires_at = created_at + timedelta(days=7)  # Link hết hạn sau 7 ngày
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO shared_links (token, period, created_at, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (token, period, created_at, expires_at))
    conn.commit()
    conn.close()
    
    share_url = url_for('public_attendance', token=token, _external=True)
    return jsonify({'share_url': share_url})

# Route: Xem bảng chấm công công khai
@app.route('/public_attendance/<token>')
def public_attendance(token):
    conn = get_db_connection()
    link = conn.execute('''
        SELECT * FROM shared_links 
        WHERE token = ? AND expires_at > ?
    ''', (token, datetime.now())).fetchone()
    
    if not link:
        conn.close()
        return render_template('error.html', message='Link không hợp lệ hoặc đã hết hạn!')
    
    period = link['period']
    today = date.today()
    if period == 'week':
        start_date = today - timedelta(days=today.weekday())  # Thứ Hai
        end_date = start_date + timedelta(days=6)  # Chủ Nhật
    else:
        start_date = today.replace(day=1)
        end_date = (start_date + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    
    dates = [start_date + timedelta(days=x) for x in range((end_date - start_date).days + 1)]
    employees = conn.execute('SELECT id, full_name FROM users WHERE role = "employee" AND is_active = 1').fetchall()
    
    # Lấy bản ghi chấm công và đơn xin nghỉ
    time_records = conn.execute('''
        SELECT tr.*, u.full_name 
        FROM time_records tr 
        JOIN users u ON tr.user_id = u.id
        WHERE date(tr.timestamp) >= ? AND date(tr.timestamp) <= ? AND u.is_active = 1
    ''', (start_date, end_date)).fetchall()
    
    leave_requests = conn.execute('''
        SELECT lr.*, u.full_name 
        FROM leave_requests lr 
        JOIN users u ON lr.user_id = u.id
        WHERE lr.leave_date >= ? AND lr.leave_date <= ? AND lr.status = 'Đã duyệt' AND u.is_active = 1
    ''', (start_date, end_date)).fetchall()
    
    # Tổng hợp dữ liệu (không bao gồm hours_worked và leave_reason)
    attendance_data = {}
    for d in dates:
        date_str = d.strftime('%Y-%m-%d')
        attendance_data[date_str] = {
            'date': d,
            'records': {e['id']: {'status': 'Chưa chấm'} for e in employees}
        }
    
    for record in time_records:
        try:
            record_date = parse_timestamp(record['timestamp']).date()
            user_id = record['user_id']
            if record_date in [d for d in dates]:
                date_str = record_date.strftime('%Y-%m-%d')
                if attendance_data[date_str]['records'][user_id]['status'] == 'Chưa chấm':
                    attendance_data[date_str]['records'][user_id]['status'] = 'Thiếu'
                if len([r for r in time_records if r['user_id'] == user_id and parse_timestamp(r['timestamp']).date() == record_date]) >= 4:
                    attendance_data[date_str]['records'][user_id]['status'] = 'Đầy đủ'
        except ValueError:
            continue
    
    for leave in leave_requests:
        leave_date = datetime.strptime(leave['leave_date'], '%Y-%m-%d').date()
        if leave_date in [d for d in dates]:
            user_id = leave['user_id']
            date_str = leave_date.strftime('%Y-%m-%d')
            attendance_data[date_str]['records'][user_id]['status'] = 'Nghỉ'
    
    # Tổng hợp số ngày công và ngày nghỉ
    summary_data = {e['id']: {'days_worked': 0, 'days_absent': 0, 'full_name': e['full_name']} for e in employees}
    for date_str, data in attendance_data.items():
        for emp_id in summary_data:
            status = data['records'][emp_id]['status']
            day_records = [r for r in time_records if r['user_id'] == emp_id and parse_timestamp(r['timestamp']).date() == data['date']]
            if status == 'Đầy đủ':
                summary_data[emp_id]['days_worked'] += 1
            elif status == 'Thiếu' and len(day_records) > 0:
                summary_data[emp_id]['days_worked'] += 0.5
            elif status == 'Nghỉ':
                summary_data[emp_id]['days_absent'] += 1
    
    conn.close()
    
    return render_template('public_attendance.html', 
                         attendance_data=attendance_data, 
                         employees=employees, 
                         period=period,
                         summary_data=summary_data)

# Route: Quản lý đơn xin nghỉ
@app.route('/admin_leave_requests', methods=['GET', 'POST'])
@login_required
def admin_leave_requests():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        request_id = request.form['request_id']
        status = request.form['status']
        
        conn.execute('UPDATE leave_requests SET status = ? WHERE id = ?', (status, request_id))
        conn.commit()
        flash('Cập nhật trạng thái đơn xin nghỉ thành công!', 'success')
    
    leave_requests = conn.execute('''
        SELECT lr.*, u.full_name 
        FROM leave_requests lr 
        JOIN users u ON lr.user_id = u.id
        WHERE u.is_active = 1
    ''').fetchall()
    conn.close()
    
    return render_template('admin_leave_requests.html', leave_requests=leave_requests)

# Route: Quản lý chiến dịch
@app.route('/admin_campaigns', methods=['GET', 'POST'])
@login_required
def admin_campaigns():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        name = request.form['name']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        description = request.form['description']
        
        conn.execute('''
            INSERT INTO campaigns (name, start_date, end_date, description)
            VALUES (?, ?, ?, ?)
        ''', (name, start_date, end_date, description))
        conn.commit()
        flash('Tạo chiến dịch thành công!', 'success')
    
    campaigns = conn.execute('SELECT * FROM campaigns').fetchall()
    conn.close()
    
    return render_template('admin_campaigns.html', campaigns=campaigns)

# Route: Quản lý dữ liệu
@app.route('/admin_data_management')
@login_required
def admin_data_management():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    return render_template('admin_data_management.html')

# Route: Cài đặt
@app.route('/admin_settings', methods=['GET', 'POST'])
@login_required
def admin_settings():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    
    if request.method == 'POST':
        checkin_morning = request.form.get('checkin_morning')
        checkout_afternoon = request.form.get('checkout_afternoon')
        
        # Xác thực định dạng giờ
        try:
            datetime.strptime(checkin_morning, '%H:%M')
            datetime.strptime(checkout_afternoon, '%H:%M')
        except ValueError:
            conn.close()
            return jsonify({'error': 'Định dạng giờ không hợp lệ! Vui lòng nhập theo dạng HH:MM.'}), 400
        
        # Lưu vào bảng settings
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', 
                    ('checkin_morning', checkin_morning + ':00'))
        conn.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', 
                    ('checkout_afternoon', checkout_afternoon + ':00'))
        conn.commit()
        conn.close()
        return jsonify({'success': 'Cài đặt đã được lưu thành công!'})
    
    # Lấy cài đặt hiện tại
    settings = {}
    rows = conn.execute('SELECT key, value FROM settings WHERE key IN ("checkin_morning", "checkout_afternoon")').fetchall()
    for row in rows:
        settings[row['key']] = row['value']
    conn.close()
    
    return render_template('admin_settings.html', settings=settings)

# Route: Cài đặt giao diện
@app.route('/admin_ui_settings')
@login_required
def admin_ui_settings():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    return render_template('admin_ui_settings.html')

# Route: Quản lý đào tạo
@app.route('/admin/training', methods=['GET', 'POST'])
@login_required
def admin_training():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        duration = request.form['duration']
        
        conn.execute('''
            INSERT INTO training_courses (title, description, duration, created_at)
            VALUES (?, ?, ?, ?)
        ''', (title, description, duration, datetime.now()))
        conn.commit()
        flash('Tạo khóa học thành công!', 'success')
    
    courses = conn.execute('SELECT * FROM training_courses').fetchall()
    conn.close()
    
    return render_template('admin_training.html', courses=courses)

# Route: Quản lý khảo sát
@app.route('/admin/survey')
@login_required
def admin_survey():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    surveys = conn.execute('SELECT s.*, u.full_name FROM surveys s JOIN users u ON s.user_id = u.id WHERE u.is_active = 1').fetchall()
    conn.close()
    
    return render_template('admin_survey.html', surveys=surveys)

# Route: Quản lý hiệu suất
@app.route('/admin/performance')
@login_required
def admin_performance():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    return render_template('admin_performance.html')

# Route: Quản lý lịch làm việc hybrid
@app.route('/admin/hybrid_schedule', methods=['GET', 'POST'])
@login_required
def admin_hybrid_schedule():
    if current_user.role != 'admin':
        flash('Bạn không có quyền truy cập!', 'danger')
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        schedule_id = request.form['schedule_id']
        status = request.form['status']
        
        conn.execute('UPDATE hybrid_schedules SET status = ? WHERE id = ?', (status, schedule_id))
        conn.commit()
        flash('Cập nhật trạng thái lịch làm việc thành công!', 'success')
    
    schedules = conn.execute('''
        SELECT hs.*, u.full_name 
        FROM hybrid_schedules hs 
        JOIN users u ON hs.user_id = u.id
        WHERE u.is_active = 1
    ''').fetchall()
    conn.close()
    
    return render_template('admin_hybrid_schedule.html', schedules=schedules)

# Route: Phục vụ ảnh chấm công
@app.route('/photos/<filename>')
def serve_photo(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    init_db()
    app.run(debug=True)