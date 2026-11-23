# King Smith WalkingPad für Home Assistant

Lokale Steuerung von King-Smith-/WalkingPad-Laufbändern per Bluetooth. Kein Cloud-Zugriff, keine Hersteller-App nötig.

Dieses Repo ist ein gepflegter Fork von [indiefan/king_smith](https://github.com/indiefan/king_smith), angepasst an aktuelle Home-Assistant-Versionen.

## Funktionen

- **Schalter** für das Laufband (Start/Stop)
- **Number-Entity** für die Geschwindigkeit (km/h)
- **Sensoren** für Distanz, Zeit, Geschwindigkeit und Schritte
- **Geräte-Trigger** `Sitzung gestartet` und `Sitzung beendet` für Automationen

## Voraussetzungen

- Home Assistant **2024.4** oder neuer
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

## Credits und Lizenz

Original von [Marke Hallowell (indiefan)](https://github.com/indiefan/king_smith), auf Basis des [integration_blueprint](https://github.com/ludeeus/integration_blueprint). Die Bluetooth-Kommunikation übernimmt [ph4-walkingpad](https://github.com/ph4r05/ph4-walkingpad). Lizenz: MIT, siehe [LICENSE](LICENSE).
