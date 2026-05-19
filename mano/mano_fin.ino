#include <WiFi.h>
#include <WebServer.h>

#define SERVO_INDICE  7
#define SERVO_MEDIO   9
#define SERVO_ANULAR  5
#define SERVO_MENIQUE 4
#define SERVO_PRET    15
#define SERVO_PGIRO   16

#define FREQ       50
#define RESOLUCION 12

#define CANAL_INDICE  0
#define CANAL_MEDIO   1
#define CANAL_ANULAR  2
#define CANAL_MENIQUE 3
#define CANAL_PRET    4
#define CANAL_PGIRO   5

const char* ssid     = "S23 FE de Gina";      // cambia por tu red
const char* password = "gina2021";     // cambia por tu clave

WebServer server(80);

struct LetraLSC {
  char letra;
  int indice;
  int medio;
  int anular;
  int menique;
  int pret;
  int pgiro;
};

LetraLSC letras[] = {
  { 'A', 0,   0,   0,   180, 45, 180 },
  { 'B', 180, 180, 180, 0,   180, 0   },
  { 'C', 90,  90,  90,  90,  0,   90  },
  { 'D', 180, 0,   0,   180, 120, 90  },
  { 'E', 0,   0,   0,   180, 180, 0   },
  { 'F', 90,  180, 180, 0,   90,  90  },
  { 'G', 140, 0,   0,   180, 180, 90  },
  { 'H', 180, 180, 0,   180, 60,  45  },
  { 'I', 0,   0,   0,   0,   120, 0   },
  { 'J', 0,   0,   0,   0,   120, 0   },
  { 'K', 180, 150, 0,   180, 150, 70  },
  { 'L', 180, 0,   0,   180, 0,   180 },
  { 'M', 50,  0,   0,   180, 100, 45  },
  { 'N', 50,  0,   0,   180, 100, 45  },
  { 'O', 70,  70,  70,  110, 30,  90  },
  { 'P', 180, 60,  0,   180, 45,  90  },
  { 'Q', 180, 0,   0,   0,   0,   90  },
  { 'R', 180, 180, 0,   0,   120, 90  },
  { 'S', 0,   0,   0,   180, 120, 90  },
  { 'T', 0,   0,   0,   180, 150, 90  },
  { 'U', 180, 0,   0,   0,   180, 0   },
  { 'V', 180, 180, 0,   0,   180, 180 },
  { 'W', 180, 180, 180, 0,   150, 180 },
  { 'X', 90,  0,   0,   0,   180, 90  },
  { 'Y', 0,   0,   0,   180, 0,   180 },
  { 'Z', 180, 0,   0,   0,   120, 90  },
};

const int TOTAL_LETRAS = sizeof(letras) / sizeof(LetraLSC);

int gradoADuty(int grado) {
  return map(grado, 0, 180, 102, 512);
}

void moverServo(int canal, int grado) {
  ledcWrite(canal, gradoADuty(grado));
}

void moverLento(int canal, int inicio, int fin) {
  if (inicio < fin) {
    for (int i = inicio; i <= fin; i++) {
      moverServo(canal, i);
      delay(20);
    }
  } else {
    for (int i = inicio; i >= fin; i--) {
      moverServo(canal, i);
      delay(20);
    }
  }
  delay(600);
}

void manoAbierta() {
  moverServo(CANAL_INDICE,  180); delay(600);
  moverServo(CANAL_MEDIO,   180); delay(600);
  moverServo(CANAL_ANULAR,  180); delay(600);
  moverServo(CANAL_MENIQUE,   0); delay(600);
  moverServo(CANAL_PRET,      0); delay(600);
  moverServo(CANAL_PGIRO,     0); delay(600);
  Serial.println("Mano abierta.");
}

