# LED_musik_visualizer
Python Code to control LEDs based on music rythms

Features
- Audioanalyse (FFT, RMS)
- automatische Audioquellen-Erkennung
- dynamische LED-Effekte
- Unterstützung für Mikrofon und VLC
  
Installation
- pip install -r requirements.txt
  
Start
- ./start.sh

Voraussetzungen
- Raspberry Pi
- LED-Streifen 
- Python 3
  
Projektstruktur
- audio_input.py → Audioanalyse
- main.py → Visualisierung
- config.py → Einstellungen
- led_test.py → LED-Test


Funktionsweise
Das Programm liest kontinuierlich Audiodaten ein und berechnet daraus Lautstärke (RMS) und Frequenzspektrum (FFT).
Diese Daten werden anschliessend verwendet um Farben, Helligkeit und Bewegungen der LEDs zu steuern.