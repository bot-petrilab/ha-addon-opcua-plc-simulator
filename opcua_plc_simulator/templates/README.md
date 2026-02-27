# OPC UA PLC Simulator Templates

Vordefinierte Modellvorlagen:

- `packml_basic.yaml` – PackML-nahe Zustände + KPI + Commands
- `alarms_process.yaml` – Alarm-/Warning-Kanal mit Ack/Reset
- `stacklight_only.yaml` – reine Signalleuchte (R/Y/G/B/W + Buzzer + Effect)
- `stacklight_alarm.yaml` – Stacklight + Alarmdaten kombiniert
- `motor_axis.yaml` – Servo-/Achsenprofil mit Position, Velocity, Torque, Fault

## Verwendung

1. Gewünschte Vorlage auswählen
2. Inhalt nach `/config/opcua_plc_simulator.yaml` kopieren
3. Add-on neu starten
