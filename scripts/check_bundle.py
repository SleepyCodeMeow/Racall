"""Exercise the frozen backend through real HTTP, including a two-page PDF."""
import io
import os
import secrets
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from reportlab.pdfgen.canvas import Canvas

root = Path(__file__).resolve().parents[1]
binary = Path(os.environ.get("RACALL_BACKEND_BINARY", str(root / "release/win-unpacked/resources/backend/open-notebook-api.exe")))
data = root / "test-results" / ("bundle-" + secrets.token_hex(6))
data.mkdir(parents=True)
token = secrets.token_hex(32)
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
with (data / "process.log").open("w") as log:
    process = subprocess.Popen(
        [str(binary), "--data-dir", str(data), "--port", str(port)],
        env={**os.environ, "OPENNOTEBOOK_SESSION_TOKEN": token},
        stdout=log, stderr=log,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", headers={"Authorization": "Bearer " + token}) as client:
            for _ in range(100):
                try:
                    if client.get("/health").status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            assert client.get("/api/notebooks", headers={"Authorization": "invalid"}).status_code == 401
            notebook = client.post("/api/notebooks", json={"title": "Packaged PDF test"}).json()["id"]
            pdf = io.BytesIO()
            canvas = Canvas(pdf)
            canvas.drawString(50, 750, "Unrelated first page")
            canvas.showPage()
            canvas.drawString(50, 750, "Marigold launch date is October 18.")
            canvas.save()
            response = client.post(f"/api/notebooks/{notebook}/sources", files={"file": ("facts.pdf", pdf.getvalue())})
            assert response.status_code == 202, response.text
            source = response.json()["id"]
            for _ in range(100):
                state = client.get(f"/api/notebooks/{notebook}/sources/{source}").json()["source"]
                if state["status"] in ("ready", "error"):
                    break
                time.sleep(.1)
            assert state["status"] == "ready", state
            result = client.post(f"/api/notebooks/{notebook}/search", json={"question": "Marigold"}).json()
            assert result["evidence"][0]["location"]["page"] == 2
            assert "October 18" in result["evidence"][0]["quote"]
            assert client.get(f"/api/notebooks/{notebook}/sources/{source}/original").content == pdf.getvalue()
            print("Frozen backend: PDF import, FTS, page citation, original download and authentication passed.")
    finally:
        process.terminate()
        process.wait(timeout=15)
