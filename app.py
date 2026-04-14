from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import os
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
ADMIN_PASSWORD_HASH = generate_password_hash('admin0000')

# ========== إعداد Supabase ==========
SUPABASE_URL = "https://lgpepojvzrgxmnzslvdc.supabase.co"
SUPABASE_KEY = "sb_publishable_7OCn_h7exZqDAr3ldlc3hQ_mWWUjxoU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== دوال التعامل مع Supabase ==========
def get_data_from_supabase():
    """جلب البيانات من جداول Supabase"""
    try:
        teams_response = supabase.table('teams').select('*').execute()
        teams = teams_response.data
        
        mvp_response = supabase.table('mvp').select('*').limit(1).execute()
        mvp = mvp_response.data[0] if mvp_response.data else {"name": "", "team": "", "score": 0}
        
        news_response = supabase.table('news_items').select('text').order('created_at', desc=False).execute()
        news_items = [item['text'] for item in news_response.data]
        
        return {"teams": teams, "mvp": mvp, "news_items": news_items}
    except Exception as e:
        print(f"خطأ في قراءة Supabase: {e}")
        return {"teams": [], "mvp": {"name": "", "team": "", "score": 0}, "news_items": []}

def save_data_to_supabase(data):
    """حفظ البيانات إلى Supabase - النسخة المحسنة"""
    try:
        print("💾 بدء الحفظ...")
        
        # حذف البيانات القديمة
        supabase.table('teams').delete().neq('id', 0).execute()
        supabase.table('mvp').delete().neq('id', 0).execute()
        supabase.table('news_items').delete().neq('id', 0).execute()
        
        # إدراج الفرق
        if data.get('teams'):
            for team in data['teams']:
                supabase.table('teams').insert(team).execute()
        
        # إدراج MVP
        if data.get('mvp'):
            supabase.table('mvp').insert(data['mvp']).execute()
        
        # إدراج الأخبار
        if data.get('news_items'):
            for news_text in data['news_items']:
                supabase.table('news_items').insert({"text": news_text}).execute()
        
        print("🎉 الحفظ نجح!")
        return True
    except Exception as e:
        print(f"❌ خطأ في الحفظ: {e}")
        raise e

def check_and_create_default_data():
    """التحقق من البيانات الافتراضية - النسخة الآمنة لـ Vercel"""
    try:
        # فحص سريع - لو مفيش فرق خالص
        count_response = supabase.table('teams').select('id', count='exact').execute()
        if count_response.count == 0:
            print("⚠️ الجداول فارغة - إنشاء بيانات افتراضية...")
            default_data = {
                "teams": [
                    {"name": "كفر الباز", "score": 125, "members": 5, "ideas": 4},
                    {"name": "الاسطي عقله ب 1000", "score": 118, "members": 4, "ideas": 3},
                    {"name": "هبده مرتده", "score": 102, "members": 5, "ideas": 2}
                ],
                "mvp": {"name": "تامر الجيار", "team": "فريق الاسطي", "score": 30},
                "news_items": [
                    "حالة هلع في التيم بسبب فويسات سليمان",
                    "تسريب لتيم الصفحه .. محمود طه يقترب من حسم افضل تيم ليدر!!!"
                ]
            }
            save_data_to_supabase(default_data)
        else:
            print(f"✅ البيانات موجودة ({count_response.count} فريق)")
    except Exception as e:
        print(f"خطأ في الفحص: {e}")

# ✅ تشغيل الفحص مرة واحدة عند أول طلب (آمن لـ Vercel)
@app.before_request
def before_request():
    if not hasattr(g, 'data_initialized'):
        check_and_create_default_data()
        g.data_initialized = True

from flask import g  # ✅ إضافة هذا السطر

# ========== Routes ==========
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    data = get_data_from_supabase()
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
    
    data = get_data_from_supabase()
    return render_template('admin_dashboard.html', data=data)

@app.route('/admin/save', methods=['POST'])
def save_data():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "غير مصرّح"}), 401
    
    try:
        data = request.json
        save_data_to_supabase(data)
        return jsonify({"success": True, "message": "تم الحفظ بنجاح! 🎉"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/admin/reset-password', methods=['POST'])
def reset_password():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "غير مصرّح"}), 401
    
    global ADMIN_PASSWORD_HASH
    new_password = request.json.get('password', 'admin1111')
    ADMIN_PASSWORD_HASH = generate_password_hash(new_password)
    return jsonify({"success": True, "message": "تم تغيير كلمة السر!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)