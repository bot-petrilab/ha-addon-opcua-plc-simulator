# HA Add-on Repository: OPC UA PLC Simulator

Dieses Repository enthält ein Home-Assistant Add-on:

- `opcua_plc_simulator` – YAML-konfigurierbarer OPC-UA PLC-Simulator

## Quick Start

1. In Home Assistant: **Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories**
2. Repository hinzufügen:
   - `https://github.com/bot-petrilab/ha-addon-opcua-plc-simulator`
3. Add-on **OPC UA PLC Simulator** installieren
4. Add-on starten
5. Optional: `/config/opcua_plc_simulator.yaml` anpassen (oder Auto-Beispiel verwenden)

Danach ist der OPC-UA Endpoint auf Port `4840` verfügbar.

## OPC-UA Integration testen (opcua_machine)

- Endpoint: `opc.tcp://<HA-Host-IP>:4840`
- Danach per Browser/Auto-Discovery Nodes importieren
