#include <Arduino.h>

// ── PINES ──────────────────────────────────────────────────
#define SERVO_PGIRO    4   // Pulgar rotar
#define SERVO_PRET     5   // Pulgar doblar
#define SERVO_INDICE   6   // Índice
#define SERVO_MEDIO    7   // Corazón
#define SERVO_ANULAR   15  // Anular
#define SERVO_MENIQUE  16  // Meñique

#define FREQ       50
#define RESOLUCION 12

#define CANAL_INDICE  0
#define CANAL_MEDIO   1
#define CANAL_ANULAR  2
#define CANAL_MENIQUE 3
#define CANAL_PRET    4
#define CANAL_PGIRO   5

#define PASO_MS      8
#define PAUSA_SERVO  200
#define PAUSA_LETRA  300
#define PAUSA_PULGAR 150

struct LetraLSC {
  char letra;
  int indice, medio, anular, menique, pret, pgiro;
};

// ── ÁNGULOS CALIBRADOS ─────────────────────────────────────
LetraLSC letras[] = {
  { 'A', 0,   0,   0,   180, 45,  180 },
  { 'B', 180, 180, 180, 0,   0,   45  },
  { 'C', 90,  90,  90,  90,  90,  90  },
  { 'D', 180, 45,  30,  150, 45,  70  },
  { 'E', 45,  45,  45,  135, 45,  0   },
  { 'F', 90,  180, 180, 0,   45,  80  },
  { 'G', 140, 0,   0,   180, 30,  90  },
  { 'H', 180, 180, 0,   180, 45,  45  },
  { 'I', 0,   0,   0,   0,   0,   0   },
  { 'J', 0,   0,   0,   0,   0,   0   },
  { 'K', 180, 130, 0,   180, 10,  70  },
  { 'L', 180, 0,   0,   180, 90,  90  },
  { 'M', 50,  0,   0,   180, 10,  45  },
  { 'N', 50,  0,   0,   180, 10,  45  },
  { 'O', 70,  70,  70,  110, 38,  90  },
  { 'P', 180, 60,  0,   180, 30,  90  },
  { 'Q', 140, 0,   0,   180, 30,  90  },
  { 'R', 180, 180, 0,   180, 20,  70  },
  { 'S', 0,   0,   0,   180, 38,  20  },
  { 'T', 50,  0,   0,   180, 20,  80  },
  { 'U', 180, 0,   0,   0,   0,   0   },
  { 'V', 180, 180, 0,   180, 0,   30  },
  { 'W', 180, 180, 180, 180, 0,   30  },
  { 'X', 130, 0,   0,   180, 10,  70  },
  { 'Y', 0,   0,   0,   0,   90,  0   },
  { 'Z', 180, 45,  30,  150, 45,  0   },
};

const int TOTAL_LETRAS = sizeof(letras) / sizeof(LetraLSC);

// Posición actual de cada servo (para arrancar animaciones desde donde están)
int posActual[6] = {180, 180, 180, 0, 0, 0};
// 0=IND, 1=MED, 2=ANU, 3=MEN, 4=PRET, 5=PGIRO

// Última letra ejecutada (para saber cómo abrir sin trabarse)
char ultimaLetra = ' ';

// ── Helpers servo ──────────────────────────────────────────

int gradoADuty(int grado) {
  grado = constrain(grado, 0, 180);
  return map(grado, 0, 180, 102, 512);
}

void moverServo(int canal, int grado) {
  ledcWrite(canal, gradoADuty(grado));
  posActual[canal] = grado;
}

void moverLento(int canal, int fin) {
  int inicio = posActual[canal];
  if (inicio == fin) return;
  int paso = (inicio < fin) ? 1 : -1;
  for (int i = inicio; i != fin; i += paso) {
    ledcWrite(canal, gradoADuty(i));
    delay(PASO_MS);
  }
  moverServo(canal, fin);
  delay(PAUSA_SERVO);
}

// ── Mano abierta inteligente ───────────────────────────────
// Abre en orden INVERSO al de cierre de la última letra,
// para evitar que los dedos se traben entre sí.

