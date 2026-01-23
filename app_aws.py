from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import boto3
import uuid
from werkzeug.utils import secure_filename
from boto3.dynamodb.conditions import Key, Attr
from botocore.exceptions import ClientError

app = Flask(__name__)
app.secret_key = 'yojeong_secret_key'

# --- AWS Configuration ---
REGION = 'us-east-1' 
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

# DynamoDB Tables
users_table = dynamodb.Table('Users')
admin_table = dynamodb.Table('AdminUsers')
bookings_table = dynamodb.Table('Bookings')      # For Edit Requests
sessions_table = dynamodb.Table('Sessions')      # For Photography Sessions
feedback_table = dynamodb.Table('Feedback')

# SNS Topic ARN
SNS_TOPIC_ARN = 'arn:aws:sns:us-east-1:604665149129:aws_capstone_topic' 

# File Upload Config
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- Helper Functions ---
def send_notification(subject, message):
    try:
        sns.publish(TopicArn=SNS_TOPIC_ARN, Subject=subject, Message=message)
    except ClientError as e:
        print(f"SNS Error: {e}")

# --- User Routes ---

@app.route('/signup', methods=['POST'])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    
    # Check if user exists
    if 'Item' in users_table.get_item(Key={'email': email}):
        flash("Account already exists!")
        return redirect(url_for('login'))
    
    # Add User with role
    users_table.put_item(Item={'email': email, 'name': name, 'password': password, 'role': 'user'})
    send_notification("New Studio Member", f"{name} ({email}) just joined Yojeong Photograph.")
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        response = users_table.get_item(Key={'email': email})
        if 'Item' in response and response['Item']['password'] == password:
            session['user'] = email
            session['role'] = 'user'
            return redirect(url_for('dashboard'))
        flash("Invalid user credentials.")
    return render_template('login.html')

# --- Admin Routes ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        response = admin_table.get_item(Key={'email': email})
        if 'Item' in response and response['Item']['password'] == password:
            session['user'] = email
            session['role'] = 'admin'
            return redirect(url_for('admin_panel'))
        flash("Access Denied: Admin credentials invalid.")
    return render_template('admin_login.html')

@app.route('/admin/panel')
def admin_panel():
    if session.get('role') != 'admin':
        return redirect(url_for('admin_login'))
    
    # Fetch data from DynamoDB
    users = users_table.scan().get('Items', [])
    bookings = bookings_table.scan().get('Items', [])
    sessions = sessions_table.scan().get('Items', [])
    feedbacks = feedback_table.scan().get('Items', [])
    
    # Format users for the template (email as key)
    users_dict = {u['email']: {'name': u['name']} for u in users}
    
    return render_template('admin.html', 
                           users=users_dict, 
                           bookings=bookings, 
                           sessions=sessions, 
                           feedbacks=feedbacks)

# --- Admin Action Routes ---

@app.route('/admin/approve/<booking_id>')
def approve_booking(booking_id):
    if session.get('role') == 'admin':
        bookings_table.update_item(
            Key={'id': booking_id},
            UpdateExpression="set #st = :s",
            ExpressionAttributeNames={'#st': 'status'},
            ExpressionAttributeValues={':s': 'Approved'}
        )
        send_notification("Booking Approved", f"Booking ID {booking_id} has been approved.")
    return redirect(url_for('admin_panel'))

@app.route('/edit_user', methods=['POST'])
def edit_user():
    if session.get('role') == 'admin':
        old_email = request.form['old_email']
        new_name = request.form['new_name']
        new_email = request.form['new_email']
        
        # In DynamoDB, you can't change a Key. We must delete and recreate if email changes.
        res = users_table.get_item(Key={'email': old_email})
        if 'Item' in res:
            item = res['Item']
            users_table.delete_item(Key={'email': old_email})
            item['email'] = new_email
            item['name'] = new_name
            users_table.put_item(Item=item)
            
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)