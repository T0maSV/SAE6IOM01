#include <SPI.h>
#include <LoRa.h>

// ==========================================
// ⚙️ CONFIGURATION LORA (Heltec V2)
// ==========================================
#define LORA_SS    18
#define LORA_RST   14
#define LORA_DI0   26
#define LORA_FREQ  870300000 // 870.3 MHz (Doit être identique au Parking)
#define SECRET_KEY "SECURE_PARK|"

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== DEMARRAGE ESP PASSERELLE ===");

  // Initialisation LoRa
  SPI.begin(5, 19, 27, 18);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DI0);
  
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("ERREUR : Module LoRa introuvable !");
    while (1); // On bloque ici si erreur
  }
  
  Serial.println("Passerelle prete et securisee.");
  Serial.println("En ecoute sur 870.3 MHz...");
  Serial.println("=================================");
}

void loop() {
  // On vérifie si un paquet LoRa est arrivé
  int packetSize = LoRa.parsePacket();
  
  if (packetSize) {
    String messageRecu = "";
    
    // On lit tout le contenu du paquet
    while (LoRa.available()) {
      messageRecu += (char)LoRa.read();
    }

    // ==========================================
    // 🛡️ FILTRE DE SECURITE CYBER
    // ==========================================
    if (messageRecu.startsWith(SECRET_KEY)) {
      
      // On découpe le message pour enlever la clé secrète.
      // Si on reçoit "SECURE_PARK|1:O|2:L|3:L", on ne garde que "1:O|2:L|3:L"
      String donneesUtiles = messageRecu.substring(String(SECRET_KEY).length());
      
      // ----------------------------------------------------
      // 🚀 ENVOI AU RASPBERRY PI (Format strict)
      // ----------------------------------------------------
      Serial.print("PYTHON_DATA:"); 
      Serial.println(donneesUtiles);
      
      // Petit affichage de debug pour toi (et pour le jury : montrer le RSSI c'est la classe)
      Serial.print("[DEBUG] Message valide traite avec succes (RSSI: ");
      Serial.print(LoRa.packetRssi());
      Serial.println(" dBm)");
      
    } else {
      // Quelqu'un essaie d'envoyer des données sur notre fréquence !
      Serial.println("[ALERTE INTRUSION] Message ignore (Cle de securite invalide).");
    }
  }
}