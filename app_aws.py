from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import boto3
import uuid
import base64
from werkzeug.utils import secure_filename
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'yojeong_secret_key'

# --- AWS Configuration ---
REGION = 'us-east-1'
dynamodb = boto3.resource('dynamodb', region_name=REGION)

# DynamoDB Tables
users_table = dynamodb.Table('Users')
admin_table = dynamodb.Table('AdminUsers')
bookings_table = dynamodb.Table('Bookings')
sessions_table = dynamodb.Table('Sessions')
feedback_table = dynamodb.Table('Feedback')
files_table = dynamodb.Table('Files')

MAX_FILE_SIZE = 100 * 1024  # 100KB

# --- Helper Functions ---
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Main Routes ---
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    confirm = request.form.get('confirm')

    if password != confirm:
        flash("Passwords don't match!")
        return redirect(url_for('login'))

    response = users_table.get_item(Key={'email': email})
    if 'Item' in response:
        flash("Account already exists!")
        return redirect(url_for('login'))

    users_table.put_item(Item={
        'email': email,
        'name': name,
        'password': password,
        'role': 'user'
    })

    flash("Account created! Please login.")
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        response = users_table.get_item(Key={'email': email})
        if 'Item' in response and response['Item']['password'] == password:
            session['user'] = response['Item']['name']
            session['email'] = email
            session['role'] = 'user'
            return redirect(url_for('dashboard'))

        flash("Invalid user credentials.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    email = session['email']

    # ✅ FIXED: Use .eq() instead of ==
    bookings_resp = bookings_table.scan(
        FilterExpression=Attr('user').eq(email)
    )
    feedbacks_resp = feedback_table.scan(
        FilterExpression=Attr('user_email').eq(email)
    )

    return render_template(
        'dashboard.html',
        name=session['user'],
        my_bookings=bookings_resp.get('Items', []),
        my_feedbacks=feedbacks_resp.get('Items', [])
    )

@app.route('/book', methods=['POST'])
def book_retouch():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    file = request.files.get('file')
    if file:
        filename = secure_filename(file.filename)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        if file_size > MAX_FILE_SIZE:
            flash("File too large! Max size is 100KB")
            return redirect(url_for('dashboard'))

        if not allowed_file(filename):
            flash("Invalid file type! Allowed: jpg, png, gif, pdf")
            return redirect(url_for('dashboard'))

        file_data = file.read()
        file_b64 = base64.b64encode(file_data).decode('utf-8')
        file_id = str(uuid.uuid4())[:8]
        booking_id = str(uuid.uuid4())[:8]

        try:
            files_table.put_item(Item={
                'id': file_id,
                'filename': filename,
                'data': file_b64,
                'file_type': filename.rsplit('.', 1)[1].lower(),
                'size': file_size,
                'user': session['email'],
                'created_at': datetime.now().isoformat()
            })

            bookings_table.put_item(Item={
                'id': booking_id,
                'user': session['email'],
                'user_name': session['user'],
                'service': f"Retouch: {request.form.get('service')}",
                'filename': filename,
                'file_id': file_id,
                'status': 'Pending',
                'created_at': datetime.now().isoformat()
            })

            flash("File uploaded successfully!")
        except ClientError as e:
            flash(f"Upload failed: {str(e)}")

    return redirect(url_for('dashboard'))

@app.route('/download/<file_id>')
def download_file(file_id):
    if session.get('role') not in ['user', 'admin']:
        return redirect(url_for('login'))

    try:
        resp = files_table.get_item(Key={'id': file_id})
        if 'Item' not in resp:
            flash("File not found!")
            return redirect(url_for('dashboard'))

        item = resp['Item']
        file_data = base64.b64decode(item['data'])

        from flask import send_file
        from io import BytesIO
        return send_file(
            BytesIO(file_data),
            as_attachment=True,
            download_name=item['filename']
        )
    except Exception as e:
        flash(f"Download failed: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/book_session', methods=['POST'])
def book_session():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    date_str = request.form.get('session_date')
    today_str = datetime.now().strftime('%Y-%m-%d')

    if date_str < today_str:
        flash("Cannot book session for past dates.")
        return redirect(url_for('dashboard'))

    session_id = str(uuid.uuid4())[:8]
    sessions_table.put_item(Item={
        'id': session_id,
        'user': session['email'],
        'user_name': session['user'],
        'service': f"{request.form.get('session_type')} (with {request.form.get('photographer')})",
        'date': date_str,
        'time': request.form.get('session_time'),
        'status': 'Pending',
        'created_at': datetime.now().isoformat()
    })

    flash("Session booked successfully!")
    return redirect(url_for('dashboard'))

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if session.get('role') != 'user':
        return redirect(url_for('login'))

    feedback_id = str(uuid.uuid4())[:8]
    feedback_table.put_item(Item={
        'id': feedback_id,
        'user_name': session['user'],
        'user_email': session['email'],
        'service': request.form.get('service'),
        'rating': int(request.form.get('rating')),
        'comment': request.form.get('comment'),
        'created_at': datetime.now().isoformat()
    })

    flash("Thank you for your feedback!")
    return redirect(url_for('dashboard'))

# --- Admin Routes ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        response = admin_table.get_item(Key={'email': email})
        if 'Item' in response and response['Item']['password'] == password:
            session['user'] = response['Item']['name']
            session['email'] = email
            session['role'] = 'admin'
            return redirect(url_for('admin_panel'))

        flash("Access Denied: Admin credentials invalid.")
    return render_template('admin_login.html')

@app.route('/admin')
def admin_panel():
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))

    users = users_table.scan().get('Items', [])
    bookings = bookings_table.scan().get('Items', [])
    sessions = sessions_table.scan().get('Items', [])
    feedbacks = feedback_table.scan().get('Items', [])

    users_dict = {u['email']: {'name': u['name']} for u in users}

    return render_template(
        'admin.html',
        users=users_dict,
        bookings=bookings,
        sessions=sessions,
        feedbacks=feedbacks
    )