void manoAbierta() {
  Serial.print("[ABRIR] Desde letra: ");
  Serial.println(ultimaLetra == ' ' ? '-' : ultimaLetra);

  switch (ultimaLetra) {

    // ─── Letras donde el PULGAR se cerró PRIMERO ───
    // Al abrir: pulgar de ÚLTIMAS (está atrapado bajo los demás)
    case 'A':
    case 'G':
    case 'I':
    case 'J':
      moverLento(CANAL_INDICE, 180);
      moverLento(CANAL_MEDIO,  180);
      moverLento(CANAL_ANULAR, 180);
      moverLento(CANAL_MENIQUE, 0);
      moverLento(CANAL_PRET,  90);
      moverLento(CANAL_PGIRO, 0);
      break;

    // ─── Letras donde el PULGAR se cerró DE ÚLTIMAS ───
    // Al abrir: pulgar PRIMERO (está encima de los demás)
    case 'E':
    case 'H':
    case 'U':
    case 'V':
    case 'X':
      moverLento(CANAL_PRET,  90);
      moverLento(CANAL_PGIRO, 0);
      moverLento(CANAL_INDICE, 180);
      moverLento(CANAL_MEDIO,  180);
      moverLento(CANAL_ANULAR, 180);
      moverLento(CANAL_MENIQUE, 0);
      break;

    // ─── K, P, S: cerraron rotando antes que bajar ───
    // Al abrir: subir pret PRIMERO, pausa, luego rotar pgiro
    case 'K':
    case 'P':
    case 'S':
      moverLento(CANAL_PRET,  90);
      delay(PAUSA_PULGAR);
      moverLento(CANAL_PGIRO, 0);
      moverLento(CANAL_INDICE, 180);
      moverLento(CANAL_MEDIO,  180);
      moverLento(CANAL_ANULAR, 180);
      moverLento(CANAL_MENIQUE, 0);
      break;

    // ─── N: cerró meñique, anular, pulgar, índice, medio ───
    // Al abrir: inverso exacto
    case 'N':
      moverLento(CANAL_MEDIO,  180);
      moverLento(CANAL_INDICE, 180);
      moverLento(CANAL_PRET,   90);
      moverLento(CANAL_PGIRO,  0);
      moverLento(CANAL_ANULAR, 180);
      moverLento(CANAL_MENIQUE, 0);
      break;

    // ─── Estándar y resto: orden seguro genérico ───
    default:
      moverLento(CANAL_INDICE, 180);
      moverLento(CANAL_MEDIO,  180);
      moverLento(CANAL_ANULAR, 180);
      moverLento(CANAL_PRET,   90);
      moverLento(CANAL_PGIRO,  0);
      moverLento(CANAL_MENIQUE, 0);
      break;
  }

  ultimaLetra = ' ';  // Reset
  Serial.println("[OK] Mano abierta");
}

// ── Buscar letra ───────────────────────────────────────────

int indiceLetra(char c) {
  for (int i = 0; i < TOTAL_LETRAS; i++) {
    if (letras[i].letra == c) return i;
  }
  return -1;
}

// ── Helpers de grupo ───────────────────────────────────────

void moverPulgarCompleto(int pret_fin, int pgiro_fin) {
  moverLento(CANAL_PGIRO, pgiro_fin);
  moverLento(CANAL_PRET,  pret_fin);
}

void moverPulgarRotarPrimero(int pret_fin, int pgiro_fin) {
  moverLento(CANAL_PGIRO, pgiro_fin);
  delay(PAUSA_PULGAR);
  moverLento(CANAL_PRET,  pret_fin);
}

void moverLargos(int ind_fin, int med_fin, int anu_fin) {
  moverLento(CANAL_INDICE, ind_fin);
  moverLento(CANAL_MEDIO,  med_fin);
  moverLento(CANAL_ANULAR, anu_fin);
}

void moverMenique(int men_fin) {
  moverLento(CANAL_MENIQUE, men_fin);
}

// ── Aplicar pose (sin animación, para calibración) ─────────

