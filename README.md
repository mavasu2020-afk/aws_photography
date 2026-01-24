📸 Photoshop Booking App (Flask)

A beginner-friendly Photoshop Service Booking Web App built using Python Flask, with support for local SQLite and cloud MongoDB/AWS deployment.
Perfect for learning Flask basics such as routing, templates, forms, sessions, and databases.

🚀 Features

User Registration & Login/Logout

Session Management

Photoshop Service Booking

Local SQLite Database (app.py)

Cloud-ready MongoDB + AWS (app_aws.py)

Beginner-friendly code structure

🧰 Technologies Used

Python 3

Flask

SQLite (for local version)

MongoDB (for cloud/AWS version)

HTML + Jinja2 Templates

AWS EC2 & SNS (optional notifications)

📁 Project Structure
photoshopbooking/
│
├── app.py # Local version (SQLite)
├── app_aws.py # AWS-ready version (MongoDB + optional SNS)
├── database.db # Local SQLite database (for app.py)
│
├── templates/
│ ├── login.html
│ ├── register.html
│ ├── dashboard.html
│ └── booking.html
│
└── static/ # CSS, JS, images, etc.
⚡ Local Setup (app.py)

Clone the repository:

git clone <repo_url>
cd photoshopbooking

Install dependencies:

pip install flask werkzeug

Run the app:

python app.py

Open your browser at:

http://127.0.0.1:5000
☁️ AWS Setup (app_aws.py)

This version is ready for cloud deployment:

Uses MongoDB Atlas or any cloud-hosted MongoDB

Supports AWS EC2 deployment

Optional SNS notifications for booking alerts

Steps:

Upload project to your EC2 instance.

Install dependencies:

pip install flask pymongo werkzeug boto3

Set environment variables on EC2:

export MONGO_URI="your_mongodb_connection_string"
export SECRET_KEY="your_secret_key"

Run the app:

python app_aws.py

Access your app at:

http://<EC2_PUBLIC_IP>:5000/
📝 Notes

Ensure your templates/ and static/ folders are in the same directory as app.py or app_aws.py to prevent TemplateNotFound errors.

Use environment variables for sensitive information when deploying on AWS.

You can enable AWS SNS notifications in app_aws.py to send alerts for new bookings.

🔗 References

Flask Documentation

MongoDB Atlas

AWS EC2

AWS SNS
