from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from supabase import create_client, Client

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
ADMIN_PASSWORD_HASH = generate_password_hash('admin0000')

# ========== إعداد Supabase ==========
SUPABASE_URL = "https://lgpepojvzrgxmnzslvdc.supabase.co"
SUPABASE_KEY = "sb_publishable_7OCn_h7exZqDAr3ldlc3hQ_mWWUjxoU"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ========== جلب البيانات ==========
def get_data_from_supabase():
    try:
        teams = supabase.table('teams').select('*').execute().data

        mvp_data = supabase.table('mvp').select('*').limit(1).execute().data
        mvp = mvp_data[0] if mvp_data else {"name": "", "team": "", "score": 0}

        news_data = supabase.table('news_items').select('text').order('created_at').execute().data
        news_items = [item['text'] for item in news_data]

        return {"teams": teams, "mvp": mvp, "news_items": news_items}

    except Exception as e:
        print(f"خطأ في القراءة: {e}")
        return {"teams": [], "mvp": {"name": "", "team": "", "score": 0}, "news_items": []}


# ========== حفظ البيانات (بدون مسح) ==========
def save_data_to_supabase(data):
    try:
        # ===== الفرق =====
        if data.get('teams'):
            for team in data['teams']:
                supabase.table('teams').upsert(team).execute()

        # ===== MVP =====
        if data.get('mvp'):
            supabase.table('mvp').upsert(data['mvp']).execute()

        # ===== الأخبار =====
        if data.get('news_items'):
            # نحذف الأخبار القديمة فقط (اختياري)
            supabase.table('news_items').delete().neq('id', 0).execute()

            for news_text in data['news_items']:
                supabase.table('news_items').insert({"text": news_text}).execute()

        return True

    except Exception as e:
        print(f"خطأ في الحفظ: {e}")
        raise e


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


# ========== Admin ==========
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form['password']

        if check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('تم تسجيل الدخول بنجاح! 🎉', 'success')
            return redirect(url_for('admin_panel'))
        else:
            flash('كلمة السر غلط ❌', 'error')

    if session.get('admin_logged_in'):
        return redirect(url_for('admin_panel'))

    return render_template('admin_login.html')


@app.route('/admin/dashboard')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    data = get_data_from_supabase()
    return render_template('admin_dashboard.html', data=data)


@app.route('/admin/save', methods=['POST'])
def save_data():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "غير مصرح"}), 401

    try:
        data = request.json
        save_data_to_supabase(data)

        return jsonify({
            "success": True,
            "message": "تم الحفظ بنجاح 🎉"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('تم تسجيل الخروج', 'info')
    return redirect(url_for('admin_login'))


@app.route('/admin/reset-password', methods=['POST'])
def reset_password():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "غير مصرح"}), 401

    global ADMIN_PASSWORD_HASH
    new_password = request.json.get('password', 'admin1111')
    ADMIN_PASSWORD_HASH = generate_password_hash(new_password)

    return jsonify({"success": True, "message": "تم تغيير الباسورد"})


# ❌ مهم: مفيش create_default_data هنا خالص

if __name__ == '__main__':
    app.run(debug=True)