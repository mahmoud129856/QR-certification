from flask import Flask, render_template, jsonify
from datetime import datetime, timedelta
import random
import time

app = Flask(__name__)

# Mock data - in production, this would come from database
def get_mock_data():
    teams = [
        {"name": "Team Alpha 🚀", "score": 125, "members": 5, "ideas": 4},
        {"name": "Team Beta ⚡", "score": 118, "members": 4, "ideas": 3},
        {"name": "Team Gamma 🔥", "score": 102, "members": 5, "ideas": 2},
        {"name": "Team Delta 💎", "score": 89, "members": 4, "ideas": 2},
        {"name": "Team Echo 🌟", "score": 76, "members": 3, "ideas": 1},
        {"name": "Team Zeta 🦄", "score": 65, "members": 5, "ideas": 3}
    ]
    
    mvp = {
        "name": "Ahmed Al-Mansoori",
        "team": "Team Alpha 🚀",
        "score": 48
    }
    
    news_items = [
        "🚀 Team Alpha just submitted their 4th killer idea!",
        "⚡ Team Beta says they discovered the winning formula",
        "🔥 Team Gamma is on fire with their latest prototype",
        "💎 Team Delta celebrating their first 100 points!",
        "🌟 Team Echo just recruited a coding wizard",
        "🦄 Team Zeta is still brainstorming... 5th coffee incoming",
        "Team Alpha spotted doing victory dance already 😂",
        "Breaking: Team Beta printer just ran out of paper"
    ]
    
    # Competition end time (2 hours from now for demo)
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