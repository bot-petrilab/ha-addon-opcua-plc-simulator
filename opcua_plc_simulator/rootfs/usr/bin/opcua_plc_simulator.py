#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import math
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from asyncua import Server


EXAMPLE_CONFIG = """server:
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

    - name: Alarm
      path: Machine/Alarm
      type: bool
      initial: false
      writable: true
      simulation:
        mode: random_choice
        values: [true, false, false, false]
        interval_ms: 4000

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

    - name: RPM
      path: Machine/RPM
      type: int
      initial: 0
      writable: true
      simulation:
        mode: ramp
        min: 0
        max: 3000
        step: 150
        interval_ms: 800

    - name: Mode
      path: Machine/Mode
      type: string
      initial: Idle
      writable: true
      simulation:
        mode: cycle
        values: [Idle, Setup, Auto, Alarm]
        interval_ms: 6000

    - name: StackLightGreen
      path: Machine/StackLight/Green
      type: bool
      initial: true
      writable: true

    - name: StackLightYellow
      path: Machine/StackLight/Yellow
      type: bool
      initial: false
      writable: true

    - name: StackLightRed
      path: Machine/StackLight/Red
      type: bool
      initial: false
      writable: true
"""


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _cast(dtype: str, value: Any) -> Any:
    dtype = str(dtype).lower().strip()
    if dtype in {"bool", "boolean"}:
        return _to_bool(value)
    if dtype in {"int", "integer", "int32", "int64", "uint16", "uint32"}:
        return int(float(value))
    if dtype in {"float", "double", "number"}:
        return float(value)
    return str(value)


@dataclass
class SimBinding:
    node: Any
    node_id: str
    dtype: str
    simulation: dict[str, Any]
    next_due: float
    cycle_index: int = 0
    phase: float = 0.0


