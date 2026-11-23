# King Smith WalkingPad für Home Assistant

[![Validate](https://github.com/DapDallas/king_smith_laufband/actions/workflows/validate.yml/badge.svg)](https://github.com/DapDallas/king_smith_laufband/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/DapDallas/king_smith_laufband)](https://github.com/DapDallas/king_smith_laufband/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)

Lokale Steuerung von King-Smith-/WalkingPad-Laufbändern per Bluetooth. Kein Cloud-Zugriff, keine Hersteller-App nötig.

Dieses Repo ist ein gepflegter Fork von [indiefan/king_smith](https://github.com/indiefan/king_smith), überarbeitet für aktuelle Home-Assistant-Versionen.

## Funktionen

| Entity | Beschreibung |
|---|---|
| Schalter | Laufband starten / stoppen |
| Geschwindigkeit (Number) | Zielgeschwindigkeit in km/h setzen |
| Geschwindigkeit, Distanz, Dauer, Schritte, Schrittfrequenz | Werte der aktuellen Sitzung |
| Gesamtdistanz, Gesamtzeit, Schritte gesamt | Zählen über alle Sitzungen und Neustarts hinweg, geeignet für Langzeitstatistiken |

Dazu:

- **Geräte-Trigger** *Sitzung gestartet* und *Sitzung beendet* für Automationen. Das Event `king_smith_session_done` enthält Dauer, Schritte, Distanz, Ø-Geschwindigkeit und Ø-Schrittfrequenz.
- **Live-Werte:** Läuft das Band, wird jede Sekunde abgefragt, im Ruhezustand im eingestellten Intervall (Standard 5 s).
- **Diagnose-Download** für Fehlerberichte.
- Läuft über die Bluetooth-Anbindung von Home Assistant, also auch über **ESPHome-Bluetooth-Proxys**. Keine zusätzlichen Python-Pakete.

## Voraussetzungen

- Home Assistant **2025.1** oder neuer
- Bluetooth in Home Assistant: ein lokaler Adapter oder ein [ESP32 als Bluetooth-Proxy](https://esphome.io/components/bluetooth_proxy.html) in Reichweite des Laufbands
- Das Laufband ist **nicht** mit einem anderen Gerät verbunden (Handy-App, Mac, ...). Es akzeptiert nur eine Bluetooth-Verbindung gleichzeitig.

## Installation über HACS

1. HACS öffnen, oben rechts Menü (drei Punkte) → **Benutzerdefinierte Repositories**.
2. `https://github.com/DapDallas/king_smith_laufband` eintragen, Typ **Integration**.
3. **King Smith Walking Pad** herunterladen und Home Assistant neu starten.

Updates erscheinen danach automatisch in HACS.

## Manuelle Installation

Den Ordner `custom_components/king_smith` aus dem [neuesten Release](https://github.com/DapDallas/king_smith_laufband/releases/latest) in das Konfigurationsverzeichnis von Home Assistant kopieren (dort, wo `configuration.yaml` liegt) und neu starten.

| Zugriff | Pfad |
|---|---|
| Home Assistant OS, Add-ons (SSH, File editor, Studio Code Server) | `/homeassistant/custom_components/king_smith` |
| Home Assistant Core/Container, Samba-Share `config` | `/config/custom_components/king_smith` |

## Einrichtung

1. **Einstellungen → Geräte & Dienste.** Wird das Laufband per Bluetooth erkannt, erscheint es unter **Entdeckt**. Auf **Konfigurieren** klicken, Namen vergeben, fertig.
2. Erscheint nichts: **Integration hinzufügen → King Smith Walking Pad**. Ein gefundenes Laufband aus der Liste wählen oder die Bluetooth-Adresse (z. B. `AA:BB:CC:DD:EE:FF`) eintippen. Die Adresse zeigt Home Assistant unter **Einstellungen → Geräte & Dienste → Bluetooth → Konfigurieren → Advertisement Monitor** beim Gerät `WalkingPad` (oder `KS-...`).

Erkannt werden Geräte mit dem Bluetooth-Namen `WalkingPad`, `KS-BL*` und `KS-ST-*`.

### Optionen

Unter **Einstellungen → Geräte & Dienste → King Smith Walking Pad → Konfigurieren** lässt sich das Abfrageintervall im Ruhezustand einstellen (2–60 s). Das Laufband meldet seinen Status nur auf Anfrage, Änderungen am Gerät oder per Fernbedienung erscheinen also spätestens nach diesem Intervall.

## Hinweise

- **Laufband stoppt von selbst:** Steht niemand auf dem Band, schaltet es sich nach wenigen Sekunden ab (Sicherheitsfunktion des Geräts). Home Assistant zeigt das korrekt als *aus* an.
- **Ausgeschaltetes Laufband:** Die Entities sind dann *nicht verfügbar* und kommen nach dem Einschalten von selbst zurück.
- **Höchstgeschwindigkeit:** Die Geschwindigkeits-Entity geht bis 6 km/h.

## Fehlersuche

1. **Einstellungen → Geräte & Dienste → King Smith Walking Pad → ⋮ → Debug-Protokollierung aktivieren**, das Problem nachstellen, Debug-Protokollierung wieder ausschalten. Das Log wird heruntergeladen.
2. **⋮ → Diagnose herunterladen.**
3. Beides an ein [Issue](https://github.com/DapDallas/king_smith_laufband/issues) hängen.

## Getestet

- WalkingPad mit Bluetooth-Namen `WalkingPad` (Service `fe00`) mit aktuellem Home Assistant
- WalkingPad C2 und A1 Pro (laut Original-Projekt)

Läuft es mit einem weiteren Modell, gerne ein Issue anlegen.

## Entwicklung

```bash
python3.13 -m venv .venv && . .venv/bin/activate
pip install -r requirements_test.txt
pytest
```

Die Tests laufen gegen ein echtes Home Assistant mit simuliertem Laufband und werden bei jedem Push von GitHub Actions ausgeführt, zusammen mit `hassfest` und der HACS-Validierung.

## Credits und Lizenz

Original von [Marke Hallowell (indiefan)](https://github.com/indiefan/king_smith), auf Basis des [integration_blueprint](https://github.com/ludeeus/integration_blueprint). Das Bluetooth-Protokoll stammt aus [ph4-walkingpad](https://github.com/ph4r05/ph4-walkingpad). Lizenz: MIT, siehe [LICENSE](LICENSE).
