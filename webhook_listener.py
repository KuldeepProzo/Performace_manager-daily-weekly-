from flask import Flask, request
import os
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    subprocess.Popen(["/root/hubspot_performance_manager/Performace_manager-daily-weekly-/deploy.sh"])
    return "Webhook received", 200

app.run(host='0.0.0.0', port=5001)