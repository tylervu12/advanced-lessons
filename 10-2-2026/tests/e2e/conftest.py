"""Start a REAL Uvicorn process and stop it even if a test fails.

This fixture uses inherited sockets on macOS/Linux. Keeping the socket open
while passing it to the server avoids a race where another process steals a
port between choosing it and starting Uvicorn. See README for Windows/WSL.

Syntax used in this file:
- @ introduces a decorator that applies behavior or metadata to a function.
  @pytest.fixture registers reusable setup; tests request it by argument name.
- tmp_path is pytest's temporary-directory fixture. Path / "name" joins paths.
- @contextmanager turns a function with yield into something usable with `with`.
  Code before yield sets up resources; yield provides the value after `as`;
  leaving the with block resumes the function so cleanup can run.
- This fixture returns the start FUNCTION without calling it. Each test chooses
  when to call it, so a single test can stop and restart the application.
- subprocess.Popen starts a separate program without waiting for it to exit.
  sys.executable uses the same Python environment as pytest. env configures the
  child's database path; pass_fds shares the already-open socket with the child.
- A socket is a network communication endpoint. A port identifies the listener
  on this computer. Binding port 0 lets the operating system choose a free port.
- try/except handles a particular failure; finally always attempts cleanup when
  leaving the try block. The startup loop tolerates connection errors while the
  server boots. pytest.fail(...) explicitly fails setup with a useful message.
- poll() checks whether the process exited; wait(timeout=...) waits up to a
  limit. terminate() requests shutdown; kill() forcibly stops a stuck process.
- The else on the while loop runs only if the loop finishes without break:
  here that means the readiness deadline expired instead of the server starting.
"""

import os
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import httpx2 as httpx
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def running_server(tmp_path):
    # Reuse this path within one test so stopping/restarting the server can
    # prove persistence. Different tests still receive different databases.
    database_path = tmp_path / "e2e.sqlite3"

    @contextmanager
    def start():
        env = os.environ.copy()
        env["STORE_DATABASE"] = str(database_path)
        log_path = tmp_path / f"server-{uuid4()}.log"

        with socket.socket() as listener, log_path.open("w") as log:
            listener.bind(("127.0.0.1", 0))  # Port 0 asks the OS for a free port.
            listener.listen(128)
            port = listener.getsockname()[1]
            process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn", "app.main:app",
                    "--fd", str(listener.fileno()), "--log-level", "warning",
                ],
                cwd=PROJECT_ROOT,
                env=env,
                pass_fds=(listener.fileno(),),
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            # The child now owns its copy. Closing the parent's copy ensures a
            # dead server cannot leave an apparently open listening port behind.
            listener.close()
            try:
                with httpx.Client(
                    base_url=f"http://127.0.0.1:{port}", timeout=2, trust_env=False
                ) as client:
                    # Poll readiness, rather than sleeping a fixed number of
                    # seconds. Slow startup gets a deadline; fast startup proceeds.
                    deadline = time.monotonic() + 15
                    while time.monotonic() < deadline:
                        if process.poll() is not None:
                            pytest.fail(f"Server exited during startup:\n{log_path.read_text()}")
                        try:
                            if client.get("/health", timeout=0.3).status_code == 200:
                                break
                        except httpx.TransportError:
                            pass  # Connection refusal is expected during startup.
                        time.sleep(0.05)
                    else:
                        pytest.fail(f"Server did not become ready:\n{log_path.read_text()}")

                    yield client
            finally:
                # Cleanup runs even after an assertion fails. No orphan servers.
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    return start
