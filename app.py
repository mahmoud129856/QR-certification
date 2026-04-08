from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import random

app = Flask(__name__)

def get_mock_data():
    teams = [
        {"name": "فريق ألفا 🚀", "score": 125, "members": 5, "ideas": 4},
        {"name": "فريق بيتا ⚡", "score": 118, "members": 4, "ideas": 3},
        {"name": "فريق غاما 🔥", "score": 102, "members": 5, "ideas": 2},
        {"name": "فريق دلتا 💎", "score": 89, "members": 4, "ideas": 2},
        {"name": "فريق إيكو 🌟", "score": 76, "members": 3, "ideas": 1},
        {"name": "فريق زيتا 🦄", "score": 65, "members": 5, "ideas": 3}
    ]
    
    mvp = {
        "name": "أحمد المنصوري",
        "team": "فريق ألفا 🚀",
        "score": 48
    }
    
    news_items = [
        "🚀 فريق ألفا قدم فكرتهم الرابعة الرهيبة!",
        "⚡ فريق بيتا يقولون اكتشفوا الفكرة الفائزة",
        "🔥 فريق غاما يشتعلون بأحدث نموذجهم",
        "💎 فريق دلتا يحتفلون بأول 100 نقطة!",
        "🌟 فريق إيكو جندوا ساحر البرمجة",
        "🦄  ممم م مم م م   م   ممممم م ممم مم م م مم فريق زيتا ما زالوا يفكرون... القهوة الخامسة قادمة",
        "فريق ألفا يرقصون رقصة النصر بالفعل 😂",
        "كسر: طابعة فريق بيتا نفد الحبر"
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