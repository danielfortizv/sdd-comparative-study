"""Black-box Stage2 researcher checker v1.3: native BMAD shape/coordinate support.

Usage: python check_api_v1_3.py --base-url http://127.0.0.1:8000 --output evidence.json
Add --created-status 200 for Tessl's preserved Stage 1 creation contract.
Version 1.2 adds an explicit expected creation status (default 201), captures
actual HTTP statuses without normalization, and preserves v1.1 gameplay cases.
The original check_api.py v1.1 remains immutable for prior evidence/report hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone


TYPES = set("IOTJLSZ")
VERSION = "1.3"
PARENT_VERSION_SHA256 = "BE6E4EA362726AEC990D0D5D456BF5E15D5071BBAD1436F6FE9C1E77B6A83F3E"


def call(base: str, method: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        try:
            data = json.load(error)
        except (ValueError, UnicodeError):
            data = None
        return error.code, data


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def board_valid(state):
    return len(state["board"]) == 20 and all(len(row) == 10 for row in state["board"])


def active_piece(state):
    piece = state.get("active_piece", state.get("activePiece"))
    check(isinstance(piece, dict), "missing active piece")
    # Researcher observation adapter only; never mutate the raw JSON response.
    normalized = dict(piece)
    if "type" not in normalized and "shape" in piece:
        normalized["type"] = piece["shape"]
    origin = piece.get("origin")
    if isinstance(origin, dict):
        normalized["origin"] = [origin["row"], origin["col"]]
    normalized["cells"] = [[c["row"], c["col"]] if isinstance(c, dict) else c for c in piece.get("cells", [])]
    return normalized


def centered_spawn(piece):
    origin = piece.get("origin")
    check(isinstance(origin, list) and len(origin) == 2, "missing spawn origin")
    check(0 <= origin[0] <= 2 and 2 <= origin[1] <= 6, f"spawn origin is not top centered: {origin}")
    check(all(0 <= r <= 3 and 0 <= c <= 9 for r, c in piece["cells"]), "spawned cells out of top board bounds")


def run(base: str, created_status: int = 201, http_observations: list | None = None):
    results = []
    observations = http_observations if http_observations is not None else []

    def request(method: str, path: str, payload=None):
        status, body = call(base, method, path, payload)
        observations.append({"method": method, "path": path, "actual_http_status": status, "raw_response": body})
        return status, body

    def case(identifier, fn):
        started = time.perf_counter()
        try:
            detail = fn()
            status = "pass"
        except Exception as error:
            detail, status = f"{type(error).__name__}: {error}", "fail"
        results.append({"id": identifier, "status": status, "detail": detail, "duration_ms": round((time.perf_counter() - started) * 1000, 2)})

    session = {}

    def initial():
        status, state = request("POST", "/api/games")
        check(status == created_status, f"create HTTP {status}; expected {created_status}")
        check(board_valid(state), "board is not 20x10")
        expected = {"score": 0, "total_lines": 0, "level": 1, "gravity_interval_ms": 500, "hold_piece": None, "can_hold": True}
        for key, value in expected.items():
            check(state.get(key) == value, f"{key}: expected {value}, got {state.get(key)}")
        check(state.get("next_piece") in TYPES, "invalid preview")
        check(active_piece(state)["type"] in TYPES, "invalid active piece")
        session["id"], session["initial"] = state["id"], state
        return "new game fields, board and tetromino types valid"

    case("S2-01", initial)
    if "id" not in session:
        return results
    game_id = session["id"]
    path = f"/api/games/{game_id}"

    def peek():
        status1, a = request("GET", path)
        status2, b = request("GET", path)
        check(status1 == 200 and status2 == 200, f"GET statuses {status1}, {status2}")
        check(a == b == session["initial"], "GET mutated the game or preview")
        return "two reads preserved full state"

    case("S2-02", peek)

    def first_hold():
        prior = session["initial"]
        status, state = request("POST", path + "/hold")
        check(status == 200, f"hold HTTP {status}")
        check(state["hold_piece"] == active_piece(prior)["type"], "hold slot mismatch")
        check(active_piece(state)["type"] == prior["next_piece"], "preview did not spawn")
        centered_spawn(active_piece(state))
        check(state["next_piece"] in TYPES, "invalid new preview")
        check(state["can_hold"] is False, "hold did not enter cooldown")
        session["held"] = state
        return "first hold consumed preview and entered cooldown"

    case("S2-10", first_hold)

    def repeated_hold():
        check("held" in session, "first hold failed")
        before = session["held"]
        status, _ = request("POST", path + "/hold")
        _, after = request("GET", path)
        check(status in (200, 400, 409), f"unexpected rejection status {status}")
        check(before == after, "repeated hold mutated game state")
        return f"second hold rejected with HTTP {status}; state preserved"

    case("S2-11", repeated_hold)

    def lock_and_swap():
        check("held" in session, "first hold failed")
        current = session["held"]
        for _ in range(25):
            status, current = request("POST", path + "/tick")
            check(status == 200, f"tick HTTP {status}")
            if current["can_hold"]:
                break
        check(current["can_hold"] is True, "hold did not reset after lock")
        check(current["score"] == 0 and current["total_lines"] == 0, "empty-board lock changed scoring")
        check(active_piece(current)["type"] == session["held"]["next_piece"], "preview not consumed at lock")
        preview = current["next_piece"]
        expected_active = current["hold_piece"]
        expected_hold = active_piece(current)["type"]
        status, swapped = request("POST", path + "/hold")
        check(status == 200, f"swap HTTP {status}")
        check(active_piece(swapped)["type"] == expected_active, "held piece did not spawn")
        centered_spawn(active_piece(swapped))
        check(swapped["hold_piece"] == expected_hold, "active piece did not enter hold")
        check(swapped["next_piece"] == preview, "swap consumed preview")
        check(swapped["can_hold"] is False, "swap did not enter cooldown")
        session["swapped"] = swapped
        return "lock reset hold; swap preserved preview, score and line count"

    case("S2-03/S2-12", lock_and_swap)

    def restart():
        status, state = request("POST", "/api/games")
        check(status == created_status, f"restart/new game HTTP {status}; expected {created_status}")
        check(state["id"] != game_id, "restart did not create a new session")
        check(board_valid(state), "restart board invalid")
        expected = {"score": 0, "total_lines": 0, "level": 1, "gravity_interval_ms": 500, "hold_piece": None, "can_hold": True, "status": "playing"}
        for key, value in expected.items():
            check(state.get(key) == value, f"restart {key}: {state.get(key)}")
        check(state["next_piece"] in TYPES, "restart preview invalid")
        return "restart restored all Stage 2 defaults"

    case("S2-15", restart)

    def api_contract():
        status, _ = request("GET", "/api/games/not-a-real-session")
        check(status == 404, f"missing game GET HTTP {status}")
        status, _ = request("POST", "/api/games/not-a-real-session/hold")
        check(status == 404, f"missing game hold HTTP {status}")
        return "missing game GET and hold return 404"

    case("S2-16", api_contract)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--created-status", type=int, choices=(200, 201), default=201,
                        help="Exact expected create/restart HTTP status from this tool's own Stage 1 contract; default 201, Tessl 200")
    args = parser.parse_args()
    observations = []
    cases = run(args.base_url.rstrip("/"), args.created_status, observations)
    result = {"version": VERSION,
              "researcher_created": True,
              "measured_at_utc": datetime.now(timezone.utc).isoformat(),
              "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
              "parent_version": "1.2", "parent_version_sha256": PARENT_VERSION_SHA256,
              "base_url": args.base_url,
              "expected_create_http_status": args.created_status,
              "observed_create_http_statuses": [row["actual_http_status"] for row in observations if row["method"] == "POST" and row["path"] == "/api/games"],
              "http_status_normalization": False, "native_representation_adapter": "v1.3 supports shape/type and object/array coordinates only in observation helpers; raw responses retained unchanged",
              "scope": "Same seven gameplay records/eightcatalogIDs asv1.2; representation adapter only, not fulltwentycase catalog",
              "http_observations": observations, "cases": cases}
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if all(case["status"] == "pass" for case in result["cases"]) else 1)
