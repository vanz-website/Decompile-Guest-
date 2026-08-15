import os
import json
import requests
import time
import threading
from flask import Flask, request

app = Flask(__name__)

# ================= KONFIGURASI =================
BOT_TOKEN = "8277021258:AAFqskqr4gbVTOluxRfnFD06nVozjlXxas8"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ================= FUNGSI TELEGRAM =================
def send_message(chat_id, text):
    url = f"{TELEGRAM_API}/sendMessage"
    try:
        return requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"[ERROR] Gagal kirim pesan: {e}")
        return None

def send_document(chat_id, file_bytes, filename="guest100067.dat", caption=""):
    url = f"{TELEGRAM_API}/sendDocument"
    try:
        files = {"document": (filename, file_bytes, "application/octet-stream")}
        data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
        resp = requests.post(url, data=data, files=files, timeout=30)
        return resp.json()
    except Exception as e:
        print(f"[ERROR] Gagal kirim file: {e}")
        return None

# ================= FUNGSI KONVERSI =================
def parse_accs(file_content):
    """Mendukung format UID:PASSWORD (per baris) dan format JSON Array"""
    accounts = []
    
    # 1. Parse format teks UID:PASSWORD (per baris)
    for line in file_content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        parts = line.split(":", 1)
        uid = str(parts[0].strip())
        pwd = str(parts[1].strip())
        if uid and pwd:
            accounts.append({"uid": uid, "password": pwd})
            
    # 2. Jika bukan format teks, coba parse sebagai JSON
    if not accounts:
        try:
            json_data = json.loads(file_content)
            if isinstance(json_data, list):
                for item in json_data:
                    uid = str(item.get("uid") or "").strip()
                    pwd = str(item.get("password") or "").strip()
                    if uid and pwd:
                        accounts.append({"uid": uid, "password": pwd})
        except Exception:
            pass
            
    return accounts

def build_guest_dat_bytes(uid: str, password: str) -> bytes:
    """Menghasilkan byte JSON persis dengan struktur guest_account_info"""
    data = {
        "guest_account_info": {
            "com.garena.msdk.guest_password": str(password),
            "com.garena.msdk.guest_uid": str(uid)
        }
    }
    # Diproses rapat tanpa spasi tambahan agar struktur JSON identik
    return json.dumps(data, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

# ================= PROSES BACKGROUND =================
def process_and_send_files(chat_id, accounts):
    send_message(chat_id, f"✅ Ditemukan **{len(accounts)}** akun.\n⏳ Memproses dan mengirim file `guest100067.dat`...")
    
    total_sent = 0
    total_accs = len(accounts)
    
    for i, acc in enumerate(accounts, 1):
        # Generate isi file sesuai UID dan Password
        file_bytes = build_guest_dat_bytes(acc["uid"], acc["password"])
        
        # Caption penanda akun agar lu tau urutan filenya di Telegram
        caption = f"📄 Akun [{i}/{total_accs}]\n🆔 UID: `{acc['uid']}`"
        
        # Nama file dikunci mati menjadi "guest100067.dat" untuk setiap dokumen
        res = send_document(chat_id, file_bytes, filename="guest100067.dat", caption=caption)
        
        if res and res.get("ok"):
            total_sent += 1
        else:
            print(f"[WARNING] Gagal mengirim file ke-{i} (UID: {acc['uid']})")
        
        # Delay 0.5 detik untuk menghindari Rate Limit (Error 429 Telegram)
        time.sleep(0.5)
    
    send_message(chat_id, f"🎉 **SELESAI!**\nTotal **{total_sent}/{total_accs}** file `guest100067.dat` berhasil dikirim.")

# ================= WEBHOOK HANDLER =================
@app.route('/', methods=['GET'])
def home():
    return "BOT SUDAH ONLINE", 200

@app.route('/start', methods=['GET'])
def start_bot():
    return "Bot Telegram sudah online!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json(force=True, silent=True)
        if not update or 'message' not in update:
            return "OK", 200
        
        message = update['message']
        chat_id = message['chat']['id']
        
        if 'document' in message:
            doc = message['document']
            file_id = doc['file_id']
            
            file_url = f"{TELEGRAM_API}/getFile?file_id={file_id}"
            file_resp = requests.get(file_url, timeout=15).json()
            
            if not file_resp.get('ok'):
                send_message(chat_id, "❌ Gagal mengunduh file dari Telegram.")
                return "OK", 200
            
            file_path = file_resp['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            file_content = requests.get(download_url, timeout=30).text
            
            accounts = parse_accs(file_content)
            if not accounts:
                send_message(chat_id, "❌ Tidak ada akun valid yang ditemukan dalam file!")
                return "OK", 200
            
            # Jalankan pengiriman file di background thread
            threading.Thread(target=process_and_send_files, args=(chat_id, accounts)).start()
            
            return "OK", 200
        
        elif 'text' in message:
            text = message['text']
            if text == '/start':
                send_message(chat_id, "🔥 **Guest Converter Bot** 🔥\n\nKirim file daftar akun (`accs.json` / `.txt`), bot akan langsung memproses tiap akun jadi file `guest100067.dat` secara otomatis.")
            else:
                send_message(chat_id, "📤 Silakan kirim file daftar akun Anda.")
        
        return "OK", 200
    
    except Exception as e:
        print("Webhook Error:", e)
        return "OK", 200

# ================= MAIN =================
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
