#include "web_server.h"

#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>

#include "led.h"
#include "servo_controller.h"
#include "engine.h"
#include "log.h"

static const char INDEX_HTML[] PROGMEM = R"rawliteral(<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kart IRL</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee; text-align: center; padding: 20px; }
    h1 { margin-bottom: 20px; }
    .status { padding: 8px 16px; border-radius: 20px; display: inline-block; margin-bottom: 30px; font-size: 14px; }
    .connected { background: #4CAF50; }
    .disconnected { background: #f44336; }
    .card { background: #16213e; border-radius: 12px; padding: 20px; margin: 15px auto; max-width: 400px; }
    .card h2 { margin-bottom: 15px; font-size: 18px; }
    input[type="range"] { width: 100%; accent-color: #4CAF50; }
    .angle { font-size: 32px; font-weight: bold; margin: 10px 0; }
    .btn { padding: 12px 30px; font-size: 16px; border: none; border-radius: 8px; cursor: pointer; margin: 5px; }
    .btn-on { background: #4CAF50; color: white; }
    .btn-off { background: #f44336; color: white; }
    .btn.active { outline: 3px solid white; }
    .speed-slider { writing-mode: vertical-lr; direction: rtl; height: 200px; width: 40px; accent-color: #2196F3; }
    .speed-value { font-size: 32px; font-weight: bold; margin: 10px 0; }
    .speed-label { font-size: 12px; color: #999; }
  </style>
</head>
<body>
  <h1>Kart IRL</h1>
  <div id="status" class="status disconnected">Connexion...</div>

  <div class="card">
    <h2>Servo</h2>
    <div class="angle" id="servoValue">90&deg;</div>
    <input type="range" id="servo" min="0" max="180" value="90">
  </div>

  <div class="card">
    <h2>Moteurs</h2>
    <div class="speed-value" id="speedValue">0%</div>
    <div class="speed-label">Avant</div>
    <input type="range" class="speed-slider" id="speed" min="-100" max="100" value="0">
    <div class="speed-label">Arriere</div>
  </div>

  <div class="card">
    <h2>LED</h2>
    <button class="btn btn-on" id="ledOn">ON</button>
    <button class="btn btn-off" id="ledOff">OFF</button>
  </div>

  <script>
    let ws;
    const status = document.getElementById('status');
    const slider = document.getElementById('servo');
    const servoValue = document.getElementById('servoValue');
    const speedSlider = document.getElementById('speed');
    const speedValue = document.getElementById('speedValue');
    const btnOn = document.getElementById('ledOn');
    const btnOff = document.getElementById('ledOff');

    function connect() {
      ws = new WebSocket('ws://' + location.hostname + '/ws');
      ws.onopen = () => {
        status.textContent = 'Connecte';
        status.className = 'status connected';
      };
      ws.onclose = () => {
        status.textContent = 'Deconnecte';
        status.className = 'status disconnected';
        setTimeout(connect, 2000);
      };
      ws.onerror = () => ws.close();
    }

    let lastSend = 0;
    slider.oninput = () => {
      servoValue.textContent = slider.value + '\u00B0';
      const now = Date.now();
      if (now - lastSend > 50) {
        ws.send(JSON.stringify({type: 'servo', angle: parseInt(slider.value)}));
        lastSend = now;
      }
    };
    slider.onchange = () => {
      ws.send(JSON.stringify({type: 'servo', angle: parseInt(slider.value)}));
    };

    let lastSpeedSend = 0;
    function sendSpeed() {
      const pct = parseInt(speedSlider.value);
      speedValue.textContent = pct + '%';
      const now = Date.now();
      if (now - lastSpeedSend > 50) {
        const pwm = Math.round(pct * 255 / 100);
        ws.send(JSON.stringify({type: 'engine', speed: pwm}));
        lastSpeedSend = now;
      }
    }
    speedSlider.oninput = sendSpeed;
    speedSlider.onchange = () => {
      const pct = parseInt(speedSlider.value);
      const pwm = Math.round(pct * 255 / 100);
      ws.send(JSON.stringify({type: 'engine', speed: pwm}));
    };
    speedSlider.addEventListener('touchend', () => {
      speedSlider.value = 0;
      speedValue.textContent = '0%';
      ws.send(JSON.stringify({type: 'engine', speed: 0}));
    });
    speedSlider.addEventListener('mouseup', () => {
      speedSlider.value = 0;
      speedValue.textContent = '0%';
      ws.send(JSON.stringify({type: 'engine', speed: 0}));
    });

    btnOn.onclick = () => {
      ws.send(JSON.stringify({type: 'led', state: 'on'}));
      btnOn.classList.add('active');
      btnOff.classList.remove('active');
    };
    btnOff.onclick = () => {
      ws.send(JSON.stringify({type: 'led', state: 'off'}));
      btnOff.classList.add('active');
      btnOn.classList.remove('active');
    };

    connect();
  </script>
</body>
</html>)rawliteral";

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
    request->send(200, "text/html", INDEX_HTML);
  });

  server.begin();
  logPrintln("Serveur web démarré sur le port 80");
}