void aplicarPose(char c) {
  int idx = indiceLetra(c);
  if (idx < 0) {
    Serial.print("[SKIP] Letra no encontrada: ");
    Serial.println(c);
    return;
  }
  LetraLSC l = letras[idx];
  moverServo(CANAL_INDICE,  l.indice);
  moverServo(CANAL_MEDIO,   l.medio);
  moverServo(CANAL_ANULAR,  l.anular);
  moverServo(CANAL_MENIQUE, l.menique);
  moverServo(CANAL_PRET,    l.pret);
  moverServo(CANAL_PGIRO,   l.pgiro);
  ultimaLetra = c;
  Serial.print("[POSE] ");
  Serial.print(c);
  Serial.print(" → I:"); Serial.print(l.indice);
  Serial.print(" M:");   Serial.print(l.medio);
  Serial.print(" A:");   Serial.print(l.anular);
  Serial.print(" Me:");  Serial.print(l.menique);
  Serial.print(" Pd:");  Serial.print(l.pret);
  Serial.print(" Pr:");  Serial.println(l.pgiro);
}

// ── Ejecutar letra con coreografía específica ──────────────

void ejecutarLetra(char letra) {
  int idx = indiceLetra(letra);
  if (idx < 0) {
    Serial.print("[SKIP] Letra no encontrada: ");
    Serial.println(letra);
    return;
  }
  LetraLSC l = letras[idx];
  Serial.print("[LSC] Ejecutando: ");
  Serial.println(l.letra);

  switch (letra) {

    case 'A':  // PULGAR PRIMERO
      moverPulgarCompleto(l.pret, l.pgiro);
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'B':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'C':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'D':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'E':  // PULGAR DE ÚLTIMAS
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarCompleto(l.pret, l.pgiro);
      break;

    case 'F':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'G':  // PULGAR DE PRIMERAS
      moverPulgarCompleto(l.pret, l.pgiro);
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'H':  // PULGAR DE ÚLTIMAS
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarCompleto(l.pret, l.pgiro);
      break;

    case 'I':  // PULGAR PRIMERAS
      moverPulgarCompleto(l.pret, l.pgiro);
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'J':  // PULGAR PRIMERAS
      moverPulgarCompleto(l.pret, l.pgiro);
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'K':  // PULGAR DE ÚLTIMAS, ROTAR PRIMERO Y AHÍ SÍ BAJAR
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarRotarPrimero(l.pret, l.pgiro);
      break;

    case 'L':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'M':  // MEÑIQUE → PULGAR → DEMÁS
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'N':  // MEÑIQUE → ANULAR → PULGAR → DEMÁS
      moverMenique(l.menique);
      moverLento(CANAL_ANULAR, l.anular);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLento(CANAL_INDICE, l.indice);
      moverLento(CANAL_MEDIO,  l.medio);
      break;

    case 'O':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'P':  // PULGAR DE ÚLTIMAS, ROTAR PRIMERO Y AHÍ SÍ BAJAR
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarRotarPrimero(l.pret, l.pgiro);
      break;

    case 'Q':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'R':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'S':  // PULGAR DE ÚLTIMAS, ROTAR PRIMERO Y AHÍ SÍ BAJAR
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarRotarPrimero(l.pret, l.pgiro);
      break;

    case 'T':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'U':  // PULGAR DE ÚLTIMAS
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarCompleto(l.pret, l.pgiro);
      break;

    case 'V':  // PULGAR DE ÚLTIMAS
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarCompleto(l.pret, l.pgiro);
      break;

    case 'W':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'X':  // PULGAR DE ÚLTIMAS
      moverMenique(l.menique);
      moverLargos(l.indice, l.medio, l.anular);
      moverPulgarCompleto(l.pret, l.pgiro);
      break;

    case 'Y':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    case 'Z':  // Estándar
      moverMenique(l.menique);
      moverPulgarCompleto(l.pret, l.pgiro);
      moverLargos(l.indice, l.medio, l.anular);
      break;

    default:
      Serial.print("[SKIP] Sin coreografía para: ");
      Serial.println(letra);
      return;
  }

  ultimaLetra = letra;  // Guardar para que manoAbierta sepa cómo abrir
  Serial.println("[OK] Listo");
}

