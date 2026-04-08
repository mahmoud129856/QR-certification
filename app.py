from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import random

app = Flask(__name__)

def get_mock_data():
    teams = [
        {"name": "كفر الباز ", "score": 125, "members": 5, "ideas": 4},
        {"name": "الاسطي عقله ب 1000", "score": 118, "members": 4, "ideas": 3},
        {"name": "هبده مرتده", "score": 102, "members": 5, "ideas": 2},
        {"name": "مش فايقين بس موجودين", "score": 89, "members": 4, "ideas": 2},
        {"name": "الجيار القدوة", "score": 76, "members": 3, "ideas": 1}
       
    ]
    
    mvp = {
        "name": "تامر الجيار",
        "team": "فريق الاسطي",
        "score": 30
    }
    
    news_items = [
        "حالة هلع في التيم بسبب فويسات سليمان",
        "بعد مرور نصف الديدلاين شباب فريق هبده مرتده يبتدون توزيع المهام",
        "تسريب لتيم الصفحه .. محمود طه يقترب من حسم افضل تيم ليدر!!!",
        "تسريبات تتهم احد افراد فريق الاسطي عقله ب 1000 بسرقة فكرة من جوجل",
        "فريق مش فايقين بس موجودين يعلنون عن فكرة جديدة في اللحظات الأخيرة",
        "تسريب: فريق الجيار القدوة يخطط لعمل فيديوهات ترويجية على تيك توك",
        "جمله غريبة من احد افراد فريق كفر الباز تثير الجدل في التيم",
        
    ]
    
    end_time = datetime.now() + timedelta(hours=2, minutes=30)
    
    return {
        "teams": teams,
        "mvp": mvp,
        "news": news_items,
        "end_time": end_time.isoformat()
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    data = get_mock_data()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True, port=5000)