void ejecutarLetra(char letra) {
  for (int i = 0; i < TOTAL_LETRAS; i++) {
    if (letras[i].letra == letra) {
      LetraLSC l = letras[i];
      Serial.print("Ejecutando: ");
      Serial.println(l.letra);

      if (letra == 'M') {
        moverLento(CANAL_MENIQUE, 0,   l.menique);
        moverLento(CANAL_PGIRO,   0,   l.pgiro);
        moverLento(CANAL_PRET,    0,   l.pret);
        moverLento(CANAL_ANULAR,  180, l.anular);
        moverLento(CANAL_MEDIO,   180, l.medio);
        moverLento(CANAL_INDICE,  180, l.indice);

      } else if (letra == 'N') {
        moverLento(CANAL_MENIQUE, 0,   l.menique);
        moverLento(CANAL_ANULAR,  180, l.anular);
        moverLento(CANAL_PGIRO,   0,   l.pgiro);
        moverLento(CANAL_PRET,    0,   l.pret);
        moverLento(CANAL_MEDIO,   180, l.medio);
        moverLento(CANAL_INDICE,  180, l.indice);

      } else {
        moverLento(CANAL_INDICE,  180, l.indice);
        moverLento(CANAL_MEDIO,   180, l.medio);
        moverLento(CANAL_ANULAR,  180, l.anular);
        moverLento(CANAL_MENIQUE,   0, l.menique);
        moverLento(CANAL_PRET,      0, l.pret);
        moverLento(CANAL_PGIRO,     0, l.pgiro);
      }

      Serial.println("Listo.");
      return;
    }
  }
  Serial.print("Saltando: ");
  Serial.println(letra);
}

void escribirPalabra(String palabra) {
  Serial.print("Escribiendo: ");
  Serial.println(palabra);

  for (int i = 0; i < palabra.length(); i++) {
    char letra = palabra.charAt(i);
    if (letra == ' ') {
      manoAbierta();
      delay(1000);
      continue;
    }
    manoAbierta();
    delay(500);
    ejecutarLetra(letra);
    delay(500);
  }

  Serial.println("Palabra completada.");
  manoAbierta();
}

void setup() {
  Serial.begin(115200);
  delay(500);

  ledcSetup(CANAL_INDICE,  FREQ, RESOLUCION); ledcAttachPin(SERVO_INDICE,  CANAL_INDICE);  delay(300);
  ledcSetup(CANAL_MEDIO,   FREQ, RESOLUCION); ledcAttachPin(SERVO_MEDIO,   CANAL_MEDIO);   delay(300);
  ledcSetup(CANAL_ANULAR,  FREQ, RESOLUCION); ledcAttachPin(SERVO_ANULAR,  CANAL_ANULAR);  delay(300);
  ledcSetup(CANAL_MENIQUE, FREQ, RESOLUCION); ledcAttachPin(SERVO_MENIQUE, CANAL_MENIQUE); delay(300);
  ledcSetup(CANAL_PRET,    FREQ, RESOLUCION); ledcAttachPin(SERVO_PRET,    CANAL_PRET);    delay(300);
  ledcSetup(CANAL_PGIRO,   FREQ, RESOLUCION); ledcAttachPin(SERVO_PGIRO,   CANAL_PGIRO);   delay(300);

  manoAbierta();

  // Conectar WiFi
  Serial.print("Conectando a WiFi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Conectado. IP: ");
  Serial.println(WiFi.localIP());

  // Rutas del servidor
  server.on("/letra", []() {
    if (server.hasArg("l")) {
      String l = server.arg("l");
      l.toUpperCase();
      char letra = l.charAt(0);
      Serial.print("Recibido por WiFi: ");
      Serial.println(letra);
      manoAbierta();
      delay(500);
      ejecutarLetra(letra);
      server.send(200, "text/plain", "OK");
    } else {
      server.send(400, "text/plain", "Falta parametro l");
    }
  });

  server.on("/palabra", []() {
    if (server.hasArg("p")) {
      String palabra = server.arg("p");
      palabra.toUpperCase();
      Serial.print("Recibido por WiFi: ");
      Serial.println(palabra);
      escribirPalabra(palabra);
      server.send(200, "text/plain", "OK");
    } else {
      server.send(400, "text/plain", "Falta parametro p");
    }
  });

  server.on("/reset", []() {
    manoAbierta();
    server.send(200, "text/plain", "OK");
  });

  server.begin();
  Serial.println("Servidor HTTP listo.");
  Serial.println("=== MANO LSC WiFi ===");
}

void loop() {
  server.handleClient();
}