// ── Ejecutar palabra ───────────────────────────────────────

void ejecutarPalabra(String palabra) {
  Serial.print("[LSC] Palabra: ");
  Serial.println(palabra);
  for (int i = 0; i < (int)palabra.length(); i++) {
    char c = palabra.charAt(i);
    if (c == ' ') { manoAbierta(); delay(500); continue; }
    manoAbierta();
    delay(PAUSA_LETRA);
    ejecutarLetra(c);
    delay(PAUSA_LETRA);
  }
  manoAbierta();
  Serial.println("[OK] Palabra completada");
}

// ── Comandos de calibración ────────────────────────────────

void cmdSet(String args) {
  args.trim();
  if (args.length() < 3) {
    Serial.println("[ERR] Uso: SET <LETRA>,ind,med,anu,men,pret,pgiro");
    return;
  }
  char letra = args.charAt(0);
  int idx = indiceLetra(letra);
  if (idx < 0) {
    Serial.print("[ERR] Letra no existe: ");
    Serial.println(letra);
    return;
  }

  int coma = args.indexOf(',');
  if (coma < 0) {
    Serial.println("[ERR] Faltan valores.");
    return;
  }
  String nums = args.substring(coma + 1);

  int vals[6];
  int count = 0;
  while (count < 6 && nums.length() > 0) {
    int c = nums.indexOf(',');
    String tok = (c < 0) ? nums : nums.substring(0, c);
    tok.trim();
    vals[count++] = tok.toInt();
    if (c < 0) break;
    nums = nums.substring(c + 1);
  }

  if (count < 6) {
    Serial.println("[ERR] Necesito 6 valores: ind,med,anu,men,pret,pgiro");
    return;
  }

  letras[idx].indice  = constrain(vals[0], 0, 180);
  letras[idx].medio   = constrain(vals[1], 0, 180);
  letras[idx].anular  = constrain(vals[2], 0, 180);
  letras[idx].menique = constrain(vals[3], 0, 180);
  letras[idx].pret    = constrain(vals[4], 0, 180);
  letras[idx].pgiro   = constrain(vals[5], 0, 180);

  Serial.print("[OK] Guardado letra ");
  Serial.println(letra);
  aplicarPose(letra);
}

void cmdServo(String args) {
  args.trim();
  int sp = args.indexOf(' ');
  if (sp < 0) {
    Serial.println("[ERR] Uso: SERVO <IND|MED|ANU|MEN|PRET|PGIRO> <0-180>");
    return;
  }
  String nombre = args.substring(0, sp);
  int grado = args.substring(sp + 1).toInt();
  nombre.toUpperCase();

  int canal = -1;
  if      (nombre == "IND")   canal = CANAL_INDICE;
  else if (nombre == "MED")   canal = CANAL_MEDIO;
  else if (nombre == "ANU")   canal = CANAL_ANULAR;
  else if (nombre == "MEN")   canal = CANAL_MENIQUE;
  else if (nombre == "PRET")  canal = CANAL_PRET;
  else if (nombre == "PGIRO") canal = CANAL_PGIRO;
  else {
    Serial.print("[ERR] Nombre inválido: ");
    Serial.println(nombre);
    return;
  }

  moverServo(canal, grado);
  Serial.print("[OK] ");
  Serial.print(nombre);
  Serial.print(" → ");
  Serial.println(grado);
}

void cmdGet(char letra) {
  int idx = indiceLetra(letra);
  if (idx < 0) {
    Serial.print("[ERR] Letra no existe: ");
    Serial.println(letra);
    return;
  }
  LetraLSC l = letras[idx];
  Serial.print("SET ");
  Serial.print(l.letra); Serial.print(",");
  Serial.print(l.indice); Serial.print(",");
  Serial.print(l.medio); Serial.print(",");
  Serial.print(l.anular); Serial.print(",");
  Serial.print(l.menique); Serial.print(",");
  Serial.print(l.pret); Serial.print(",");
  Serial.println(l.pgiro);
}

