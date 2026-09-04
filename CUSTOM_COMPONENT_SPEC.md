# Viessmann Zirkulationsplan für Home Assistant

## 1. Ziel

Eine eigenständige Home-Assistant-Custom-Component steuert die Warmwasser-Zirkulationspumpe einer Viessmann Vitocal 222-G über die Viessmann Climate Solutions API.

Die Viessmann-API bietet keinen unmittelbaren Schaltbefehl für die Zirkulationspumpe. Die Steuerung erfolgt daher durch das Schreiben vollständiger Wochenzeitpläne an den API-Datenpunkt:

```text
heating.dhw.pumps.circulation.schedule
```

Die erste Version bietet drei feste Presets:

| Preset | Montag bis Freitag | Samstag und Sonntag |
|---|---|---|
| `Standard` | 17:00 bis 22:00 | 07:30 bis 23:00 |
| `Ganztägig` | 00:00 bis 24:00 | 00:00 bis 24:00 |
| `Aus` | Keine Zeitfenster | Keine Zeitfenster |

Die Auswahl soll manuell im Home-Assistant-Dashboard und automatisiert über Home-Assistant-Automationen möglich sein.

## 2. Abgrenzung

### Bestandteil der ersten Version

- OAuth2-Anmeldung über einen eigenen Viessmann-Developer-Client.
- Automatische Ermittlung von Installation, Gateway und Heizgerät.
- Lesen des aktuellen Zirkulationszeitplans.
- Setzen eines der drei festen Presets.
- Anzeige des tatsächlich gemeldeten Pumpenstatus.
- Anzeige des aktuell gelesenen Schedule-JSON als Diagnoseinformation.
- Erkennung, ob der aktuelle API-Zeitplan einem bekannten Preset entspricht.
- Unterstützung für Home-Assistant-Neustarts, Token-Refresh, API-Fehler und Offline-Geräte.
- HACS-kompatibles Repository.

### Nicht Bestandteil der ersten Version

- Bearbeitung oder Neuerstellung von Zeitplänen im Home-Assistant-Frontend.
- Frei konfigurierbare Presets.
- Temporäres Einschalten für eine Laufzeit.
- Eigene Solar-, Anwesenheits- oder Urlaubsautomationen.
- Änderungen an der bestehenden offiziellen ViCare-Core-Integration.
- Aufnahme in Home Assistant Core.
- Behauptungen oder Regelungen zum Legionellenschutz.

Automationen zur Auswahl der Presets werden außerhalb der Custom Component in Home Assistant umgesetzt.

## 3. API-Erkenntnisse

### 3.1 Geräte-API

Die aktuelle Feature-API verwendet Version 2:

```text
https://api.viessmann-climatesolutions.com/iot/v2/features/
```

Die Gerätehierarchie wird über folgende Endpunkte ermittelt:

```text
GET /iot/v2/equipment/installations
GET /iot/v2/equipment/gateways
GET /iot/v2/equipment/installations/{installation_id}/gateways/{gateway_serial}/devices
```

Als Zielgerät wird das Gerät mit folgendem Wert verwendet:

```json
{
  "deviceType": "heating"
}
```

Es darf nicht angenommen werden, dass die Heizungs-Geräte-ID immer `0` ist. Die Component muss die Geräte-ID aus dem API-Ergebnis ermitteln.

### 3.2 Pumpenstatus

Der aktuelle gemeldete Status der Warmwasser-Zirkulationspumpe wird über dieses Feature gelesen:

```text
GET /iot/v2/features/installations/{installation_id}/gateways/{gateway_serial}/devices/{device_id}/features/heating.dhw.pumps.circulation
```

Relevanter Antwortauszug:

```json
{
  "feature": "heating.dhw.pumps.circulation",
  "isEnabled": true,
  "isReady": true,
  "properties": {
    "status": {
      "type": "string",
      "value": "on"
    }
  },
  "commands": {}
}
```

Mögliche Werte müssen nicht auf `on` und `off` begrenzt werden. Unbekannte Werte sind als unbekannter Entity-Zustand abzubilden und zu protokollieren.

