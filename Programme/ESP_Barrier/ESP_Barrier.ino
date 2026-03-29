#include <SPI.h>
#include <MFRC522.h>
#include <ESP32Servo.h>

// ==========================================
// 📍 PINOUT (TON PCB BARRIÈRE)
// ==========================================
// --- RFID RC522 ---
// SDA (SS) -> 21
// SCK      -> 18
// MOSI     -> 23
// MISO     -> 19
// RST      -> 22
#define SS_PIN  21
#define RST_PIN 22
#define LED_ROUGE 25
#define LED_VERTE 26
#define SERVO_PIN 13
#define TRIG_PIN 33
#define ECHO_PIN 32

MFRC522 rfid(SS_PIN, RST_PIN);
Servo barriere;

bool barriereOuverte = false;

void setup() {
  Serial.begin(115200);
  
  // Cette ligne magique permet au Raspberry Pi de détecter qui est branché sur quel port USB !
  Serial.println("DEVICE_TYPE=BARRIERE"); 

  // Config LEDs
  pinMode(LED_ROUGE, OUTPUT);
  pinMode(LED_VERTE, OUTPUT);
  digitalWrite(LED_ROUGE, HIGH);
  digitalWrite(LED_VERTE, LOW);

  // Config HC-SR04
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);

  // Config Servomoteur
  ESP32PWM::allocateTimer(0);
  barriere.setPeriodHertz(50);
  barriere.attach(SERVO_PIN, 500, 2400);
  barriere.write(0); // Fermée par défaut

  // Config RFID
  SPI.begin();
  rfid.PCD_Init();
}

void loop() {
  // ----------------------------------------------------
  // 1. ÉCOUTE DU RASPBERRY PI (A-t-on reçu l'ordre d'ouvrir ?)
  // ----------------------------------------------------
  if (Serial.available() > 0) {
    String ordre = Serial.readStringUntil('\n');
    ordre.trim(); // Enlever les espaces invisibles
    
    if (ordre == "OUVRIR" && !barriereOuverte) {
      sequenceOuverture();
    }
  }

  // ----------------------------------------------------
  // 2. ÉCOUTE DU LECTEUR RFID (Y a-t-il un badge ?)
  // ----------------------------------------------------
  if (!barriereOuverte && rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    
    String uid_lu = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      uid_lu += String(rfid.uid.uidByte[i] < 0x10 ? " 0" : " ");
      uid_lu += String(rfid.uid.uidByte[i], HEX);
    }
    uid_lu.toUpperCase();
    
    // On envoie l'UID au Raspberry Pi pour qu'il vérifie dans la BDD
    Serial.print("UID=");
    Serial.println(uid_lu);
    
    rfid.PICC_HaltA(); // On met le badge en pause pour ne pas spammer
    delay(1000);       // Petite pause anti-rebond
  }
}

// ==========================================
// ⚙️ FONCTION D'OUVERTURE AVEC SÉCURITÉ ULTRASON
// ==========================================
void sequenceOuverture() {
  barriereOuverte = true;
  digitalWrite(LED_ROUGE, LOW);
  digitalWrite(LED_VERTE, HIGH);
  
  barriere.write(90); // Lève la barrière
  delay(3000);        // Laisse passer la voiture pendant 3 sec
  
  // --- SECURITE ANTI-FERMETURE (HC-SR04) ---
  while (voitureSousBarriere()) {
    // Tant qu'une voiture est détectée sous la barrière (distance < 10cm), on attend !
    delay(500); 
  }
  
  // La voie est libre, on ferme
  barriere.write(0);
  digitalWrite(LED_VERTE, LOW);
  digitalWrite(LED_ROUGE, HIGH);
  barriereOuverte = false;
  
  // On prévient le RPi que c'est terminé
  Serial.println("BARRIERE_FERMEE");
}

// ==========================================
// 📏 FONCTION DE MESURE DE DISTANCE (AVEC DEBUG)
// ==========================================
bool voitureSousBarriere() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  
  long duree = pulseIn(ECHO_PIN, HIGH, 30000); // Timeout 30ms
  
  if (duree == 0) {
    Serial.println("[HC-SR04] Erreur : Aucune reponse (Distance = 0)");
    return false; 
  }
  
  float distance = (duree / 2.0) * 0.0343;
  
  // Affichage dans la console pour comprendre ce que voit le capteur
  Serial.print("[HC-SR04] Distance mesuree : ");
  Serial.print(distance);
  Serial.println(" cm");
  
  // J'ai monté le seuil à 15 cm pour tester facilement avec la main
  if (distance > 1.0 && distance < 8.0) {
    Serial.println(">>> OBSTACLE DETECTE ! Je bloque la fermeture.");
    return true; 
  }
  
  return false;
}