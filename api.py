import os
import json
import requests
import time
import threading
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= KONFIGURASI =================
BOT_TOKEN = "8277021258:AAFqskqr4gbVTOluxRfnFD06nVozjlXxas8"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Variabel untuk cek status first deploy (supaya gak spam kirim pesan setiap request)
FIRST_RUN = True

# ================= FUNGSI TELEGRAM =================
def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    return requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

def send_document(chat_id, file_bytes, filename):
    url = f"{TELEGRAM_API}/sendDocument"
    try:
        return requests.post(url, data={"chat_id": chat_id}, files={"document": (filename, file_bytes)}, timeout=30)
    except:
        return None

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

# ================= PROSES BACKGROUND (SUPAYA GAK MUNTAH ULANG) =================
def process_and_send_files(chat_id, accounts):
    send_message(chat_id, f"✅ Ditemukan {len(accounts)} akun. Memproses di background...")
    
    batch_size = 5
    total_sent = 0
    
    for i, acc in enumerate(accounts):
        data = build_guest_dat(acc["uid"], acc["password"])
        json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
        file_bytes = json_str.encode("utf-8")
        
        try:
            send_document(chat_id, file_bytes, f"guest100067.dat")
            total_sent += 1
        except:
            pass
        
        if (i + 1) % batch_size == 0 and (i + 1) < len(accounts):
            time.sleep(2)
    
    send_message(chat_id, f"✅ Selesai! Total {total_sent} file `guest100067.dat` berhasil dikirim.")

# ================= WEBHOOK HANDLER =================
@app.route('/', methods=['GET'])
def home():
    return "BOT SUDAH ONLINE", 200

# 🔥 Tambahan endpoint untuk kirim pesan /start otomatis
@app.route('/start', methods=['GET'])
def start_bot():
    return "Bot Telegram sudah online, silakan ketik /start di Telegram!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    global FIRST_RUN
    try:
        update = request.get_json()
        if not update or 'message' not in update:
            return "OK", 200
        
        message = update['message']
        chat_id = message['chat']['id']
        
        # 🔥 Saat pertama kali bot menerima request, kirim sambutan
        if FIRST_RUN:
            send_message(chat_id, "🔥 **BOT SUDAH ONLINE** 🔥\n\nSilakan kirim file `accs.json` (format `UID:PASSWORD`) untuk mengubahnya jadi file `guest100067.dat`.\n\n*Tolong ketik /start untuk melihat petunjuk.*")
            FIRST_RUN = False
        
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
            
            # 🔥 Jalankan di background thread
            threading.Thread(target=process_and_send_files, args=(chat_id, accounts)).start()
            
            return "OK", 200
        
        elif 'text' in message:
            if message['text'] == '/start':
                send_message(chat_id, "🔥 **Guest Converter Bot** 🔥\n\nKirim file `accs.json` (format `UID:PASSWORD`) dan saya akan mengubahnya jadi file `guest100067.dat` satu per satu.\n\nBOT SUDAH ONLINE ✅\n\nSilakan kirim file Anda.")
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
