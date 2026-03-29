import RPi.GPIO as GPIO
from RPLCD.gpio import CharLCD
import serial
import time
import threading
import sqlite3
from influxdb import InfluxDBClient
from flask import Flask, render_template, jsonify, request
import glob
from datetime import datetime

# --- CONFIGURATION GLOBALE ---
app = Flask(__name__)
lcd_lock = threading.Lock()
lcd = None 

# Ajout des chronomètres (time_1, time_2, time_3)
etat_parking = {
    "1": "INCONNU", "2": "INCONNU", "3": "INCONNU", 
    "time_1": time.time(), "time_2": time.time(), "time_3": time.time(),
    "last_update": "Jamais", 
    "entree": "Fermée",
    "statut_global": "OUVERT"
}
DB_PATH = "parking.db"

# --- INIT BDD SQLITE ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS utilisateurs (uid TEXT PRIMARY KEY, nom TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS acces_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, uid TEXT, nom TEXT, statut TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- CONNEXIONS USB ---
ser_lora = None
ser_barriere = None

def detecter_ports_usb():
    global ser_lora, ser_barriere
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    for port in ports:
        try:
            s = serial.Serial(port, 115200, timeout=2)
            time.sleep(2)
            for _ in range(10):
                if s.in_waiting > 0:
                    line = s.readline().decode('utf-8', errors='ignore').strip()
                    if "BARRIERE" in line: ser_barriere = s; break
                    elif "LoRa" in line or "Passerelle" in line: ser_lora = s; break
            if ser_lora is None and ser_barriere is None: s.close()
        except: pass

if ser_lora is None:
    try: ser_lora = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    except: pass
if ser_barriere is None:
    try: ser_barriere = serial.Serial('/dev/ttyUSB1', 115200, timeout=1)
    except: pass

# --- BDD INFLUXDB ---
try:
    db_client = InfluxDBClient(host='localhost', port=8086)
    db_client.switch_database('parking_db')
except Exception as e: print(f"⚠️ Erreur InfluxDB: {e}")

# --- INIT LCD ---
try:
    GPIO.setwarnings(False); GPIO.setmode(GPIO.BCM)
    GPIO.setup(18, GPIO.OUT); pwm = GPIO.PWM(18, 1000); pwm.start(50)
    lcd = CharLCD(cols=16, rows=2, pin_rs=25, pin_e=24, pins_data=[23, 17, 27, 22], numbering_mode=GPIO.BCM)
except: pass


def reset_lcd_hardware():
    global lcd
    with lcd_lock:
        try:
            print("[SYSTEME] Reset PROFOND de l'écran LCD en cours...")
            
            # 1. On tente de fermer l'ancienne connexion proprement
            if lcd:
                try: lcd.close(clear=True)
                except: pass
                
            # 2. On coupe tout
            GPIO.setmode(GPIO.BCM)
            GPIO.cleanup([25, 24, 23, 17, 27, 22])
            
            # Pause BEAUCOUP plus longue pour vider l'électricité statique des fils
            time.sleep(1.5) 

            # 3. On recrée l'objet (ça renvoie la séquence d'initialisation 4-bits)
            GPIO.setmode(GPIO.BCM)
            lcd = CharLCD(cols=16, rows=2, pin_rs=25, pin_e=24, pins_data=[23, 17, 27, 22], numbering_mode=GPIO.BCM)
            
            time.sleep(0.5)
            lcd.clear()
            lcd.write_string("REBOOT OK...")
            time.sleep(1)
            print("[SYSTEME] LCD Réinitialisé !")
        except Exception as e:
            print(f"Erreur Reset LCD: {e}")



# --- THREAD 1 : LORA (MAJ des chronomètres) ---
def thread_lora_loop():
    while True:
        if ser_lora and ser_lora.in_waiting > 0:
            try:
                line = ser_lora.readline().decode('utf-8', errors='ignore').strip()
                if line.startswith("PYTHON_DATA:"):
                    donnees = line.replace("PYTHON_DATA:", "")
                    places = donnees.split('|')
                    for p in places:
                        id_place, etat = p.split(':')
                        etat_str = "OCCUPE" if etat == "O" else "LIBRE"
                        
                        # Si l'état change, on reset le chronomètre de cette place
                        if etat_parking[id_place] != etat_str:
                            etat_parking[id_place] = etat_str
                            etat_parking[f"time_{id_place}"] = time.time()
                            save_influx(id_place, 1 if etat == "O" else 0, etat_str)
                            
                    etat_parking["last_update"] = datetime.now().strftime("%H:%M:%S")
                    update_lcd()
            except: pass
        time.sleep(0.1)

