#!/usr/bin/env python3
import time
from rpi_ws281x import PixelStrip, Color

LED_COUNT = 144       # anpassen
LED_PIN = 18          # GPIO anpassen
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 120
LED_INVERT = False
LED_CHANNEL = 0

strip = PixelStrip(
    LED_COUNT,
    LED_PIN,
    LED_FREQ_HZ,
    LED_DMA,
    LED_INVERT,
    LED_BRIGHTNESS,
    LED_CHANNEL
)

def fill_color(r, g, b):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(r, g, b))
    strip.show()

def clear():
    fill_color(0, 0, 0)

def chase_test():
    clear()
    for step in range(20):
        for i in range(strip.numPixels()):
            if (i + step) % 6 < 3:
                strip.setPixelColor(i, Color(255, 0, 0))
            else:
                strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        time.sleep(0.1)

def one_by_one():
    clear()
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 255, 0))
        strip.show()
        time.sleep(0.02)
    time.sleep(1)
    clear()

if __name__ == "__main__":
    strip.begin()

    print("Test 1: Rot")
    fill_color(255, 0, 0)
    time.sleep(2)

    print("Test 2: Grün")
    fill_color(0, 255, 0)
    time.sleep(2)

    print("Test 3: Blau")
    fill_color(0, 0, 255)
    time.sleep(2)

    print("Test 4: Weiß")
    fill_color(255, 255, 255)
    time.sleep(2)

    print("Test 5: Lauflicht")
    one_by_one()

    print("Test 6: Chase")
    chase_test()

    print("Aus")
    clear()