### 3.3 Zirkulationszeitplan

Der aktuelle Wochenplan wird über diesen Endpunkt gelesen:

```text
GET /iot/v2/features/installations/{installation_id}/gateways/{gateway_serial}/devices/{device_id}/features/heating.dhw.pumps.circulation.schedule
```

Der zurückgegebene Wert befindet sich unter:

```text
data.properties.entries.value
```

Relevante Feature-Eigenschaften:

```json
{
  "feature": "heating.dhw.pumps.circulation.schedule",
  "isEnabled": true,
  "isReady": true,
  "properties": {
    "entries": {
      "type": "Schedule",
      "value": {}
    },
    "active": {
      "type": "boolean",
      "value": true
    }
  }
}
```

### 3.4 Zeitplan schreiben

Der API-Command lautet:

```text
POST /iot/v2/features/installations/{installation_id}/gateways/{gateway_serial}/devices/{device_id}/features/heating.dhw.pumps.circulation.schedule/commands/setSchedule
```

Request-Header:

```http
Authorization: Bearer {access_token}
Content-Type: application/json
Accept: application/json
```

Request-Body:

```json
{
  "newSchedule": {
    "mon": [],
    "tue": [],
    "wed": [],
    "thu": [],
    "fri": [],
    "sat": [],
    "sun": []
  }
}
```

Die API meldet derzeit folgende Constraints:

```json
{
  "modes": ["5/25-cycles", "5/10-cycles", "on"],
  "maxEntries": 8,
  "resolution": 10,
  "defaultMode": "off",
  "overlapAllowed": true
}
```

Der von ViCare konfigurierte und erfolgreich ausgelesene Plan enthält allerdings `07:30`. Die Component darf daher nicht selbst erzwingen, dass Uhrzeiten ausschließlich in 10-Minuten-Schritten liegen. Sie überträgt die fest hinterlegten API-Werte unverändert.

Weitere erkennbare Commands:

```text
resetSchedule
resetDay
```

Diese Commands werden in Version 1 nicht verwendet, da sie eine unbekannte werkseitige Konfiguration wiederherstellen oder einzelne Wochentage verändern könnten.

## 4. Feste Preset-Daten

Die Presets werden in Version 1 im Quellcode als unveränderliche Daten definiert.

### 4.1 Standard

```json
{
  "mon": [{ "start": "17:00", "end": "22:00", "mode": "on", "position": 0 }],
  "tue": [{ "start": "17:00", "end": "22:00", "mode": "on", "position": 0 }],
  "wed": [{ "start": "17:00", "end": "22:00", "mode": "on", "position": 0 }],
  "thu": [{ "start": "17:00", "end": "22:00", "mode": "on", "position": 0 }],
  "fri": [{ "start": "17:00", "end": "22:00", "mode": "on", "position": 0 }],
  "sat": [{ "start": "07:30", "end": "23:00", "mode": "on", "position": 0 }],
  "sun": [{ "start": "07:30", "end": "23:00", "mode": "on", "position": 0 }]
}
```

### 4.2 Ganztägig

```json
{
  "mon": [{ "start": "00:00", "end": "24:00", "mode": "on", "position": 0 }],
  "tue": [{ "start": "00:00", "end": "24:00", "mode": "on", "position": 0 }],
  "wed": [{ "start": "00:00", "end": "24:00", "mode": "on", "position": 0 }],
  "thu": [{ "start": "00:00", "end": "24:00", "mode": "on", "position": 0 }],
  "fri": [{ "start": "00:00", "end": "24:00", "mode": "on", "position": 0 }],
  "sat": [{ "start": "00:00", "end": "24:00", "mode": "on", "position": 0 }],
  "sun": [{ "start": "00:00", "end": "24:00", "mode": "on", "position": 0 }]
}
```

### 4.3 Aus

```json
{
  "mon": [],
  "tue": [],
  "wed": [],
  "thu": [],
  "fri": [],
  "sat": [],
  "sun": []
}
```

