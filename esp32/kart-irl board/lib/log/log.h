#pragma once

#include <Arduino.h>
#include <WiFi.h>

void logSetup();
void logStartTelnet();
void logLoop();
void logPrint(String message);
void logPrintln(String message);
