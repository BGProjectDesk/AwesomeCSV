"""Owned synthetic HTML checks; intended only for the guarded hosted CI job."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser


class ProofParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.parts = []
        self.matches = 0

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


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def main():
    expected = {
        "GITHUB_ACTIONS": "true",
        "RUNNER_ENVIRONMENT": "github-hosted",
        "RUNNER_OS": "Linux",
        "GITHUB_REPOSITORY": "BGProjectDesk/AwesomeCSV",
        "GITHUB_REF": "refs/heads/cloud-model-trial-20261116",
        "GITHUB_RUN_ATTEMPT": "1",
    }
    require(all(os.environ.get(k) == v for k, v in expected.items()), "runner guard failed")
    fixture = Path(__file__).resolve().with_name("html-fixture.html")
    require(fixture.is_file(), "fixture missing")
    chrome = shutil.which("google-chrome")
    require(chrome is not None, "installed google-chrome missing")
    version = subprocess.run([chrome, "--version"], capture_output=True, text=True, timeout=5, check=True)
    print(json.dumps({"browserVersion": version.stdout.strip()[:120]}))
    failures = 0
    for width, control in [(320, False), (768, False), (1280, False), (320, True)]:
        try:
            with tempfile.TemporaryDirectory(prefix="owned-layout-") as profile:
                args = [chrome, "--headless", "--dump-dom", "--timeout=10000",
                        "--virtual-time-budget=1000", f"--window-size={width},900",
                        f"--user-data-dir={profile}", "--disable-background-networking",
                        "--disable-component-update", "--disable-sync", "--no-first-run",
                        "--no-default-browser-check", "--host-resolver-rules=MAP * ~NOTFOUND",
                        fixture.as_uri() + ("?overflow=1" if control else "")]
                result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                        timeout=20, check=False)
            require(result.returncode == 0, "browser exit failure")
            require(len(result.stdout) <= 65536, "unexpected DOM size")
            parser = ProofParser()
            parser.feed(result.stdout.decode("utf-8", errors="strict"))
            require(parser.matches == 1, "proof element missing or duplicated")
            metrics = json.loads("".join(parser.parts))
            rect = metrics["main"]
            require(all(number(v) for v in [metrics["innerWidth"], metrics["scrollWidth"],
                                           rect["left"], rect["right"], rect["width"]]), "invalid metrics")
            overflow = metrics["scrollWidth"] > metrics["innerWidth"]
            checks = {
                "exactViewport": metrics["innerWidth"] == width,
                "controlMatches": metrics["control"] is control,
                "containerFits": rect["left"] >= 0 and rect["right"] <= metrics["innerWidth"] and rect["width"] > 0,
                "programmaticFocus": metrics["buttonFocused"] is True,
                "zeroResourceEntries": type(metrics["externalResourceCount"]) is int and metrics["externalResourceCount"] == 0,
                "overflowExpectation": overflow == control,
            }
            passed = all(checks.values())
            failures += not passed
            print(json.dumps({"requestedWidth": width, "actualWidth": metrics["innerWidth"],
                              "scrollWidth": metrics["scrollWidth"], "main": rect,
                              "control": control, "checks": checks, "passed": passed}))
        except Exception as exc:
            failures += 1
            print(json.dumps({"requestedWidth": width, "control": control,
                              "passed": False, "errorType": type(exc).__name__}))
    print(json.dumps({"cases": 4, "failed": failures, "passed": failures == 0}))
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"passed": False, "errorType": type(exc).__name__}))
        sys.exit(1)