## 5. Architektur

### 5.1 Repository-Struktur

```text
ha-vicare-circulation/
├── custom_components/
│   └── vicare_circulation/
│       ├── __init__.py
│       ├── api.py
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── manifest.json
│       ├── select.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── strings.json
│       └── translations/
│           ├── de.json
│           └── en.json
├── tests/
│   └── components/
│       └── vicare_circulation/
│           ├── __init__.py
│           ├── conftest.py
│           ├── fixtures/
│           ├── test_api.py
│           ├── test_config_flow.py
│           ├── test_coordinator.py
│           ├── test_select.py
│           └── test_sensor.py
├── hacs.json
├── README.md
├── LICENSE
├── pyproject.toml
└── requirements_test.txt
```

Der endgültige Domain-Name soll vor der Implementierung geprüft werden. `vicare_circulation` ist verständlich, darf aber nicht mit der offiziellen Core-Integration `vicare` kollidieren oder Verwechslungen bei Konfiguration und Logging erzeugen.

### 5.2 Plattformen

```python
PLATFORMS = [
    Platform.SELECT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]
```

### 5.3 Asynchronität

- Ausschließlich asynchrone I/O über `aiohttp` und den von Home Assistant bereitgestellten `aiohttp.ClientSession` verwenden.
- Keine blockierenden HTTP-Aufrufe.
- Keine Verwendung von `requests`.
- Keine handgeführten Hintergrund-Threads.
- API-Zugriffe über einen `DataUpdateCoordinator` zentralisieren.
- Plan-Schreibvorgänge mit einem `asyncio.Lock` pro Config Entry serialisieren.

### 5.4 Aktualisierungsintervall

Das Standardintervall soll zunächst 5 Minuten betragen.

Beim Start der Integration erfolgt ein unmittelbarer Abruf. Nach einer Preset-Auswahl erfolgt direkt nach dem erfolgreichen POST ein erneuter GET-Abruf.

Ein niedrigeres Intervall ist nicht notwendig, da der Zirkulationsplan selten geändert wird und die Component keine Echtzeitsteuerung erfordert.

## 6. OAuth2 und Authentifizierung

### 6.1 Grundsatz

Die Custom Component nutzt einen eigenen Viessmann-Developer-Client. Sie verwendet nicht die internen Authentifizierungsdaten der offiziellen ViCare-Core-Integration.

Diese Entkopplung verhindert Abhängigkeiten von privaten Implementierungsdetails, Versionskonflikte und unklare Token-Verantwortlichkeiten.

### 6.2 OAuth-Verfahren

- OAuth 2.0 Authorization Code Flow mit PKCE.
- Viessmann-Autorisierungsendpunkt:

```text
https://iam.viessmann-climatesolutions.com/idp/v3/authorize
```

- Viessmann-Token-Endpunkt:

```text
https://iam.viessmann-climatesolutions.com/idp/v3/token
```

- Erforderlicher Scope:

```text
IoT User offline_access
```

- Client Secret ist für diesen Public-Client-Flow leer.
- Der PKCE-Code-Verifier darf nicht fest hinterlegt sein. Er muss pro Anmeldevorgang kryptographisch sicher erzeugt werden.
- Der Code Challenge Method ist `S256`.

### 6.3 Callback-URI

Die in Viessmann Developer Portal hinterlegte Redirect URI muss genau dem von Home Assistant verwendeten OAuth-Callback entsprechen.

Die Integration soll Home Assistants bestehende OAuth2-Mechanismen verwenden, insbesondere `config_entry_oauth2_flow` und Application Credentials, sofern dies für Custom Components technisch vollständig unterstützt wird.

Vor Implementierung muss in einer Testinstanz bestätigt werden:

- Welche konkrete Callback-URI Home Assistant für die Component verwendet.
- Ob der eigene Client im Viessmann Developer Portal mehrere Redirect URIs unterstützt.
- Ob die Callback-URI extern erreichbar sein muss oder der Home-Assistant-Redirect-Dienst verwendet werden kann.
- Ob Viessmann den OAuth-Rücksprung bei der Home-Assistant-OS-VM zuverlässig akzeptiert.

