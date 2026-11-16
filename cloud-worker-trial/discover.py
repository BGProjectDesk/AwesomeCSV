"""Cloud-only Groq catalogue adapter. No completion or customer-data path."""
import argparse
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request
import unittest
from unittest import mock

ENDPOINT = "https://api.groq.com/openai/v1/models"
MAX_BYTES = 1024 * 1024
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/:-]{0,159}\Z")


def cloud_guard(env):
    if not (
        env.get("GITHUB_ACTIONS") == "true"
        and env.get("RUNNER_ENVIRONMENT") == "github-hosted"
        and env.get("RUNNER_OS") == "Linux"
        and env.get("GITHUB_RUN_ATTEMPT") == "1"
    ):
        raise ValueError("CLOUD_CONTEXT_REQUIRED")


def approval_guard(env):
    cloud_guard(env)
    if not (
        env.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
        and env.get("GITHUB_REPOSITORY") == "BGProjectDesk/AwesomeCSV"
        and env.get("GITHUB_REF") == "refs/heads/cloud-model-trial-20261116"
        and env.get("OWNER_FREE_CONFIRMATION") == "FREE"
        and env.get("APPROVAL_SCOPE") == "DISCOVER_ONLY"
    ):
        raise ValueError("DISCOVERY_APPROVAL_REQUIRED")


def catalogue(value):
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        raise ValueError("INVALID_CATALOGUE")
    rows = value["data"]
    if not rows or len(rows) > 200:
        raise ValueError("INVALID_MODEL_COUNT")
    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("INVALID_MODEL")
        ident = row.get("id")
        if not isinstance(ident, str) or not ID.fullmatch(ident) or ident in seen:
            raise ValueError("INVALID_MODEL_ID")
        seen.add(ident)
        item = {"id": ident}
        if "active" in row:
            if type(row["active"]) is not bool:
                raise ValueError("INVALID_ACTIVE_FLAG")
            item["active"] = row["active"]
        if "context_window" in row:
            n = row["context_window"]
            if type(n) is not int or not 0 < n <= 10000000:
                raise ValueError("INVALID_CONTEXT_WINDOW")
            item["context_window"] = n
        result.append(item)
    return sorted(result, key=lambda item: item["id"])


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def read_catalogue(key, opener=None):
    """One fixed GET. No retries, redirects, generation, error-body logging."""
    if not key or len(key) > 256 or not key.isascii() or any(c.isspace() for c in key):
        raise ValueError("KEY_MISSING_OR_INVALID")
    if opener is None:
        opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        ENDPOINT,
        headers={"Authorization": "Bearer " + key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=30) as response:
            if response.status != 200:
                raise ValueError("UNEXPECTED_STATUS")
            raw = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
        raise ValueError("HTTP_" + str(status)) from None
    except urllib.error.URLError:
        raise ValueError("NETWORK_ERROR") from None
    except TimeoutError:
        raise ValueError("NETWORK_TIMEOUT") from None
    if len(raw) > MAX_BYTES:
        raise ValueError("RESPONSE_TOO_LARGE")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError):
        raise ValueError("INVALID_JSON") from None
    return catalogue(value)


def discover(env):
    approval_guard(env)  # Before reading any provider secret.
    key = env.get("GROQ_API_KEY", "")
    models = read_catalogue(key)
    return {
        "stage": "availability_only",
        "observed_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "get_requests": 1,
        "completion_requests": 0,
        "owner_free_attestation": True,
        "connected_working_models_verified": 0,
        "stage_2_enabled": False,
        "models": models,
        "precision": "Catalogue only; no inference, task suitability or free-model entitlement verified.",
    }


