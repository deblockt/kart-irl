#include "servo_controller.h"

#include <ESP32Servo.h>

#include "log.h"

static Servo monServo;

void servoSetup(int pin) {
  monServo.attach(pin);
  monServo.write(90);
}

void servoLoop() {
  static unsigned long lastMove = 0;
  static int angle = 90;
  static int direction = 1;

  if (millis() - lastMove > 20) {
    lastMove = millis();

    angle += direction;

    if (angle >= 180) {
      direction = -1;
      logPrintln("Servo: 180° → 0°");
    }
    if (angle <= 0) {
      direction = 1;
      logPrintln("Servo: 0° → 180°");
    }

    monServo.write(angle);
  }
}
