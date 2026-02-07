#include <ArduinoOTA.h>

#include "config.h"
#include "led.h"
#include "log.h"
#include "wifi_manager.h"
#include "servo_controller.h"
#include "engine.h"
#include "web_server.h"

Motor motor(PIN_ENGINE_PWM, PIN_ENGINE_IN_1, PIN_ENGINE_IN_2, PWM_CHANNEL_ENGINE);

void setup() {
  ledSetup(LED_FLASH);
  logSetup();
  wifiSetup(WIFI_SSID, WIFI_PASSWORD);
  logStartTelnet();
  servoSetup(SERVO_PIN);
  engineSetup(motor);
  webServerSetup();
}

void loop() {
  ArduinoOTA.handle();
  logLoop();
}
