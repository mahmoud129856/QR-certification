from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

ADMIN_PASSWORD_HASH = generate_password_hash('admin1111')

def create_default_data():
    default_data = {
        "teams": [
            {"name": "كفر الباز", "score": 125, "members": 5, "ideas": 4},
            {"name": "الاسطي عقله ب 1000", "score": 118, "members": 4, "ideas": 3},
            {"name": "هبده مرتده", "score": 102, "members": 5, "ideas": 2}
        ],
        "mvp": {
            "name": "تامر الجيار",
            "team": "فريق الاسطي",
            "score": 30
        },
        "news_items": [
            "حالة هلع في التيم بسبب فويسات سليمان",
            "تسريب لتيم الصفحه .. محمود طه يقترب من حسم افضل تيم ليدر!!!"
        ]
    }
    os.makedirs('static', exist_ok=True)
    with open('static/data.json', 'w', encoding='utf-8') as f:
        json.dump(default_data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    try:
        with open('static/data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        end_time = datetime.now() + timedelta(hours=2, minutes=30)
        data['end_time'] = end_time.isoformat()
        data['news'] = data['news_items']
        return jsonify(data)
    except FileNotFoundError:
        create_default_data()
        return api_data()

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']
        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('تم تسجيل الدخول بنجاح! 🎉', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('كلمة السر خاطئة! 🚫', 'error')
    
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_panel'))
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('تم تسجيل الخروج بنجاح', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    try:
        with open('static/data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    except:
        create_default_data()
        with open('static/data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
    
    return render_template('admin_dashboard.html', data=data)

@app.route('/admin/save', methods=['POST'])
def save_data():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "غير مصرّح"}), 401
    
    try:
        data = request.json
        with open('static/data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True, "message": "تم الحفظ بنجاح! 🎉"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/reset-password', methods=['POST'])
def reset_password():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "غير مصرّح"}), 401
    
    global ADMIN_PASSWORD_HASH
    new_password = request.json.get('password', 'admin123')
    ADMIN_PASSWORD_HASH = generate_password_hash(new_password)
    return jsonify({"success": True, "message": "تم تغيير كلمة السر!"})

if __name__ == '__main__':
    create_default_data()
    app.run(debug=True, port=5000)