@app.route('/admin/approve/<booking_id>')
def approve(booking_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    bookings_table.update_item(
        Key={'id': booking_id},
        UpdateExpression="set #st = :s",
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={':s': 'Confirmed'}
    )
    return redirect(url_for('admin_panel'))

@app.route('/admin/reject/<booking_id>')
def reject(booking_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    bookings_table.update_item(
        Key={'id': booking_id},
        UpdateExpression="set #st = :s",
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={':s': 'Cancelled'}
    )
    return redirect(url_for('admin_panel'))

@app.route('/admin/confirm_session/<session_id>')
def confirm_session(session_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    today_str = datetime.now().strftime('%Y-%m-%d')
    resp = sessions_table.get_item(Key={'id': session_id})

    if 'Item' in resp:
        status = 'Today' if resp['Item']['date'] == today_str else 'Upcoming'
        sessions_table.update_item(
            Key={'id': session_id},
            UpdateExpression="set #st = :s",
            ExpressionAttributeNames={'#st': 'status'},
            ExpressionAttributeValues={':s': status}
        )
    return redirect(url_for('admin_panel'))

@app.route('/admin/complete_session/<session_id>')
def complete_session(session_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    sessions_table.update_item(
        Key={'id': session_id},
        UpdateExpression="set #st = :s",
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={':s': 'Completed'}
    )
    return redirect(url_for('admin_panel'))

@app.route('/admin/cancel_session/<session_id>')
def cancel_session(session_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    sessions_table.update_item(
        Key={'id': session_id},
        UpdateExpression="set #st = :s",
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={':s': 'Cancelled'}
    )
    return redirect(url_for('admin_panel'))

@app.route('/edit_user', methods=['POST'])
def edit_user():
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    old_email = request.form['old_email']
    new_name = request.form['new_name']
    new_email = request.form['new_email']

    res = users_table.get_item(Key={'email': old_email})
    if 'Item' in res:
        item = res['Item']
        users_table.delete_item(Key={'email': old_email})
        item['email'] = new_email
        item['name'] = new_name
        users_table.put_item(Item=item)

    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_user/<email>')
def delete_user(email):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    users_table.delete_item(Key={'email': email})
    return redirect(url_for('admin_panel'))

@app.route('/admin/delete_feedback/<feedback_id>')
def delete_feedback(feedback_id):
    if session.get('role') != 'admin':
        return "Unauthorized", 403

    feedback_table.delete_item(Key={'id': feedback_id})
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
