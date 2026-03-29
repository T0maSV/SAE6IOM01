#include <SPI.h>
#include <LoRa.h>

// ==========================================
// ⚙️ CONFIGURATION LORA (Heltec V2)
// ==========================================
#define LORA_SS    18
#define LORA_RST   14
#define LORA_DI0   26
#define LORA_FREQ  870300000 // 870.3 MHz
#define SECRET_KEY "SECURE_PARK|" // Notre "sécurité du pauvre"

// ==========================================
// 📍 CONFIGURATION DES BROCHES (GPIO)
// ==========================================
// Les tableaux permettent de gérer les 3 places d'un coup avec une boucle !
// Ordre : [Place 1 (IR), Place 2 (Hall), Place 3 (Reed)]
const int pinCapteurs[3] = {32, 22, 25};
const int pinLedRouge[3] = {13, 23, 17};
const int pinLedVerte[3] = {21,  2, 12};

// ==========================================
// ⏱️ GESTION DU TEMPS ET DES ETATS (Manœuvres)
// ==========================================
const unsigned long DELAI_MANOEUVRE = 5000; // 5 secondes de confirmation
bool etatActuel[3]     = {false, false, false}; // Ce que lit le capteur à l'instant T
bool etatConfirme[3]   = {false, false, false}; // L'état officiel après les 5 secondes
unsigned long chrono[3]= {0, 0, 0};             // Chronomètre pour chaque place

void setup() {
  Serial.begin(115200);
  Serial.println("\n--- DEMARRAGE ESP PARKING ---");

  // 1. Initialisation des broches
  for (int i = 0; i < 3; i++) {
    pinMode(pinCapteurs[i], INPUT_PULLUP); // PULLUP important pour Hall et Reed
    pinMode(pinLedRouge[i], OUTPUT);
    pinMode(pinLedVerte[i], OUTPUT);
    
    // Par défaut : Place Libre (VERT allumé, ROUGE éteint)
    digitalWrite(pinLedVerte[i], HIGH);
    digitalWrite(pinLedRouge[i], LOW);
  }

  // 2. Initialisation LoRa
  SPI.begin(5, 19, 27, 18);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DI0);
  
  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("ERREUR : LoRa introuvable !");
    while (1); // On bloque ici si erreur
  }
  Serial.println("LoRa OK. Freq: 870.3 MHz. Attente des vehicules...");
}

void loop() {
  bool changementDetecte = false;

  // On scanne les 3 places en boucle très rapidement
  for (int i = 0; i < 3; i++) {
    // Lecture du capteur (LOW = Aimant/Voiture détectée, HIGH = Rien)
    bool lecture = (digitalRead(pinCapteurs[i]) == LOW);

    // Si le capteur "saute" ou change d'état, on reset le chronomètre de cette place
    if (lecture != etatActuel[i]) {
      chrono[i] = millis(); 
      etatActuel[i] = lecture;
    }

    // Si l'état est stable pendant plus de 5 secondes...
    if ((millis() - chrono[i]) > DELAI_MANOEUVRE) {
      
      // ... et que cet état est différent de l'état officiel connu
      if (etatActuel[i] != etatConfirme[i]) {
        etatConfirme[i] = etatActuel[i]; // On valide le nouvel état
        changementDetecte = true;        // On prépare l'envoi LoRa
        
        // Mise à jour visuelle des LEDs
        if (etatConfirme[i] == true) { // OCCUPÉ
          digitalWrite(pinLedVerte[i], LOW);
          digitalWrite(pinLedRouge[i], HIGH);
          Serial.print("Place "); Serial.print(i+1); Serial.println(" : OCCUPEE !");
        } else {                       // LIBRE
          digitalWrite(pinLedRouge[i], LOW);
          digitalWrite(pinLedVerte[i], HIGH);
          Serial.print("Place "); Serial.print(i+1); Serial.println(" : LIBRE !");
        }
      }
    }
  }

  // S'il y a eu au moins un changement confirmé, on envoie UN SEUL message LoRa global
  if (changementDetecte) {
    envoyerTrameLoRa();
  }
}

// ==========================================
// 📡 FONCTION D'ENVOI LORA
// ==========================================
void envoyerTrameLoRa() {
  // Format : SECURE_PARK|1:O|2:L|3:O
  String message = String(SECRET_KEY);
  
  for (int i = 0; i < 3; i++) {
    message += String(i+1) + ":" + (etatConfirme[i] ? "O" : "L");
    if (i < 2) message += "|"; // Séparateur
  }

  LoRa.beginPacket();
  LoRa.print(message);
  LoRa.endPacket();

  Serial.println("-> Message LoRa envoye : " + message);
}