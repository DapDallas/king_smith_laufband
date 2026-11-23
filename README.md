# King Smith WalkingPad für Home Assistant

Lokale Steuerung von King-Smith-/WalkingPad-Laufbändern per Bluetooth. Kein Cloud-Zugriff, keine Hersteller-App nötig.

Dieses Repo ist ein gepflegter Fork von [indiefan/king_smith](https://github.com/indiefan/king_smith), angepasst an aktuelle Home-Assistant-Versionen.

## Funktionen

- **Schalter** für das Laufband (Start/Stop)
- **Number-Entity** für die Geschwindigkeit (km/h)
- **Sensoren** für Distanz, Dauer, Geschwindigkeit, Schritte und Schrittfrequenz der aktuellen Sitzung
- **Gesamtsensoren** für Distanz, Zeit und Schritte, die über Neustarts hinweg weiterzählen
- **Geräte-Trigger** `Sitzung gestartet` und `Sitzung beendet` für Automationen
- **Einstellbares Abfrageintervall** (Standard 5 s) unter *Konfigurieren*
- **Diagnose-Download** für Fehlerberichte

## Voraussetzungen

- Home Assistant **2025.1** oder neuer
- Bluetooth in Home Assistant: ein lokaler Adapter oder ein [ESP32 als Bluetooth-Proxy](https://esphome.io/components/bluetooth_proxy.html) in Reichweite des Laufbands
- Das Laufband ist an und **nicht** mit einem anderen Gerät verbunden (Handy-App, Mac, ...). Es akzeptiert nur eine BLE-Verbindung gleichzeitig.

## Installation über HACS

1. HACS öffnen, oben rechts Menü (drei Punkte) → **Benutzerdefinierte Repositories**.
2. `https://github.com/DapDallas/king_smith_laufband` eintragen, Kategorie **Integration**.
3. **King Smith Walking Pad** herunterladen und Home Assistant neu starten.

## Manuelle Installation

Den Ordner `custom_components/king_smith` in das Konfigurationsverzeichnis von Home Assistant kopieren (dort, wo `configuration.yaml` liegt) und neu starten.

| Zugriff | Pfad |
|---|---|
| Home Assistant OS, Add-ons (SSH, File editor, Studio Code Server) | `/homeassistant/custom_components/king_smith` |
| Home Assistant Core/Container, Samba-Share `config` | `/config/custom_components/king_smith` |

## Einrichtung

1. **Einstellungen → Geräte & Dienste.** Wird das Laufband per Bluetooth erkannt, erscheint es unter **Entdeckt**. Auf **Konfigurieren** klicken, einen Namen vergeben, fertig.
2. Erscheint nichts: **Integration hinzufügen → King Smith Walking Pad** und Name sowie Bluetooth-Adresse (MAC) manuell eintragen. Die Adresse zeigt Home Assistant unter **Einstellungen → Geräte & Dienste → Bluetooth → Konfigurieren → Advertisement Monitor** beim Gerät `WalkingPad` (oder `KS-...`).

Das Abfrageintervall lässt sich später unter **Einstellungen → Geräte & Dienste → King Smith Walking Pad → Konfigurieren** ändern. Das Laufband meldet seinen Status nur auf Anfrage; Änderungen am Gerät oder per Fernbedienung erscheinen spätestens nach diesem Intervall.

Erkannt werden Geräte mit dem Bluetooth-Namen `WalkingPad`, `KS-BL*` und `KS-ST-*`.

## Getestet

- WalkingPad C2 und A1 Pro (laut Original-Projekt)
- Einrichtung mit einem WalkingPad, das sich als `WalkingPad` mit Service `fe00` meldet (Protokoll aus [ph4-walkingpad](https://github.com/ph4r05/ph4-walkingpad))

Läuft es mit einem weiteren Modell, gerne ein Issue anlegen.

## Änderungen gegenüber dem Original

- Config-Flow an aktuelle Home-Assistant-Versionen angepasst (`ConfigFlowResult`, keine veraltete `CONNECTION_CLASS`), damit die Integration überhaupt geladen wird
- Manueller Einrichtungsschritt (Name und MAC), falls die Bluetooth-Erkennung nicht greift
- Deutsche und englische Texte für den Einrichtungsdialog
- Import von `UnitOfTime` auf `homeassistant.const` umgestellt
- Entwicklungsballast aus dem Template entfernt (Devcontainer, Skripte, Lint-Workflow)
- Eigene, schlanke Bluetooth-Anbindung über die BLE-Verbindung von Home Assistant (`bleak-retry-connector`, funktioniert auch über ESPHome-Proxys) statt `ph4-walkingpad`. Keine zusätzlichen Python-Pakete mehr nötig
- Ein zentrales Polling statt einer eigenen Abfrage pro Entity. Befehle werden sauber nacheinander gesendet
- Geräte-Trigger repariert (vorher schlug das Speichern der Automation fehl und die Events passten nie)
- Gesamtsensoren zählen nach einem Neustart nicht mehr doppelt
- Wechselt der Bluetooth-Adapter oder Proxy, wird das automatisch übernommen
- Entity-Namen übersetzt (de/en); Entity-IDs und Unique-IDs bleiben unverändert

## Credits und Lizenz

Original von [Marke Hallowell (indiefan)](https://github.com/indiefan/king_smith), auf Basis des [integration_blueprint](https://github.com/ludeeus/integration_blueprint). Die Bluetooth-Kommunikation übernimmt [ph4-walkingpad](https://github.com/ph4r05/ph4-walkingpad). Lizenz: MIT, siehe [LICENSE](LICENSE).
