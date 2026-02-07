#include "engine.h"

#include "log.h"

static const int PWM_FREQ = 5000;
static const int PWM_RESOLUTION = 8; // 0-255

Motor::Motor(int pwmPin, int in1Pin, int in2Pin, int channel)
  : _pwmPin(pwmPin), _in1Pin(in1Pin), _in2Pin(in2Pin), _channel(channel) {}

void Motor::setup() {
  pinMode(_in1Pin, OUTPUT);
  pinMode(_in2Pin, OUTPUT);
  ledcSetup(_channel, PWM_FREQ, PWM_RESOLUTION);
  ledcAttachPin(_pwmPin, _channel);
  stop();
}

void Motor::setSpeed(int speed) {
  if (speed < -255) speed = -255;
  if (speed > 255) speed = 255;
  if (speed > 0) {
    digitalWrite(_in1Pin, HIGH);
    digitalWrite(_in2Pin, LOW);
  } else if (speed < 0) {
    digitalWrite(_in1Pin, LOW);
    digitalWrite(_in2Pin, HIGH);
  } else {
    digitalWrite(_in1Pin, LOW);
    digitalWrite(_in2Pin, LOW);
  }
  ledcWrite(_channel, abs(speed));
}

void Motor::stop() {
  setSpeed(0);
}

// --- API globale ---

static Motor *_motor;

void engineSetup(Motor &motor) {
  _motor = &motor;
  _motor->setup();
  logPrintln("Moteur initialisé (TB6612FNG)");
}

void engineSetSpeed(int speed) {
  _motor->setSpeed(speed);
  logPrintln("Moteur vitesse " + String(speed));
}

void engineStop() {
  _motor->stop();
}
