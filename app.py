from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
import sys

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
ADMIN_PASSWORD_HASH = generate_password_hash('admin123')

# ========== إعداد MongoDB ==========
MONGO_URI = os.environ.get('MONGO_URI')
mongo_available = False
db = None

if MONGO_URI:
    try:
        from pymongo import MongoClient
        from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')  # اختبار الاتصال
        db = client.get_database("competition_db")
        mongo_available = True
        print("✅ تم الاتصال بـ MongoDB بنجاح", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ فشل الاتصال بـ MongoDB: {e}", file=sys.stderr)
else:
    print("⚠️ متغير MONGO_URI غير موجود - لن تُحفظ البيانات", file=sys.stderr)

# ========== دوال البيانات ==========
def get_data_from_db():
    """جلب البيانات من MongoDB أو إرجاع بيانات فارغة"""
    if mongo_available and db is not None:
        try:
            teams = list(db.teams.find({}, {'_id': False}))
            mvp = db.mvp.find_one({}, {'_id': False}) or {"name": "", "team": "", "score": 0}
            news_items = [news['text'] for news in db.news.find({}, {'_id': False})]
            return {"teams": teams, "mvp": mvp, "news_items": news_items}
        except Exception as e:
            print(f"خطأ في قراءة MongoDB: {e}", file=sys.stderr)
    # بيانات وهمية (فارغة) في حالة عدم توفر قاعدة البيانات
    return {"teams": [], "mvp": {"name": "", "team": "", "score": 0}, "news_items": []}

def save_data_to_db(data):
    """حفظ البيانات إلى MongoDB"""
    if not mongo_available or db is None:
        raise Exception("⚠️ MongoDB غير متاح - البيانات لم تُحفظ. تأكد من إعداد MONGO_URI في Vercel.")
    try:
        db.teams.drop()
        db.mvp.drop()
        db.news.drop()
        if data.get('teams'):
            db.teams.insert_many(data['teams'])
        if data.get('mvp'):
            db.mvp.insert_one(data['mvp'])
        if data.get('news_items'):
            db.news.insert_many([{'text': news} for news in data['news_items']])
        return True
    except Exception as e:
        print(f"خطأ في حفظ MongoDB: {e}", file=sys.stderr)
        raise e

def create_default_data():
    """إنشاء بيانات افتراضية إذا كانت قاعدة البيانات فارغة"""
    if mongo_available and db is not None:
        try:
            if db.teams.count_documents({}) == 0:
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
                save_data_to_db(default_data)
                print("✅ تم إنشاء البيانات الافتراضية", file=sys.stderr)
        except Exception as e:
            print(f"خطأ في إنشاء البيانات الافتراضية: {e}", file=sys.stderr)

create_default_data()

# ========== Routes ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    data = get_data_from_db()
    end_time = datetime.now() + timedelta(hours=2, minutes=30)
    data['end_time'] = end_time.isoformat()
    data['news'] = data['news_items']
    return jsonify(data)

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
    data = get_data_from_db()
    return render_template('admin_dashboard.html', data=data)

@app.route('/admin/save', methods=['POST'])
def save_data():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "غير مصرّح"}), 401
    try:
        data = request.json
        save_data_to_db(data)
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
    app.run(debug=True, port=5000)