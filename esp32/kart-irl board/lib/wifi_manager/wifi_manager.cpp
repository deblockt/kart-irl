#include "wifi_manager.h"

#include <WiFi.h>
#include <ArduinoOTA.h>

#include "led.h"
#include "log.h"

void wifiSetup(const char* ssid, const char* password) {
  ledOn();
  logPrintln("Connexion au WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.waitForConnectResult() != WL_CONNECTED) {
    logPrintln("Échec de connexion! Redémarrage...");
    flash(10, 300);
    delay(5000);
    ESP.restart();
  }

  logPrintln("WiFi connecté!");
  logPrint("Adresse IP: ");
  logPrintln(WiFi.localIP().toString());

  ledOff();
  flash(3, 1000);

  // OTA
  ArduinoOTA.setHostname("ESP32-CAM");
  ArduinoOTA.begin();
}