### 6.4 Geheimnisse

Folgende Daten gelten als Geheimnisse und dürfen nicht geloggt, in Diagnoseinformationen ausgegeben oder committed werden:

- ViCare-Passwort.
- OAuth Authorization Code.
- Access Token.
- Refresh Token.
- HTTP-Cookies.
- Client Secret, falls Viessmann künftig eines vergibt.

Die Client-ID kann in der Config Entry gespeichert werden, soll jedoch ebenfalls nicht unnötig in Logs erscheinen.

## 7. Datenmodell

### 7.1 Laufzeitdaten

Der `DataUpdateCoordinator` hält mindestens folgende Daten:

```python
@dataclass
class CirculationData:
    installation_id: str
    gateway_serial: str
    device_id: str
    device_serial: str | None
    model: str | None
    schedule: dict[str, list[dict[str, str | int]]]
    schedule_active: bool | None
    pump_status: str | None
    schedule_feature_enabled: bool
    schedule_feature_ready: bool
    pump_feature_enabled: bool
    pump_feature_ready: bool
    last_update_success: datetime
```

Die IDs müssen aus der Laufzeitdarstellung ferngehalten werden, soweit sie in Entity-Attributen oder Diagnoseausgaben erscheinen könnten.

### 7.2 Vergleich von Zeitplänen

Für die Preset-Erkennung muss der aktuelle API-Plan mit den drei Presets verglichen werden.

Der Vergleich muss semantisch stabil sein:

- Alle sieben Wochentage `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun` müssen berücksichtigt werden.
- Fehlende Wochentage und leere Listen müssen normalisiert werden.
- Dictionary-Reihenfolgen dürfen das Ergebnis nicht beeinflussen.
- Einträge sollen vor dem Vergleich anhand von `position`, `start`, `end` und `mode` sortiert werden.
- Zusätzliche API-Metadaten dürfen nicht Teil des Vergleichs sein.
- Der Vergleich erfolgt ausschließlich auf dem Wert unter `properties.entries.value`.

Das Ergebnis ist genau einer der folgenden Zustände:

```text
standard
all_day
off
custom
unknown
```

`unknown` wird verwendet, wenn kein valider Zeitplan gelesen werden konnte. `custom` bedeutet, dass ein valider, aber keinem Preset entsprechender ViCare-Zeitplan vorliegt.

## 8. Entities

### 8.1 Select: Zirkulationszeitplan

Vorgeschlagene Entity-ID:

```text
select.<geraet>_warmwasser_zirkulation_zeitplan
```

Anzeigetitel:

```text
Warmwasser-Zirkulation Zeitplan
```

Optionen:

```text
Standard
Ganztägig
Aus
```

Zustandsregeln:

| API-Plan | Select-Zustand |
|---|---|
| Entspricht `Standard` | `Standard` |
| Entspricht `Ganztägig` | `Ganztägig` |
| Entspricht `Aus` | `Aus` |
| Gültig, aber keinem Preset entsprechend | `Benutzerdefiniert` oder `unknown` |
| API nicht verfügbar | `unavailable` |
| Ungültige API-Antwort | `unknown` |

Für Home-Assistant-Select-Entities sollten nur auswählbare Werte in `options` stehen. Daher ist bevorzugt:

- `options`: `Standard`, `Ganztägig`, `Aus`
- Zustand bei einem abweichenden Plan: `unknown`
- Zusätzliches Attribut `detected_schedule`: `Benutzerdefiniert`

Alternativ kann `Benutzerdefiniert` als nicht auswählbare Zustandsdarstellung über eine separate Sensor-Entity erfolgen. Es darf nicht als auswählbare Select-Option implementiert werden, wenn dafür keine Schreiblogik existiert.

Bei `async_select_option(option)`:

