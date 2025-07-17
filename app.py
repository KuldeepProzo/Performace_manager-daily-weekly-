from flask import Flask
import subprocess
import threading

app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Prozo Performance Manager is Live."

@app.route('/run/daily')
def run_daily():
    threading.Thread(target=lambda: subprocess.run(["python", "daily_main.py"])).start()
    return "🚀 Daily performance job triggered."

@app.route('/run/weekly')
def run_weekly():
    threading.Thread(target=lambda: subprocess.run(["python", "weekly_main.py"])).start()
    return "🚀 Weekly performance job triggered."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
