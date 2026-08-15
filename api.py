import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= KONFIGURASI =================
BOT_TOKEN = "8277021258:AAFqskqr4gbVTOluxRfnFD06nVozjlXxas8"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ================= FUNGSI TELEGRAM =================
def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    return requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def send_document(chat_id, file_bytes, filename):
    url = f"{TELEGRAM_API}/sendDocument"
    return requests.post(url, data={"chat_id": chat_id}, files={"document": (filename, file_bytes)})

# ================= FUNGSI KONVERSI =================
def parse_accs(file_content):
    accounts = []
    for line in file_content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        uid, pwd = line.split(":", 1)
        if uid.strip().isdigit() and pwd.strip():
            accounts.append({
                "uid": uid.strip(),
                "password": pwd.strip()
            })
    return accounts

def build_guest_dat(uid, password):
    return {
        "guest_account_info": {
            "com.garena.msdk.guest_password": password,
            "com.garena.msdk.guest_uid": uid
        }
    }

# ================= WEBHOOK HANDLER =================
@app.route('/', methods=['GET'])
def home():
    return "Bot is Online! 🚀", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        if not update or 'message' not in update:
            return "OK", 200
        
        message = update['message']
        chat_id = message['chat']['id']
        
        if 'document' in message:
            doc = message['document']
            file_id = doc['file_id']
            file_name = doc['file_name']
            
            if file_name != "accs.json":
                send_message(chat_id, "❌ Kirim file dengan nama `accs.json`!")
                return "OK", 200
            
            file_url = f"{TELEGRAM_API}/getFile?file_id={file_id}"
            file_resp = requests.get(file_url).json()
            if not file_resp.get('ok'):
                send_message(chat_id, "❌ Gagal mengambil file.")
                return "OK", 200
            
            file_path = file_resp['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            file_content = requests.get(download_url).text
            
            accounts = parse_accs(file_content)
            if not accounts:
                send_message(chat_id, "❌ Tidak ada akun valid di `accs.json`.")
                return "OK", 200
            
            send_message(chat_id, f"✅ Ditemukan {len(accounts)} akun. Mengirim file satu per satu...")
            
            for acc in accounts:
                data = build_guest_dat(acc["uid"], acc["password"])
                json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
                file_bytes = json_str.encode("utf-8")
                send_document(chat_id, file_bytes, f"guest100067.dat")
            
            return "OK", 200
        
        elif 'text' in message:
            if message['text'] == '/start':
                send_message(chat_id, "🔥 **Guest Converter Bot** 🔥\n\nKirim file `accs.json` (format `UID:PASSWORD`) dan saya akan mengubahnya jadi file `guest100067.dat` satu per satu.")
            else:
                send_message(chat_id, "📤 Silakan kirim file `accs.json`.")
        
        return "OK", 200
    
    except Exception as e:
        print("Error:", e)
        return "OK", 200

# ================= MAIN =================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