1. Option in internes Preset abbilden.
2. Schreibsperre erwerben.
3. Aktuellen Token sicherstellen beziehungsweise erneuern.
4. Vollständigen Preset-Plan per `setSchedule` senden.
5. Bei HTTP- oder API-Fehler: Ausnahme auslösen, kein lokales Umschalten.
6. Nach erfolgreicher API-Antwort einen Coordinator-Refresh erzwingen.
7. Select-Zustand ausschließlich aus dem frisch gelesenen API-Plan bestimmen.
8. Schreibsperre freigeben.

Die Component darf nach einem erfolgreichen POST nicht allein aufgrund der HTTP-Antwort behaupten, der Zeitplan sei aktiviert.

### 8.2 Binary Sensor: Pumpenstatus

Vorgeschlagene Entity-ID:

```text
binary_sensor.<geraet>_warmwasser_zirkulation_aktiv
```

Anzeigetitel:

```text
Warmwasser-Zirkulation aktiv
```

Device Class:

```text
running
```

Zustandszuordnung:

| API-Wert | Binary Sensor |
|---|---|
| `on` | `on` |
| `off` | `off` |
| Fehlend oder unbekannt | `unknown` |
| Feature deaktiviert oder API nicht erreichbar | `unavailable` |

Die Entity repräsentiert ausschließlich den von Viessmann gemeldeten aktuellen Status. Sie darf nicht aus dem ausgewählten Zeitplan abgeleitet werden.

### 8.3 Sensor: Erkannter Zeitplan

Vorgeschlagene Entity-ID:

```text
sensor.<geraet>_warmwasser_zirkulation_zeitplan_status
```

Anzeigetitel:

```text
Warmwasser-Zirkulation Zeitplanstatus
```

Zustände:

```text
Standard
Ganztägig
Aus
Benutzerdefiniert
Unbekannt
```

Diese Entity verhindert, dass ein abweichender, in ViCare geänderter Plan als eines der bekannten Presets dargestellt wird.

### 8.4 Sensor: API-Diagnoseplan

Vorgeschlagene Entity-ID:

```text
sensor.<geraet>_warmwasser_zirkulation_api_plan
```

Anzeigetitel:

```text
Warmwasser-Zirkulation API-Plan
```

Der Hauptzustand soll kurz und stabil bleiben, etwa:

```text
available
```

Der ausgelesene Wochenplan wird als Attribut abgelegt:

```json
{
  "schedule": {
    "mon": [],
    "tue": [],
    "wed": [],
    "thu": [],
    "fri": [],
    "sat": [],
    "sun": []
  },
  "schedule_active": true,
  "feature_enabled": true,
  "feature_ready": true,
  "last_successful_update": "2026-09-03T..."
}
```

OAuth-Tokens, Installations-ID, Gateway-Seriennummer, Geräte-ID und Seriennummern dürfen nicht als Entity-Attribute ausgegeben werden.

## 9. Fehlermanagement

### 9.1 API- und Netzwerkfehler

| Situation | Verhalten |
|---|---|
| Gateway nicht erreichbar | Entities `unavailable`, erneuter Abruf beim nächsten Coordinator-Zyklus |
| Timeout | Abruf als fehlgeschlagen markieren, keine Wiederholungsschleife ohne Begrenzung |
| HTTP 401 oder 403 | Token erneuern; bei endgültigem Fehler Reauthentifizierung anfordern |
| HTTP 429 | API-Rate-Limit protokollieren, Retry über nächstes reguläres Update, kein aggressives Polling |
| HTTP 5xx | Vorübergehender Fehler, Entities unverfügbar oder letzter bekannter Zustand nach Home-Assistant-Konvention |
| Feature nicht vorhanden | Setup mit klarer Fehlermeldung abbrechen oder die betroffenen Entities nicht erzeugen |
| `isEnabled: false` | Betroffene Entities als `unavailable` behandeln |
| `isReady: false` | Betroffene Entities als `unavailable` behandeln |
| Ungültige JSON-Struktur | Fehlermeldung mit struktureller Information, aber ohne Geheimnisse; Zustand `unknown` |