void cmdDump() {
  Serial.println("// ─── Valores actuales (copia al código) ───");
  for (int i = 0; i < TOTAL_LETRAS; i++) {
    LetraLSC l = letras[i];
    Serial.print("{ '"); Serial.print(l.letra); Serial.print("', ");
    Serial.print(l.indice); Serial.print(", ");
    Serial.print(l.medio); Serial.print(", ");
    Serial.print(l.anular); Serial.print(", ");
    Serial.print(l.menique); Serial.print(", ");
    Serial.print(l.pret); Serial.print(", ");
    Serial.print(l.pgiro); Serial.println(" },");
  }
}

void cmdHelp() {
  Serial.println("=== COMANDOS ===");
  Serial.println("<letra>              → ejecutar seña (ej: A)");
  Serial.println("<palabra>            → deletrear (ej: HOLA)");
  Serial.println("RESET / OPEN         → mano abierta");
  Serial.println("POSE <letra>         → ir directo a la pose sin animación");
  Serial.println("SET <L>,i,m,a,me,pr,pg → cambiar ángulos y aplicar");
  Serial.println("GET <letra>          → mostrar ángulos actuales");
  Serial.println("SERVO <NOMBRE> <0-180> → mover un servo (IND/MED/ANU/MEN/PRET/PGIRO)");
  Serial.println("DUMP                 → volcar todo el alfabeto");
  Serial.println("HELP                 → esta ayuda");
}

// ── Parser ─────────────────────────────────────────────────

void procesarEntrada(String entrada) {
  entrada.trim();
  if (entrada.length() == 0) return;

  String upper = entrada;
  upper.toUpperCase();

  if (upper == "RESET" || upper == "OPEN") { manoAbierta(); return; }
  if (upper == "HELP"  || upper == "?")    { cmdHelp(); return; }
  if (upper == "DUMP")                     { cmdDump(); return; }

  if (upper.startsWith("SET "))   { cmdSet(entrada.substring(4)); return; }
  if (upper.startsWith("GET "))   { cmdGet(upper.charAt(4)); return; }
  if (upper.startsWith("POSE "))  { aplicarPose(upper.charAt(5)); return; }
  if (upper.startsWith("SERVO ")) { cmdServo(entrada.substring(6)); return; }

  if (upper.length() == 1) {
    manoAbierta();
    delay(PAUSA_LETRA);
    ejecutarLetra(upper.charAt(0));
  } else {
    ejecutarPalabra(upper);
  }
}

// ── Setup / Loop ───────────────────────────────────────────

void setup() {
  Serial.begin(115200);
  delay(300);

  ledcSetup(CANAL_INDICE,  FREQ, RESOLUCION); ledcAttachPin(SERVO_INDICE,  CANAL_INDICE);
  ledcSetup(CANAL_MEDIO,   FREQ, RESOLUCION); ledcAttachPin(SERVO_MEDIO,   CANAL_MEDIO);
  ledcSetup(CANAL_ANULAR,  FREQ, RESOLUCION); ledcAttachPin(SERVO_ANULAR,  CANAL_ANULAR);
  ledcSetup(CANAL_MENIQUE, FREQ, RESOLUCION); ledcAttachPin(SERVO_MENIQUE, CANAL_MENIQUE);
  ledcSetup(CANAL_PRET,    FREQ, RESOLUCION); ledcAttachPin(SERVO_PRET,    CANAL_PRET);
  ledcSetup(CANAL_PGIRO,   FREQ, RESOLUCION); ledcAttachPin(SERVO_PGIRO,   CANAL_PGIRO);

  // Estado inicial: mano abierta directo (sin animación al arranque)
  moverServo(CANAL_INDICE,  180);
  moverServo(CANAL_MEDIO,   180);
  moverServo(CANAL_ANULAR,  180);
  moverServo(CANAL_MENIQUE,   0);
  moverServo(CANAL_PRET,     90);
  moverServo(CANAL_PGIRO,     0);
  delay(500);

  Serial.println("=== MANO LSC — Modo Calibración ===");
  cmdHelp();
}

void loop() {
  if (Serial.available()) {
    String entrada = Serial.readStringUntil('\n');
    procesarEntrada(entrada);
  }
}