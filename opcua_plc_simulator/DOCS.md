# Home Assistant Add-on: OPC UA PLC Simulator

## Installation

1. Lege dieses Repository in GitHub ab.
2. In Home Assistant: **Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories**
3. Repository-URL eintragen.
4. Add-on **OPC UA PLC Simulator** installieren und starten.

## Optionen

- `config_file` (String): Pfad zur YAML-Datei, Standard `/config/opcua_plc_simulator.yaml`
- `auto_create_example` (Bool): Erstellt eine Beispiel-YAML, falls Datei fehlt

Beispieldatei im Repo: `opcua_plc_simulator.example.yaml`

## YAML-Templates (fertig)

Im Add-on Repo enthalten:

- `templates/packml_basic.yaml`
- `templates/alarms_process.yaml`
- `templates/stacklight_only.yaml`
- `templates/stacklight_alarm.yaml`
- `templates/motor_axis.yaml`

Starte z. B. mit dem PackML-Template und kopiere es nach `/config/opcua_plc_simulator.yaml`.

## YAML-Konfiguration

```yaml
server:
  endpoint: opc.tcp://0.0.0.0:4840
  namespace_uri: urn:homeassistant:opcua:plc-simulator
  tick_ms: 500

model:
  root: Machine
  variables:
    - name: Running
      path: Machine/Running
      type: bool
      initial: false
      writable: true
      simulation:
        mode: toggle
        interval_ms: 3000

    - name: Temperature
      path: Machine/Temperature
      type: float
      initial: 42.0
      writable: true
      simulation:
        mode: random_walk
        min: 20
        max: 110
        step: 1.5
        interval_ms: 1000
```

### Typen

- `bool`
- `int`
- `float`
- `string`

### Simulationsmodi

- `toggle` (bool)
- `random_walk` (int/float)
- `random_choice` (alle Typen, via `values`)
- `cycle` (alle Typen, via `values`)
- `ramp` (int/float)
- `sine` (float)

## In Home Assistant integrieren

Mit deiner Custom Integration `opcua_machine`:

- Endpoint: `opc.tcp://<HA-Host-IP>:4840`
- Dann über Optionen/Browser oder Auto-Discovery Nodes importieren.

## Hinweis

Dies ist ein Test-/Entwicklungs-Simulator, keine Safety-SPS.