### 9.2 Schreibfehler

Wenn `setSchedule` fehlschlägt:

- Kein lokales Umschalten der Select-Entity.
- Fehler als `HomeAssistantError` mit verständlicher, übersetzter Meldung ausgeben.
- Kein automatischer Fallback auf `resetSchedule`.
- Kein automatischer Wiederholungssturm.
- Der vorherige, durch einen erfolgreichen GET bestätigte Zeitplan bleibt sichtbar.
- Der fehlgeschlagene Request muss in Debug-Logs nur mit Preset-Name, Statuscode und gekürzter Fehlerursache erscheinen, niemals mit Token.

### 9.3 Externe Änderungen in ViCare

Wenn der Plan in ViCare oder durch einen anderen API-Client verändert wird:

- Beim nächsten Refresh Plan neu lesen.
- Plan mit allen bekannten Presets vergleichen.
- Bei Abweichung Zeitplanstatus auf `Benutzerdefiniert` setzen.
- Select-Zustand auf `unknown` setzen.
- Keine automatische Wiederherstellung oder Überschreibung.
- Die nächste bewusste Auswahl im Select ersetzt den individuellen Plan vollständig mit dem gewünschten Preset.

## 10. Config Flow

### 10.1 Initiale Einrichtung

1. Nutzer wählt die Integration in Home Assistant aus.
2. Nutzer gibt die Viessmann Client-ID des eigenen Developer-Clients ein, falls Application Credentials nicht verwendet werden können.
3. OAuth2-Autorisierung in Viessmann.
4. Token austauschen und sicher speichern.
5. Installationen abrufen.
6. Bei mehreren Installationen Auswahl anbieten.
7. Zugehörige Gateways abrufen.
8. Bei mehreren Heizungs-Gateways Auswahl anbieten.
9. Geräte abrufen und Gerät mit `deviceType: "heating"` auswählen.
10. Zirkulations-Schedule-Feature abrufen.
11. Prüfen, ob Feature aktiviert, bereit und der Command `setSchedule` ausführbar ist.
12. Config Entry anlegen.
13. Plattformen laden und ersten Coordinator-Refresh durchführen.

### 10.2 Fehler im Config Flow

- Keine Installation: verständliche Fehlermeldung.
- Mehrere Installationen oder Gateways: Auswahl nicht automatisch erraten.
- Kein Gerät mit `deviceType: "heating"`: Setup abbrechen.
- Schedule-Feature fehlt: Setup abbrechen, da dies die Kernfunktion ist.
- Feature ist deaktiviert oder Command ist nicht ausführbar: Setup abbrechen und auf ViCare-/Gerätekonfiguration verweisen.
- OAuth-Ablehnung: erneuten Autorisierungsversuch anbieten.
- Netzwerkfehler: Flow darf erneut versucht werden, ohne unvollständigen Entry zu erzeugen.

### 10.3 Reconfigure und Reauth

Die Component soll unterstützen:

- Reauthentifizierung bei abgelaufenen oder widerrufenen Tokens.
- Änderung der Client-ID, falls erforderlich.
- Neuauswahl von Installation, Gateway und Heizgerät.
- Erneute Funktionsprüfung des Schedule-Features.

Eine Preset-Bearbeitung ist nicht Teil des Reconfigure-Flows der ersten Version.

## 11. Geräte- und Entity-Registrierung

Die Component soll eine eigene Device-Registry-Entität anlegen.

Vorgeschlagene Geräteinformationen:

- Hersteller: `Viessmann`
- Modell: Aus der Geräte-API, falls vorhanden
- Name: `Viessmann Warmwasser-Zirkulation`
- Seriennummer: Nur lokal in der Device Registry, sofern durch die API verfügbar
- Verbindung: Verweis auf die eigene Config Entry

Falls die offizielle ViCare-Core-Integration gleichzeitig aktiv ist, ist ein gemeinsames Device-Registry-Gerät nicht zwingend möglich, weil die Domains verschieden sind. Die Component darf keine bestehenden ViCare-Geräte verändern.

