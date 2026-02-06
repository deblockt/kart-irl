#include "log.h"

static WiFiServer telnetServer(23);
static WiFiClient telnetClient;

void logSetup() {
  Serial.begin(115200);
}

void logStartTelnet() {
  telnetServer.begin();
  telnetServer.setNoDelay(true);
  logPrintln("Serveur Telnet démarré sur le port 23");
}

void logLoop() {
  if (telnetServer.hasClient()) {
    if (!telnetClient || !telnetClient.connected()) {
      if (telnetClient) telnetClient.stop();
      telnetClient = telnetServer.available();
      telnetClient.flush();
      logPrintln("Nouveau client Telnet connecté");
    }
  }
}

void logPrint(String message) {
  Serial.print(message);
  if (telnetClient && telnetClient.connected()) {
    telnetClient.print(message);
  }
}

void logPrintln(String message) {
  Serial.println(message);
  if (telnetClient && telnetClient.connected()) {
    telnetClient.println(message);
  }
}
