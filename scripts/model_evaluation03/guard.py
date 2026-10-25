"""Bounded, serial production completion tracing and local runtime guards."""

from __future__ import annotations

import ctypes
import json
import os
import shutil
import subprocess
import threading
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


class EvaluationStop(RuntimeError):
    """An unsafe/failed runtime must not trigger further inference attempts."""


def timestamp():
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def local_endpoint(value: str) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/v1"
    ):
        raise ValueError("Only a loopback HTTP Ollama /v1 endpoint is allowed.")
    parsed.port
    return value.rstrip("/")


def available_memory():
    if os.name == "nt":

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("load", ctypes.c_ulong),
                *[
                    (name, ctypes.c_ulonglong)
                    for name in (
                        "total_physical",
                        "available_physical",
                        "total_pagefile",
                        "available_pagefile",
                        "total_virtual",
                        "available_virtual",
                        "available_extended",
                    )
                ],
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise EvaluationStop("Cannot determine available system RAM.")
        return status.available_physical
    if Path("/proc/meminfo").exists():
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise EvaluationStop("This live runner needs a reliable Windows/Linux RAM measurement.")


def resource_snapshot():
    result = {"available_ram_bytes": available_memory(), "nvidia_free_mib": None}
    command = shutil.which("nvidia-smi")
    if command:
        response = subprocess.run(
            [command, "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        values = [int(line.strip()) for line in response.stdout.splitlines() if line.strip()]
        if not values:
            raise EvaluationStop("NVIDIA is available but free VRAM could not be measured.")
        result["nvidia_free_mib"] = values
    if result["available_ram_bytes"] < 1_500_000_000:
        raise EvaluationStop("Available RAM fell below 1.5 GB.")
    if result["nvidia_free_mib"] is not None and min(result["nvidia_free_mib"]) < 1024:
        raise EvaluationStop("Available NVIDIA VRAM fell below 1024 MiB.")
    return result


def model_name(value):
    return value if ":" in value else value + ":latest"


class LiveGuard:
    def __init__(self, output, endpoint, model, source_model, max_calls=80, minutes=45):
        self.output = Path(output)
        self.endpoint = local_endpoint(endpoint)
        self.ollama = self.endpoint.removesuffix("/v1")
        self.model = model_name(model)
        self.source_model = model_name(source_model)
        self.max_calls = max_calls
        self.deadline = time.monotonic() + minutes * 60
        self.started = timestamp()
        self.lock = threading.RLock()
        self.serial = threading.Lock()
        self.local = threading.local()
        self.calls = []
        self.resources = []
        self.failure = None
        self.case = "initialization"
        self.expected_interrupt = False
        self.digests = None

    def save(self):
        with self.lock:
            write_json(
                self.output / "provider-trace.json",
                {
                    "started_at": self.started,
                    "model": self.model,
                    "endpoint": self.endpoint,
                    "production_generation_overrides": {},
                    "calls": self.calls,
                    "resource_checks": self.resources,
                    "stop_reason": self.failure,
                    "transport_entry_meaning": "Before production complete_json; response headers may not exist yet.",
                },
            )

    def stop(self, reason):
        with self.lock:
            self.failure = self.failure or str(reason)
            self.save()
        raise EvaluationStop(self.failure)

    def check(self):
        if self.failure:
            raise EvaluationStop(self.failure)
        if (self.output / "STOP").exists():
            self.stop("Stopped explicitly by the acceptance reviewer (STOP file).")
        if time.monotonic() >= self.deadline:
            self.stop("45-minute/global evaluation time budget exhausted.")

    def runtime(self, label):
        import httpx

        self.check()
        try:
            resources = resource_snapshot()
            with httpx.Client(timeout=10, trust_env=False) as client:
                tags = client.get(self.ollama + "/api/tags").raise_for_status().json()["models"]
                loaded = client.get(self.ollama + "/api/ps").raise_for_status().json()["models"]
            digests = {}
            for name in {self.model, self.source_model}:
                item = next((row for row in tags if model_name(row.get("name", "")) == name), None)
                if item is None or not item.get("digest"):
                    raise EvaluationStop("Expected model/tag is unavailable: " + name)
                digests[name] = item["digest"]
            if self.digests is not None and digests != self.digests:
                raise EvaluationStop("Model/tag digest changed during acceptance.")
            if any(model_name(row.get("name", row.get("model", ""))) != self.model for row in loaded):
                raise EvaluationStop("Another model is loaded; acceptance requires one test model only.")
            self.digests = digests
            with self.lock:
                self.resources.append(
                    {
                        "at": timestamp(),
                        "label": label,
                        **resources,
                        "digests": digests,
                        "loaded": [
                            {key: row.get(key) for key in ("name", "digest", "size_vram")} for row in loaded
                        ],
                    }
                )
                self.save()
            return self.resources[-1]
        except Exception as error:
            self.stop(f"Runtime/resource check failed: {error}")

    def phase(self, system):
        if "evidence critic" in system:
            return "critic"
        return "planner" if "Plan research" in system else "writer"

    @contextmanager
    def instrument(self):
        from on_knowledge import providers

        original_complete = providers.OpenAICompatible.complete
        original_transport = providers.complete_json

        def transport(url, headers, payload, **kwargs):
            from on_knowledge.completion_stream import _cancellation, cancellable_completion

            self.check()
            if not url.startswith(self.endpoint + "/"):
                self.stop("A production completion attempted a different endpoint.")
            with self.lock:
                call = self.local.call
                call.update(transport_entered_at=timestamp(), transport_url=url, wire_payload=payload)
                self.save()
            kwargs["deadline_seconds"] = min(
                kwargs.get("deadline_seconds", 300), self.deadline - time.monotonic()
            )
            production_checkpoint = _cancellation.get()

            def checkpoint():
                self.check()
                if production_checkpoint is not None:
                    production_checkpoint()

            with cancellable_completion(checkpoint):
                return original_transport(url, headers, payload, **kwargs)

        def complete(provider, system, data):
            self.check()
            if not self.serial.acquire(blocking=False):
                self.stop("Concurrent inference was attempted.")
            call = None
            try:
                if provider.base != self.endpoint or model_name(provider.settings["model"]) != self.model:
                    self.stop("Completion connection/model differs from the explicit test alias.")
                if len(self.calls) >= self.max_calls:
                    self.stop("80-call/global completion budget exhausted.")
                before = self.runtime("before completion")
                with self.lock:
                    call = {
                        "id": len(self.calls) + 1,
                        "case": self.case,
                        "phase": self.phase(system),
                        "started_at": timestamp(),
                        "system": system,
                        "data": data,
                        "resources_before": before,
                        "status": "running",
                    }
                    self.calls.append(call)
                    self.local.call = call
                    self.save()
                result = original_complete(provider, system, data)
                with self.lock:
                    call.update(status="completed", result=result)
                return result
            except Exception as error:
                expected = self.expected_interrupt and bool(getattr(error, "cancelled", False))
                if call is not None:
                    call.update(
                        status="cancelled" if expected else "failed",
                        error_type=type(error).__name__,
                        error=str(error),
                    )
                if not expected:
                    self.failure = self.failure or f"Provider/guard failure: {type(error).__name__}: {error}"
                raise
            finally:
                try:
                    if call is not None:
                        call["finished_at"] = timestamp()
                        if not self.failure:
                            call["resources_after"] = self.runtime("after completion")
                finally:
                    self.save()
                    self.serial.release()

        providers.OpenAICompatible.complete = complete
        providers.complete_json = transport
        try:
            self.runtime("before acceptance")
            yield self
        finally:
            providers.OpenAICompatible.complete = original_complete
            providers.complete_json = original_transport
            self.save()

    def wait_idle(self, timeout=30):
        end = time.monotonic() + timeout
        while self.serial.locked():
            self.check()
            if time.monotonic() > end:
                self.stop("The previous completion did not close locally after interruption.")
            time.sleep(0.1)
        self.check()

    def wait_writer(self, start_count, timeout=60):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.check()
            with self.lock:
                active = [
                    call
                    for call in self.calls[start_count:]
                    if call["phase"] == "writer"
                    and call["status"] == "running"
                    and call.get("transport_entered_at")
                ]
                if active:
                    return active[-1]["id"]
            time.sleep(0.02)
        self.stop("No active production writer transport entry was observed.")
