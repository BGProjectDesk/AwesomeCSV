"""Owned synthetic layout checks on the guarded GitHub-hosted runner only."""
import json
import math
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser


class ProofParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active, self.matches, self.parts = False, 0, []

    def handle_starttag(self, tag, attrs):
        if tag == "pre" and dict(attrs).get("id") == "layout-proof":
            self.active = True
            self.matches += 1

    def handle_endtag(self, tag):
        if tag == "pre":
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect refused")


def require(ok):
    if not ok:
        raise ValueError("proof requirement failed")


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def case(driver, chrome, fixture, width, control):
    proc, session = None, None
    with tempfile.TemporaryDirectory(prefix="owned-layout-") as profile:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

        def request(method, path, payload=None, timeout=20):
            require(path.startswith("/") and not path.startswith("//"))
            data = None if payload is None else json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(base + path, data=data, method=method,
                                         headers={"Content-Type": "application/json"})
            with opener.open(req, timeout=timeout) as response:
                raw = response.read(131073)
            require(len(raw) <= 131072)
            result = json.loads(raw)
            value = result.get("value")
            require(not (isinstance(value, dict) and "error" in value))
            return value

        try:
            # Default driver access is loopback only; never enable remote clients.
            proc = subprocess.Popen([driver, f"--port={port}"],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
            deadline = time.monotonic() + 8
            while True:
                require(proc.poll() is None)
                try:
                    status = request("GET", "/status", timeout=1)
                    if status.get("ready") is True:
                        break
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    pass
                require(time.monotonic() < deadline)
                time.sleep(0.1)
            args = ["--headless", f"--user-data-dir={profile}",
                    "--disable-background-networking", "--disable-component-update",
                    "--disable-sync", "--no-first-run", "--no-default-browser-check",
                    "--host-resolver-rules=MAP * ~NOTFOUND"]
            created = request("POST", "/session", {"capabilities": {"alwaysMatch": {
                "browserName": "chrome", "pageLoadStrategy": "normal",
                "goog:chromeOptions": {"binary": chrome, "args": args},
                "timeouts": {"implicit": 0, "pageLoad": 10000, "script": 10000}
            }}})
            session = created["sessionId"]
            require(isinstance(session, str) and session.isalnum())
            version = created.get("capabilities", {}).get("browserVersion")
            require(isinstance(version, str) and len(version) < 100)
            prefix = "/session/" + session
            request("POST", prefix + "/goog/cdp/execute", {
                "cmd": "Emulation.setDeviceMetricsOverride",
                "params": {"width": width, "height": 900,
                           "deviceScaleFactor": 1, "mobile": False}
            })
            request("POST", prefix + "/url", {
                "url": fixture.as_uri() + ("?overflow=1" if control else "")
            })
            dom = request("GET", prefix + "/source")
            require(isinstance(dom, str) and len(dom) <= 65536)
            parser = ProofParser()
            parser.feed(dom)
            require(parser.matches == 1)
            metrics = json.loads("".join(parser.parts))
            rect = metrics["main"]
            require(all(number(v) for v in [metrics["innerWidth"], metrics["scrollWidth"],
                                           rect["left"], rect["right"], rect["width"]]))
            checks = {
                "exactViewport": metrics["innerWidth"] == width,
                "controlMatches": metrics["control"] is control,
                "containerFits": rect["left"] >= 0 and rect["right"] <= metrics["innerWidth"] and rect["width"] > 0,
                "programmaticFocus": metrics["buttonFocused"] is True,
                "zeroResourceEntries": type(metrics["externalResourceCount"]) is int and metrics["externalResourceCount"] == 0,
                "overflowExpectation": (metrics["scrollWidth"] > metrics["innerWidth"]) == control,
            }
            return {"browserVersion": version, "requestedWidth": width,
                    "actualWidth": metrics["innerWidth"], "scrollWidth": metrics["scrollWidth"],
                    "main": rect, "control": control, "checks": checks, "passed": all(checks.values())}
        finally:
            if session is not None and isinstance(session, str) and session.isalnum():
                try:
                    request("DELETE", "/session/" + session, timeout=3)
                except Exception:
                    pass
            if proc is not None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=3)


def main():
    expected = {"GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted",
                "RUNNER_OS": "Linux", "GITHUB_REPOSITORY": "BGProjectDesk/AwesomeCSV",
                "GITHUB_REF": "refs/heads/cloud-model-trial-20261116", "GITHUB_RUN_ATTEMPT": "1"}
    require(all(os.environ.get(k) == v for k, v in expected.items()))
    fixture = Path(__file__).resolve().with_name("html-fixture.html")
    driver, chrome = shutil.which("chromedriver"), shutil.which("google-chrome")
    require(fixture.is_file() and driver is not None and chrome is not None)
    failures = 0
    for width, control in [(320, False), (768, False), (1280, False), (320, True)]:
        try:
            result = case(driver, chrome, fixture, width, control)
        except Exception as exc:
            result = {"requestedWidth": width, "control": control,
                      "passed": False, "errorType": type(exc).__name__}
        failures += not result["passed"]
        print(json.dumps(result))
    print(json.dumps({"cases": 4, "failed": failures, "passed": failures == 0}))
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__}))
        sys.exit(1)
