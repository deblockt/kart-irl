#include "servo_controller.h"

#include <ESP32Servo.h>

#include "log.h"

static Servo monServo;

void servoSetup(int pin) {
  monServo.attach(pin);
  monServo.write(90);
}

void servoSetAngle(int angle) {
  if (angle < 0) angle = 0;
  if (angle > 180) angle = 180;
  monServo.write(angle);
}
