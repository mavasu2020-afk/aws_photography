import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "yojeong_secret_key_2026"

# --- CONFIGURATION ---
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DUMMY DATABASE ---
users = {
    "admin@yojeong.com": {"name": "Admin User", "password": "adminposthost", "role": "admin"},
    "client@test.com": {"name": "Jane Doe", "password": "password123", "role": "user"}
}

bookings = []         # Retouching requests (Uploads)
session_bookings = []  # Photography dates (Calendar)
feedbacks = []         # User reviews

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    email = request.form.get('email')
    password = request.form.get('password')
    if email and email not in users:
        users[email] = {"name": name, "password": password, "role": "user"}
    return redirect(url_for('login'))

# --- SEPARATED LOGIN: USER ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users.get(email)
        
        # Check if user exists and is NOT an admin
        if user and user['password'] == password and user['role'] == 'user':
            session.update({'user': user['name'], 'role': user['role'], 'email': email})
            return redirect(url_for('dashboard'))
        
        return "Invalid User Credentials. <a href='/login'>Try Again</a>"
    return render_template('login.html')

# --- SEPARATED LOGIN: ADMIN ---
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = users.get(email)
        
        # Check if user exists and IS an admin
        if user and user['password'] == password and user['role'] == 'admin':
            session.update({'user': user['name'], 'role': user['role'], 'email': email})
            return redirect(url_for('admin_panel'))
            
        return "Invalid Admin Credentials. <a href='/admin/login'>Try Again</a>"
    return render_template('admin_login.html') # You will need to create this template

@app.route('/dashboard')
def dashboard():
    if 'user' in session and session.get('role') == 'user':
        email = session['email']
        my_data = [b for b in bookings if b['user'] == email] + \
                  [s for s in session_bookings if s['user'] == email]
        my_feedbacks = [f for f in feedbacks if f['user_email'] == email]
        return render_template('dashboard.html', 
                               name=session['user'], 
                               my_bookings=my_data, 
                               my_feedbacks=my_feedbacks)
    return redirect(url_for('login'))

@app.route('/book', methods=['POST'])
def book_retouch():
    if 'user' not in session: return redirect(url_for('login'))
    file = request.files.get('file')
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        bookings.append({
            "id": len(bookings) + 1, 
            "user": session['email'],
            "service": f"Retouch: {request.form.get('service')}", 
            "filename": filename, 
            "status": "Pending"
        })
    return redirect(url_for('dashboard'))

@app.route('/book_session', methods=['POST'])
def book_session():
    if 'user' not in session: return redirect(url_for('login'))
    
    date_str = request.form.get('session_date') 
    today_str = datetime.now().strftime('%Y-%m-%d')
    if date_str < today_str:
        return f"Error: You cannot book a session for {date_str}. <a href='/dashboard'>Go Back</a>"

    event_type = request.form.get('session_type')
    photographer = request.form.get('photographer')
    time = request.form.get('session_time')

    session_bookings.append({
        "id": len(session_bookings) + 1000, 
        "user": session['email'],
        "user_name": session['user'], 
        "service": f"{event_type} (with {photographer})", 
        "date": date_str, 
        "time": time,
        "status": "Pending"
    })
    return redirect(url_for('dashboard'))

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if 'email' not in session: return redirect(url_for('login'))
    feedback_data = {
        "id": str(uuid.uuid4())[:8],
        "user_name": session.get('user'), 
        "user_email": session.get('email'),
        "service": request.form.get('service'),
        "rating": int(request.form.get('rating')),
        "comment": request.form.get('comment')
    }
    feedbacks.append(feedback_data)
    return redirect(url_for('dashboard'))

# --- ADMIN ACTIONS ---

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin': 
        return redirect(url_for('admin_login'))
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    for s in session_bookings:
        if s['status'] in ['Upcoming', 'Today']:
            if s['date'] == today_str:
                s['status'] = 'Today'
            else:
                s['status'] = 'Upcoming'

    return render_template('admin.html', 
                           users=users, 
                           bookings=bookings, 
                           sessions=session_bookings,
                           feedbacks=feedbacks)

@app.route('/admin/approve/<int:id>')
def approve(id):
    if session.get('role') != 'admin': return "Unauthorized", 403
    for b in bookings:
        if b['id'] == id:
            b['status'] = 'Confirmed'
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<int:id>')
def reject(id):
    if session.get('role') != 'admin': return "Unauthorized", 403
    for b in bookings:
        if b['id'] == id:
            b['status'] = 'Cancelled'
    return redirect(url_for('admin_panel'))

@app.route('/admin/confirm_session/<int:id>')
def confirm_session(id):
    if session.get('role') != 'admin': return "Unauthorized", 403
    today_str = datetime.now().strftime('%Y-%m-%d')
    for s in session_bookings:
        if s['id'] == id:
            if s['date'] == today_str:
                s['status'] = 'Today'
            else:
                s['status'] = 'Upcoming'
    return redirect(url_for('admin_panel'))

@app.route('/admin/complete_session/<int:id>')
def complete_session(id):
    if session.get('role') != 'admin': return "Unauthorized", 403
    for s in session_bookings:
        if s['id'] == id:
            s['status'] = 'Completed'
    return redirect(url_for('admin_panel'))

@app.route('/admin/cancel_session/<int:id>')
def cancel_session(id):
    if session.get('role') != 'admin': return "Unauthorized", 403
    for s in session_bookings:
        if s['id'] == id:
            s['status'] = 'Cancelled'
    return redirect(url_for('admin_panel'))

# --- DATABASE MANAGEMENT ---

@app.route('/edit_user', methods=['POST'])
def edit_user():
    if session.get('role') != 'admin': return "Unauthorized", 403
    old_email = request.form.get('old_email')
    new_name = request.form.get('new_name')
    new_email = request.form.get('new_email')
    if old_email in users:
        data = users.pop(old_email)
        data['name'] = new_name
        users[new_email] = data
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<email>')
def delete_user(email):
    if session.get('role') != 'admin': return "Unauthorized", 403
    if email in users:
        users.pop(email)
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_feedback/<id>')
def delete_feedback(id):
    if session.get('role') != 'admin': return "Unauthorized", 403
    global feedbacks
    feedbacks = [f for f in feedbacks if f['id'] != id]
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)    