class AdapterTests(unittest.TestCase):
    def cloud_env(self):
        return {
            "GITHUB_ACTIONS": "true",
            "RUNNER_ENVIRONMENT": "github-hosted",
            "RUNNER_OS": "Linux",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "BGProjectDesk/AwesomeCSV",
            "GITHUB_REF": "refs/heads/cloud-model-trial-20261116",
            "OWNER_FREE_CONFIRMATION": "FREE",
            "APPROVAL_SCOPE": "DISCOVER_ONLY",
        }

    def test_cloud_only(self):
        cloud_guard(self.cloud_env())
        for field in ("GITHUB_ACTIONS", "RUNNER_ENVIRONMENT", "RUNNER_OS", "GITHUB_RUN_ATTEMPT"):
            env = self.cloud_env()
            env[field] = "wrong"
            with self.assertRaises(ValueError):
                approval_guard(env)

    def test_stop_before_secret_or_network(self):
        class Guarded(dict):
            def get(self, key, default=None):
                if key == "GROQ_API_KEY":
                    raise AssertionError("Secret accessed before approval")
                return super().get(key, default)
        for field in ("OWNER_FREE_CONFIRMATION", "APPROVAL_SCOPE", "GITHUB_EVENT_NAME", "GITHUB_REPOSITORY", "GITHUB_REF"):
            env = Guarded(self.cloud_env())
            env[field] = "STOP"
            with mock.patch(__name__ + ".read_catalogue", side_effect=AssertionError("Network called")):
                with self.assertRaises(ValueError):
                    discover(env)

    def test_public_metadata_only(self):
        rows = catalogue({"data": [{"id": "publisher/model", "active": True,
                                    "context_window": 8192, "untrusted_extra": "ignored"}]})
        self.assertEqual(rows, [{"id": "publisher/model", "active": True, "context_window": 8192}])

    def test_bad_catalogues(self):
        for value in ([], {}, {"data": []}, {"data": [{}]},
                      {"data": [{"id": "::malformed\n"}]},
                      {"data": [{"id": "ok"}, {"id": "ok"}]},
                      {"data": [{"id": "ok", "active": 1}]},
                      {"data": [{"id": "ok", "context_window": True}]}):
            with self.assertRaises(ValueError):
                catalogue(value)

    def test_redirect_refused(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.invalid"))

    def test_fake_transport_one_get(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit):
                self.limit = limit
                return b'{"data":[{"id":"fake/model"}]}'
        class Opener:
            calls = 0
            def open(self, request, timeout):
                self.calls += 1
                self.request, self.timeout = request, timeout
                return Response()
        opener = Opener()
        self.assertEqual(read_catalogue("synthetic-not-a-real-key", opener), [{"id": "fake/model"}])
        self.assertEqual(opener.calls, 1)
        self.assertEqual(opener.request.full_url, ENDPOINT)
        self.assertEqual(opener.request.get_method(), "GET")
        self.assertIsNone(opener.request.data)
        self.assertEqual(opener.timeout, 30)

    def test_oversized_response(self):
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, limit): return b"x" * limit
        class Opener:
            def open(self, request, timeout): return Response()
        with self.assertRaisesRegex(ValueError, "^RESPONSE_TOO_LARGE$"):
            read_catalogue("synthetic-not-a-real-key", Opener())

    def test_missing_key_has_no_transport_call(self):
        with mock.patch("urllib.request.build_opener", side_effect=AssertionError("Transport created")):
            with self.assertRaises(ValueError):
                read_catalogue("")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("self-test", "discover"))
    args = parser.parse_args()
    try:
        cloud_guard(os.environ)
        if args.mode == "self-test":
            # Tests use invented metadata and injected fake transport only.
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdapterTests)
            passed = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite).wasSuccessful()
            return 0 if passed else 1
        receipt = discover(os.environ)
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except ValueError as exc:
        print(json.dumps({"status": "stopped", "code": str(exc),
                          "completion_requests": 0, "working_models_verified": 0}))
        return 2
    except Exception:
        print(json.dumps({"status": "stopped", "code": "UNEXPECTED_ERROR",
                          "completion_requests": 0, "working_models_verified": 0}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
