from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, User, PasswordResetToken
import threading
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


auth_bp = Blueprint('auth', __name__)

def send_async_email(app, recipient, subject, html_content):
    with app.app_context():
        try:
            print("=== EMAIL THREAD STARTED (GMAIL MODE) ===")
            
            sender_email = app.config.get('MAIL_USERNAME')
            sender_password = app.config.get('MAIL_PASSWORD')
            
            if not sender_email or not sender_password:
                print("=== EMAIL FAILED: MAIL_USERNAME or MAIL_PASSWORD not set in .env ===")
                return

            print(f"Sender: {sender_email}")
            print(f"Recipient: {recipient}")

            msg = MIMEMultipart()
            msg['From'] = f"ShopByGold <{sender_email}>"
            msg['To'] = recipient
            msg['Subject'] = subject
            
            msg.attach(MIMEText(html_content, "html"))

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient, msg.as_string())
            server.quit()
            
            print(f"=== EMAIL SENT to {recipient} ===")
                
        except Exception as e:
            print(f"=== EMAIL FAILED: {e} ===")
            print(traceback.format_exc())


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'msg': 'Missing username, email, or password'}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'msg': 'Email already exists'}), 400
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'msg': 'Username already exists'}), 400

    hashed = current_app.bcrypt.generate_password_hash(data['password']).decode('utf-8')
    
    user = User(
        username=data['username'],
        email=data['email'], 
        password_hash=hashed,
        role=data.get('role', 'customer')
    )
    
    db.session.add(user)
    db.session.commit()
    
    access_token = create_access_token(identity=str(user.id))
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    user = User.query.filter(
        (User.email == data.get('email')) | (User.username == data.get('username'))
    ).first()

    if user and current_app.bcrypt.check_password_hash(user.password_hash, data['password']):
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict()
        })
    
    return jsonify({'msg': 'Invalid credentials'}), 401

# FORGOT PASSWORD - FIXED FOR GMAIL
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json() or {}
    email = data.get('email')
    
    if not email:
        return jsonify({'msg': 'If that email exists, a reset link has been sent'}), 200

    try:
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({'msg': 'If that email exists, a reset link has been sent'}), 200
        
        PasswordResetToken.query.filter_by(user_id=user.id).delete()
        
        reset_token = PasswordResetToken(user_id=user.id)
        db.session.add(reset_token)
        db.session.commit()
        
        frontend_url = current_app.config.get('FRONTEND_URL') or 'http://127.0.0.1:5500'
        reset_link = f'{frontend_url}/reset-password.html?token={reset_token.token}'

        html = f'''
        <div style="font-family: Arial; max-width: 600px; margin: auto; background: white; padding: 30px; border-radius: 10px; border:1px solid #eee;">
            <h2 style="color: #eab308;">ShopByGold</h2>
            <h2>Password Reset Request</h2>
            <p>Hi {user.username},</p>
            <p>Click the link below to reset your password. Link expires in 1 hour:</p>
            <a href="{reset_link}" style="background:#eab308;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;display:inline-block;">Reset Password</a>
            <p style="margin-top:15px;">Or copy: {reset_link}</p>
        </div>
        '''

        threading.Thread(
            target=send_async_email, 
            args=(current_app._get_current_object(), user.email, "ShopByGold - Password Reset", html),
            daemon=True
        ).start()
        
    except Exception as e:
        print(f'Forgot password error: {e}')
        print(traceback.format_exc())
    
    return jsonify({'msg': 'If that email exists, a reset link has been sent'}), 200

# RESET PASSWORD
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')
    
    if not token or not new_password:
        return jsonify({'msg': 'Token and password required'}), 400
    
    if len(new_password) < 6:
        return jsonify({'msg': 'Password must be at least 6 characters'}), 400
    
    reset_token = PasswordResetToken.query.filter_by(token=token).first()
    
    if not reset_token or not reset_token.is_valid():
        return jsonify({'msg': 'Invalid or expired token'}), 400
    
    user = reset_token.user
    user.password_hash = current_app.bcrypt.generate_password_hash(new_password).decode('utf-8')
    reset_token.used = True
    
    db.session.commit()
    
    return jsonify({'msg': 'Password reset successful. You can now login.'}), 200