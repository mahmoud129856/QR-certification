from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
ADMIN_PASSWORD_HASH = generate_password_hash('admin123')

# ========== إعداد الاتصال بـ MongoDB Atlas ==========
MONGO_URI = os.environ.get('MONGO_URI')
if not MONGO_URI:
    raise Exception("متغير البيئة MONGO_URI غير موجود. الرجاء إضافته في Vercel.")

# محاولة الاتصال بقاعدة البيانات مع معالجة الأخطاء
try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)  # مهلة 5 ثواني
    # التحقق من الاتصال
    client.admin.command('ping')
    print("✅ تم الاتصال بـ MongoDB بنجاح")
except (ConnectionFailure, ServerSelectionTimeoutError) as e:
    print(f"❌ فشل الاتصال بـ MongoDB: {e}")
    # في حالة فشل الاتصال، نستخدم متغير وهمي لتجنب الكراش (لكن سيظهر خطأ عند الاستخدام)
    client = None

# تحديد اسم قاعدة البيانات (يجب أن يكون موجوداً في URI أو نضعه هنا)
if client:
    # استخراج اسم قاعدة البيانات من URI إن أمكن، أو استخدام الافتراضي
    db_name = "competition_db"
    db = client[db_name]
else:
    db = None

# ========== دوال مساعدة للتعامل مع MongoDB ==========
def get_data_from_db():
    """جلب جميع البيانات من MongoDB"""
    if db is None:
        # بيانات وهمية للاختبار في حالة فشل الاتصال
        return {
            "teams": [],
            "mvp": {"name": "", "team": "", "score": 0},
            "news_items": []
        }
    try:
        teams = list(db.teams.find({}, {'_id': False}))
        mvp = db.mvp.find_one({}, {'_id': False}) or {"name": "", "team": "", "score": 0}
        news_items = [news['text'] for news in db.news.find({}, {'_id': False})]
        return {
            "teams": teams,
            "mvp": mvp,
            "news_items": news_items
        }
    except Exception as e:
        print(f"خطأ في قراءة البيانات: {e}")
        return {"teams": [], "mvp": {"name": "", "team": "", "score": 0}, "news_items": []}

def save_data_to_db(data):
    """حفظ البيانات إلى MongoDB"""
    if db is None:
        raise Exception("قاعدة البيانات غير متصلة")
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
        print(f"خطأ في الحفظ: {e}")
        raise e

def create_default_data():
    """إنشاء بيانات افتراضية إذا كانت قاعدة البيانات فارغة"""
    if db is None:
        return
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
            print("✅ تم إنشاء البيانات الافتراضية")
    except Exception as e:
        print(f"خطأ في إنشاء البيانات الافتراضية: {e}")

# استدعاء إنشاء البيانات الافتراضية
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