# --- THREAD 2 : BARRIERE ---
def thread_barriere_loop():
    while True:
        if ser_barriere and ser_barriere.in_waiting > 0:
            try:
                line = ser_barriere.readline().decode('utf-8', errors='ignore').strip()
                if "UID=" in line: verifier_badge(line.split("=")[1])
                elif "BARRIERE_FERMEE" in line: 
                    etat_parking["entree"] = "Fermée"
                    update_lcd()
            except: pass
        time.sleep(0.1)

def verifier_badge(uid):
    uid_propre = uid.strip()
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT nom FROM utilisateurs WHERE uid = ?", (uid_propre,))
        user = cursor.fetchone()
        nom_user = user[0] if user else "Inconnu"
        
        if etat_parking["statut_global"] == "FERME":
            statut_log = "REFUSÉ (Parking Fermé)"
            action_lcd = "PARKING FERME"
        elif user:
            statut_log = "AUTORISÉ"
            action_lcd = f"BONJOUR\n{nom_user}"
            ser_barriere.write(b"OUVRIR\n")
            etat_parking["entree"] = "Ouverte"
        else:
            statut_log = "REFUSÉ (Badge Inconnu)"
            action_lcd = "ACCES REFUSE"

        cursor.execute("INSERT INTO acces_logs (timestamp, uid, nom, statut) VALUES (?, ?, ?, ?)", (date_now, uid_propre, nom_user, statut_log))
        conn.commit()
        conn.close()

        with lcd_lock:
            try:
                if lcd:
                    lcd.clear()
                    lcd.write_string(action_lcd)
            except: pass
            
        time.sleep(3)
        update_lcd()
    except: pass

def update_lcd():
    with lcd_lock:
        try:
            if lcd:
                nb_libres = sum(1 for i in ["1", "2", "3"] if etat_parking[i] == "LIBRE")
                lcd.clear()
                lcd.write_string(f"Parking {etat_parking['statut_global']}")
                lcd.cursor_pos = (1, 0)
                lcd.write_string(f"Places dispo: {nb_libres}")
        except: pass

def save_influx(id_place, val_num, msg):
    try: db_client.write_points([{"measurement": "occupation", "tags": {"place": f"P{id_place}"}, "fields": {"etat": val_num, "msg": msg}}])
    except: pass

# ==========================================
# 🌐 ROUTES FLASK
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data')
def api_data():
    places_occupees = sum(1 for i in ["1", "2", "3"] if etat_parking[i] == "OCCUPE")
    pourcentage = int((places_occupees / 3.0) * 100)
    data = etat_parking.copy()
    data["stats"] = f"{pourcentage}% Occupé"
    
    # Calcul du "Temps Occupé" pour l'interface web
    for i in ["1", "2", "3"]:
        duree_sec = int(time.time() - etat_parking[f"time_{i}"])
        m, s = divmod(duree_sec, 60)
        data[f"duree_{i}"] = f"{m}m {s}s"
        
    return jsonify(data)

@app.route('/api/logs')
def api_logs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, uid, nom, statut FROM acces_logs ORDER BY id DESC LIMIT 8")
    logs = cursor.fetchall()
    conn.close()
    return jsonify(logs)

@app.route('/api/stats_globales')
def api_stats_globales():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM acces_logs")
    total = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM acces_logs WHERE statut LIKE '%AUTORISÉ%'")
    auth = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM acces_logs WHERE statut LIKE '%REFUSÉ%'")
    refus = cursor.fetchone()[0]
    conn.close()
    return jsonify({"total": total, "auth": auth, "refus": refus})

@app.route('/api/toggle_status', methods=['POST'])
def toggle_status():
    etat_parking["statut_global"] = "FERME" if etat_parking["statut_global"] == "OUVERT" else "OUVERT"
    update_lcd()
    return jsonify({"success": True})

@app.route('/api/reset_lcd', methods=['POST'])
def api_reset_lcd():
    reset_lcd_hardware()
    update_lcd()
    return jsonify({"success": True})

@app.route('/api/add_user', methods=['POST'])
def add_user():
    data = request.json
    uid = data.get('uid').strip().upper()
    nom = data.get('nom').strip()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO utilisateurs (uid, nom) VALUES (?, ?)", (uid, nom))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

if __name__ == '__main__':
    app.config['JSON_AS_ASCII'] = False
    update_lcd()
    detecter_ports_usb()
    threading.Thread(target=thread_lora_loop, daemon=True).start()
    threading.Thread(target=thread_barriere_loop, daemon=True).start()
    print("--- SYSTEME OK : PRET POUR LA SOUTENANCE ---")
    app.run(host='0.0.0.0', port=5000)