## 12. Logging und Diagnose

### 12.1 Log-Level

- `DEBUG`: API-Operation, Feature-Name, HTTP-Status, Preset-Name, erkannter Zeitplanstatus.
- `INFO`: Erfolgreicher Wechsel eines Presets und erfolgreiche Reauthentifizierung.
- `WARNING`: API-Rate-Limit, unbekannter Pumpenstatus, externer benutzerdefinierter Plan.
- `ERROR`: Nicht behebbarer Setup- oder API-Fehler.

### 12.2 Redaction

Die folgenden Felder müssen in Logs und Diagnosen entfernt oder maskiert werden:

```text
Authorization
access_token
refresh_token
id_token
password
cookie
set-cookie
installation_id
gateway_serial
device_id
serial number
```

Die Diagnoseausgabe darf die bereinigte Struktur des Schedule-Features und dessen Constraints enthalten, weil sie für Fehleranalyse relevant sind.

## 13. Tests

### 13.1 API-Client-Tests

- Ermittlung einer Installation, eines Gateways und eines `heating`-Geräts.
- Mehrere Installationen und korrekte Nutzerauswahl.
- Mehrere Heizgeräte und korrekte Nutzerauswahl.
- Lesen des Pumpenstatus `on`.
- Lesen des Pumpenstatus `off`.
- Lesen eines unbekannten Pumpenstatus.
- Lesen des Standard-, Ganztägig- und Aus-Plans.
- Schreiben jedes der drei Presets.
- Request-Body ist exakt `{"newSchedule": <preset>}`.
- API-Endpunkt verwendet `/iot/v2/features`.
- HTTP 401, 403, 404, 429 und 5xx.
- Ungültiges oder unvollständiges JSON.
- Feature `isEnabled: false`.
- Feature `isReady: false`.
- `setSchedule.isExecutable: false`.

### 13.2 Preset-Vergleichstests

- Standard wird korrekt erkannt.
- Ganztägig wird korrekt erkannt.
- Aus wird korrekt erkannt.
- Abweichender Zeitplan wird als `custom` erkannt.
- Unterschiedliche JSON-Key-Reihenfolgen ändern das Ergebnis nicht.
- Fehlende Wochentage werden mit leeren Listen normalisiert.
- Mehrere Einträge pro Tag werden deterministisch sortiert.
- API-Metadaten beeinflussen die Erkennung nicht.
- Zeitwert `07:30` ist zulässig und darf nicht abgewiesen werden.
- Zeitwert `24:00` ist zulässig und darf nicht in `00:00` umgewandelt werden.

### 13.3 Entity-Tests

- Select enthält exakt die drei auswählbaren Presets.
- Select setzt Zustand erst nach erfolgreichem Refresh.
- Fehlgeschlagener Schreibvorgang verändert den Select-Zustand nicht.
- Pumpenstatus wird korrekt als Binary Sensor abgebildet.
- Benutzerdefinierter ViCare-Plan zeigt `unknown` im Select und `Benutzerdefiniert` im Statussensor.
- Diagnose-Sensor enthält den Zeitplan, aber keine IDs oder Tokens.
- Entities werden bei nicht verfügbarem Feature als `unavailable` abgebildet.

### 13.4 Config-Flow-Tests

- Erfolgreicher OAuth-Flow.
- Abgebrochene OAuth-Autorisierung.
- Abgelaufener Token führt zu Reauth.
- Fehlendes Schedule-Feature verhindert Setup.
- Mehrfaches Einrichten derselben Anlage wird verhindert.
- Reconfigure aktualisiert die Zielgeräteauswahl.

### 13.5 Manuelle Integrationstests

In einer Home-Assistant-Testumgebung:

