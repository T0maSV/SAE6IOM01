import sqlite3
from influxdb import InfluxDBClient

print("--- RÉINITIALISATION DES BASES DE DONNÉES ---")

# ==========================================
# 1. BASE SQLITE (Badges RFID)
# ==========================================
try:
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()
    
    # On supprime l'ancienne table si elle existe
    cursor.execute('DROP TABLE IF EXISTS utilisateurs')
    
    # On recrée la table
    cursor.execute('''
        CREATE TABLE utilisateurs (
            uid TEXT PRIMARY KEY,
            nom TEXT NOT NULL
        )
    ''')
    
    # On ajoute un badge de test (Tu mettras ton vrai UID plus tard)
    cursor.execute("INSERT INTO utilisateurs (uid, nom) VALUES ('A1 B2 C3 D4', 'Professeur/Jury')")
    
    conn.commit()
    conn.close()
    print("✅ SQLite   : 'parking.db' recréée avec succès (Table 'utilisateurs' prête).")
except Exception as e:
    print(f"❌ Erreur SQLite : {e}")

# ==========================================
# 2. BASE INFLUXDB (Historique d'occupation)
# ==========================================
try:
    client = InfluxDBClient(host='localhost', port=8086)
    
    # On détruit l'ancienne base et on la recrée vide
    client.drop_database('parking_db')
    client.create_database('parking_db')
    
    print("✅ InfluxDB : Base 'parking_db' nettoyée et recréée avec succès.")
except Exception as e:
    print(f"❌ Erreur InfluxDB : Vérifie que le service InfluxDB tourne bien sur le Raspberry ({e})")

print("---------------------------------------------")