# Performance Manager – Deployment Setup

This guide explains how to set up and run the **Performance Manager** project on a server, including a **Flask-based webhook listener** to automatically pull changes from GitHub.

## 1. Install Dependencies

Update and install required packages:

```bash
sudo apt update
sudo apt install git -y
sudo apt install python3-pip -y
sudo apt install python3.12-venv -y
sudo apt install python3-flask -y
```

## 2. Configure GitHub SSH Access

Generate a new SSH key:

```bash
ssh-keygen -t ed25519 -C "surendra.kumar@prozo.com"
```

Follow the prompts, then add the generated **public key** (from `~/.ssh/id_ed25519.pub`) to your **GitHub account** under:
**Settings → SSH and GPG keys → New SSH key**.

## 3. Clone the Repository

```bash
git clone git@github.com:KuldeepProzo/Performace_manager-daily-weekly-.git
```

## 4. Create and Activate Virtual Environment

Inside the cloned project folder:

```bash
python3 -m venv hpm
source hpm/bin/activate
pip install -r requirements.txt
```

## 5. Run the Application

```bash
python3 app.py
```

## 6. Webhook Listener for GitHub Changes

### Create `deploy.sh`

```bash
sudo nano /root/hubspot_performance_manager/Performace_manager-daily-weekly-/deploy.sh
```

Paste:

```bash
#!/bin/bash
cd /root/hubspot_performance_manager/Performace_manager-daily-weekly- || exit
git pull origin main
```

Make it executable:

```bash
chmod +x /root/deploy.sh
```

### Create `webhook_listener.py`

```python
from flask import Flask, request
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    subprocess.Popen(["/root/hubspot_performance_manager/Performace_manager-daily-weekly-/deploy.sh"])
    return "Webhook received", 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001)
```

### Run the Webhook Listener

```bash
python3 webhook_listener.py
```

## 7. Notes

* The webhook listener runs on **port 5001** and should be exposed to GitHub via **Settings → Webhooks**.
* Ensure `/root/deploy.sh` starts with a **shebang** (`#!/bin/bash`) and is executable.
* For production, use `gunicorn` or run inside `tmux`/`screen` to keep it alive.
* If using a firewall, open port `5001`:

```bash
sudo ufw allow 5001
sudo ufw allow 5000
```
