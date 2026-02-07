#include "web_server.h"

#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include "led.h"
#include "servo_controller.h"
#include "engine.h"
#include "log.h"

extern const char index_html_start[] asm("_binary_data_index_html_start");
extern const char index_html_end[] asm("_binary_data_index_html_end");

static AsyncWebServer server(80);
static AsyncWebSocket ws("/ws");

static void handleWebSocketMessage(void *arg, uint8_t *data, size_t len) {
  AwsFrameInfo *info = (AwsFrameInfo*)arg;
  if (info->final && info->index == 0 && info->len == len && info->opcode == WS_TEXT) {
    data[len] = 0;

    JsonDocument doc;
    if (deserializeJson(doc, (char*)data)) {
      logPrintln("WebSocket: JSON invalide");
      return;
    }

    const char* type = doc["type"];
    if (!type) return;

    if (strcmp(type, "servo") == 0) {
      int angle = doc["angle"];
      servoSetAngle(angle);
      logPrintln("WS: servo " + String(angle));
    } else if (strcmp(type, "engine") == 0) {
      int speed = doc["speed"];
      engineSetSpeed(speed);
      logPrintln("WS: engine " + String(speed));
    } else if (strcmp(type, "led") == 0) {
      const char* state = doc["state"];
      if (state && strcmp(state, "on") == 0) {
        ledOn();
        logPrintln("WS: led on");
      } else if (state && strcmp(state, "off") == 0) {
        ledOff();
        logPrintln("WS: led off");
      }
    }
  }
}

static void onWebSocketEvent(AsyncWebSocket *server, AsyncWebSocketClient *client,
                              AwsEventType type, void *arg, uint8_t *data, size_t len) {
  switch (type) {
    case WS_EVT_CONNECT:
      logPrintln("WS client connecté #" + String(client->id()));
      break;
    case WS_EVT_DISCONNECT:
      logPrintln("WS client déconnecté #" + String(client->id()));
      break;
    case WS_EVT_DATA:
      handleWebSocketMessage(arg, data, len);
      break;
    default:
      break;
  }
}

void webServerSetup() {
  ws.onEvent(onWebSocketEvent);
  server.addHandler(&ws);

  server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
    request->send_P(200, "text/html", index_html_start);
  });

  server.begin();
  logPrintln("Serveur web démarré sur le port 80");
}