1. `Standard` in ViCare einstellen.
2. Component installieren und Einrichtung abschließen.
3. Prüfen, ob Select `Standard` und Statussensor `Standard` anzeigen.
4. Im Dashboard `Ganztägig` auswählen.
5. API-Plan über Postman lesen und mit `ganztag.json` vergleichen.
6. Änderung in ViCare prüfen.
7. Im Dashboard `Aus` auswählen.
8. API-Plan mit `aus.json` vergleichen.
9. In ViCare einen absichtlich abweichenden Plan konfigurieren.
10. Prüfen, ob Select `unknown` und Statussensor `Benutzerdefiniert` zeigt.
11. Home Assistant neu starten.
12. Prüfen, ob OAuth-Token, Gerätezuordnung und Entity-Zustände korrekt wiederhergestellt werden.
13. Gateway vorübergehend vom Netzwerk trennen.
14. Prüfen, ob die Entities nachvollziehbar `unavailable` werden und nach Wiederverbindung zurückkehren.

## 14. HACS und Dokumentation

Das Repository soll als HACS Custom Repository installiert werden können.

Erforderliche Dokumentation in `README.md`:

- Zweck und Funktionsumfang.
- Unterstützte API-Funktion.
- Hinweis: Es wird ein eigener Viessmann-Developer-Client benötigt.
- Schritt-für-Schritt-Anleitung zur Anlage des Clients.
- Exakte benötigte Redirect URI.
- OAuth-Scopes.
- Installationsanleitung über HACS.
- Manuelle Installation unter `custom_components`.
- Neustart- und Einrichtungsschritte.
- Entity-Liste.
- Beispiele für Automation und Dashboard.
- Erklärung der Zustände `Standard`, `Ganztägig`, `Aus`, `Benutzerdefiniert` und `Unbekannt`.
- Fehlerbehebung bei OAuth, API-Rate-Limits und nicht verfügbarem Gateway.
- Klarstellung, dass die Component nur den Zirkulations-Zeitplan verwaltet und keine Aussagen zum hygienischen Betrieb der Trinkwasserinstallation trifft.

Beispielautomation für Urlaub:

```yaml
alias: Zirkulation bei Urlaub ausschalten
triggers:
  - trigger: state
    entity_id: input_boolean.urlaub
    to: "on"
actions:
  - action: select.select_option
    target:
      entity_id: select.viessmann_warmwasser_zirkulation_zeitplan
    data:
      option: Aus
mode: single
```

Beispielautomation für Anwesenheit:

```yaml
alias: Standardplan bei Anwesenheit setzen
triggers:
  - trigger: state
    entity_id: person.beispiel
    to: home
actions:
  - action: select.select_option
    target:
      entity_id: select.viessmann_warmwasser_zirkulation_zeitplan
    data:
      option: Standard
mode: single
```

## 15. Abnahmekriterien

Die erste Version gilt als abgenommen, wenn alle folgenden Kriterien erfüllt sind:

1. Die Custom Component lässt sich über HACS oder manuell in Home Assistant OS installieren.
2. Die Anmeldung über den eigenen Viessmann-Developer-Client funktioniert ohne Speicherung von Passwörtern.
3. Installation, Gateway und Heizgerät werden korrekt erkannt oder auswählbar angeboten.
4. Der aktuelle Zirkulationsplan wird korrekt gelesen.
5. Die Select-Entity zeigt bei allen drei Referenzplänen das korrekte Preset an.
6. Die Auswahl eines Presets schreibt genau den erwarteten vollständigen Wochenplan.
7. Ein anschließender API-Read bestätigt die geschriebene Konfiguration.
8. Der aktuelle Pumpenstatus wird separat und korrekt angezeigt.
9. Ein über ViCare abweichend eingestellter Plan wird als `Benutzerdefiniert` erkannt und nicht überschrieben.
10. API-Fehler, nicht erreichbares Gateway und abgelaufene Tokens führen nicht zu falschen Zuständen oder unkontrollierten Wiederholungen.
11. In Logdateien, Entity-Attributen und Diagnosen sind keine OAuth-Tokens, Passwörter oder Installationskennungen enthalten.
12. Unit-Tests und manuelle Tests in der Testumgebung sind erfolgreich.