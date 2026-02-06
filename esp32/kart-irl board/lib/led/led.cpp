#include "led.h"

static int ledPin;

void ledSetup(int pin) {
  ledPin = pin;
  pinMode(ledPin, OUTPUT);
}

void ledOn() {
  digitalWrite(ledPin, HIGH);
}

void ledOff() {
  digitalWrite(ledPin, LOW);
}

void flash(int number, int delayMs) {
  for (int i = 0; i < number; i++) {
    ledOn();
    delay(delayMs);
    ledOff();
    delay(delayMs);
  }
}
