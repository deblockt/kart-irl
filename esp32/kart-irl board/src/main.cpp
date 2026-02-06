#include <ArduinoOTA.h>

#include "config.h"
#include "led.h"
#include "log.h"
#include "wifi_manager.h"
#include "servo_controller.h"

void setup() {
  ledSetup(LED_FLASH);
  logSetup();
  wifiSetup(WIFI_SSID, WIFI_PASSWORD);
  logStartTelnet();
  servoSetup(SERVO_PIN);
}

void loop() {
  ArduinoOTA.handle();
  logLoop();
  servoLoop();
}