class PlcSimulator:
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        self.server = Server()
        self.bindings: list[SimBinding] = []
        self.default_tick_ms = int(cfg.get("server", {}).get("tick_ms", 1000))

    async def setup(self) -> None:
        server_cfg = self.cfg.get("server", {})
        endpoint = server_cfg.get("endpoint", "opc.tcp://0.0.0.0:4840")
        namespace_uri = server_cfg.get("namespace_uri", "urn:homeassistant:opcua:plc-simulator")

        await self.server.init()
        self.server.set_endpoint(endpoint)
        ns_idx = await self.server.register_namespace(namespace_uri)

        print(f"[sim] Endpoint: {endpoint}")
        print(f"[sim] Namespace URI: {namespace_uri} (ns={ns_idx})")

        model = self.cfg.get("model", {})
        root_name = model.get("root", "Machine")

        objects_cache: dict[str, Any] = {"": self.server.nodes.objects}
        await self._ensure_object_path(objects_cache, ns_idx, root_name)

        variables = model.get("variables", [])
        if not isinstance(variables, list):
            raise ValueError("model.variables must be a list")

        for item in variables:
            if not isinstance(item, dict):
                continue

            name = str(item.get("name") or "Variable")
            path = str(item.get("path") or f"{root_name}/{name}")
            dtype = str(item.get("type") or "float").lower()
            writable = bool(item.get("writable", True))
            initial = _cast(dtype, item.get("initial", False if dtype == "bool" else 0))

            parent_path, leaf = self._split_path(path)
            parent = await self._ensure_object_path(objects_cache, ns_idx, parent_path)

            raw_node_id = item.get("node_id")
            if raw_node_id:
                node_id = str(raw_node_id)
                if not node_id.startswith("ns="):
                    node_id = f"ns={ns_idx};s={node_id}"
            else:
                canonical = path.replace("/", ".")
                node_id = f"ns={ns_idx};s={canonical}"

            var_node = await parent.add_variable(node_id, leaf, initial)
            if writable:
                await var_node.set_writable()

            print(f"[sim] var: {name:20s} -> {node_id} (type={dtype}, writable={writable})")

            sim_cfg = item.get("simulation")
            if isinstance(sim_cfg, dict) and sim_cfg.get("mode"):
                interval_ms = int(sim_cfg.get("interval_ms", self.default_tick_ms))
                self.bindings.append(
                    SimBinding(
                        node=var_node,
                        node_id=node_id,
                        dtype=dtype,
                        simulation=sim_cfg,
                        next_due=time.monotonic() + interval_ms / 1000.0,
                    )
                )

    async def _ensure_object_path(self, cache: dict[str, Any], ns_idx: int, path: str) -> Any:
        norm = "/".join([p for p in str(path).split("/") if p])
        if norm in cache:
            return cache[norm]

        parent_path, leaf = self._split_path(norm)
        parent = await self._ensure_object_path(cache, ns_idx, parent_path) if norm else self.server.nodes.objects
        if not norm:
            return parent

        node_id = f"ns={ns_idx};s={norm.replace('/', '.')}"
        obj = await parent.add_object(node_id, leaf)
        cache[norm] = obj
        return obj

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        clean = "/".join([p for p in str(path).split("/") if p])
        if "/" not in clean:
            return "", clean
        parent, leaf = clean.rsplit("/", 1)
        return parent, leaf

    async def run(self) -> None:
        async with self.server:
            print(f"[sim] running with {len(self.bindings)} simulated variables")
            while True:
                await self._tick()
                await asyncio.sleep(max(self.default_tick_ms, 100) / 1000.0)

    async def _tick(self) -> None:
        now = time.monotonic()
        for b in self.bindings:
            interval_ms = int(b.simulation.get("interval_ms", self.default_tick_ms))
            if now < b.next_due:
                continue

            try:
                current = await b.node.read_value()
            except Exception:
                continue

            mode = str(b.simulation.get("mode", "")).lower().strip()
            new_value = current

            if mode == "toggle":
                new_value = not _to_bool(current)

            elif mode == "random_walk":
                step = float(b.simulation.get("step", 1.0))
                minimum = float(b.simulation.get("min", 0.0))
                maximum = float(b.simulation.get("max", 100.0))
                cur = float(current)
                cur += random.uniform(-step, step)
                new_value = max(minimum, min(maximum, cur))

            elif mode == "random_choice":
                values = b.simulation.get("values", [])
                if isinstance(values, list) and values:
                    new_value = random.choice(values)

            elif mode == "cycle":
                values = b.simulation.get("values", [])
                if isinstance(values, list) and values:
                    b.cycle_index = (b.cycle_index + 1) % len(values)
                    new_value = values[b.cycle_index]

            elif mode == "ramp":
                step = float(b.simulation.get("step", 1.0))
                minimum = float(b.simulation.get("min", 0.0))
                maximum = float(b.simulation.get("max", 100.0))
                cur = float(current) + step
                if cur > maximum:
                    cur = minimum
                if cur < minimum:
                    cur = maximum
                new_value = cur

            elif mode == "sine":
                minimum = float(b.simulation.get("min", 0.0))
                maximum = float(b.simulation.get("max", 100.0))
                period_ms = float(b.simulation.get("period_ms", 5000.0))
                b.phase += (2 * math.pi) * (interval_ms / max(period_ms, 10.0))
                center = (maximum + minimum) / 2.0
                amp = (maximum - minimum) / 2.0
                new_value = center + amp * math.sin(b.phase)

            casted = _cast(b.dtype, new_value)
            try:
                await b.node.write_value(casted)
            except Exception:
                pass

            b.next_due = now + interval_ms / 1000.0


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Top-level YAML must be a mapping/object")
    return data


def _maybe_create_example(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(EXAMPLE_CONFIG, encoding="utf-8")


async def _main() -> None:
    cfg_path = Path(os.environ.get("OPCUA_SIM_CONFIG_FILE", "/config/opcua_plc_simulator.yaml"))
    auto_create = _to_bool(os.environ.get("OPCUA_SIM_AUTO_CREATE", True))

    if auto_create and not cfg_path.exists():
        print(f"[sim] Config not found, creating example: {cfg_path}")
        _maybe_create_example(cfg_path)

    cfg = _load_yaml(cfg_path)

    sim = PlcSimulator(cfg)
    await sim.setup()
    await sim.run()


if __name__ == "__main__":
    asyncio.run(_main())
