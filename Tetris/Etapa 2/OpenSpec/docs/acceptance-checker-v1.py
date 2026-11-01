"""Black-box Stage 2 acceptance checks for any of the five implementations.

Usage: python check_api.py --base-url http://127.0.0.1:8000 --output evidence.json
The same script and expected values are retained across tools.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


TYPES = set("IOTJLSZ")


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


def run(base: str):
    results = []

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
        status, state = call(base, "POST", "/api/games")
        check(status == 201, f"create HTTP {status}")
        check(board_valid(state), "board is not 20x10")
        expected = {"score": 0, "total_lines": 0, "level": 1, "gravity_interval_ms": 500, "hold_piece": None, "can_hold": True}
        for key, value in expected.items():
            check(state.get(key) == value, f"{key}: expected {value}, got {state.get(key)}")
        check(state.get("next_piece") in TYPES, "invalid preview")
        check(state["active_piece"]["type"] in TYPES, "invalid active piece")
        session["id"], session["initial"] = state["id"], state
        return "new game fields, board and tetromino types valid"

    case("S2-01", initial)
    if "id" not in session:
        return results
    game_id = session["id"]
    path = f"/api/games/{game_id}"

    def peek():
        status1, a = call(base, "GET", path)
        status2, b = call(base, "GET", path)
        check(status1 == 200 and status2 == 200, f"GET statuses {status1}, {status2}")
        check(a == b == session["initial"], "GET mutated the game or preview")
        return "two reads preserved full state"

    case("S2-02", peek)

    def first_hold():
        prior = session["initial"]
        status, state = call(base, "POST", path + "/hold")
        check(status == 200, f"hold HTTP {status}")
        check(state["hold_piece"] == prior["active_piece"]["type"], "hold slot mismatch")
        check(state["active_piece"]["type"] == prior["next_piece"], "preview did not spawn")
        check(state["active_piece"]["origin"] == [0, 3], "spawn origin mismatch")
        check(state["next_piece"] in TYPES, "invalid new preview")
        check(state["can_hold"] is False, "hold did not enter cooldown")
        session["held"] = state
        return "first hold consumed preview and entered cooldown"

    case("S2-10", first_hold)

    def repeated_hold():
        check("held" in session, "first hold failed")
        before = session["held"]
        status, _ = call(base, "POST", path + "/hold")
        _, after = call(base, "GET", path)
        check(status in (200, 400, 409), f"unexpected rejection status {status}")
        check(before == after, "repeated hold mutated game state")
        return f"second hold rejected with HTTP {status}; state preserved"

    case("S2-11", repeated_hold)

    def lock_and_swap():
        check("held" in session, "first hold failed")
        current = session["held"]
        for _ in range(25):
            status, current = call(base, "POST", path + "/move", {"direction": "down"})
            check(status == 200, f"move HTTP {status}")
            if current["can_hold"]:
                break
        check(current["can_hold"] is True, "hold did not reset after lock")
        check(current["score"] == 0 and current["total_lines"] == 0, "empty-board lock changed scoring")
        check(current["active_piece"]["type"] == session["held"]["next_piece"], "preview not consumed at lock")
        preview = current["next_piece"]
        expected_active = current["hold_piece"]
        expected_hold = current["active_piece"]["type"]
        status, swapped = call(base, "POST", path + "/hold")
        check(status == 200, f"swap HTTP {status}")
        check(swapped["active_piece"]["type"] == expected_active, "held piece did not spawn")
        check(swapped["active_piece"]["origin"] == [0, 3], "swapped origin mismatch")
        check(swapped["hold_piece"] == expected_hold, "active piece did not enter hold")
        check(swapped["next_piece"] == preview, "swap consumed preview")
        check(swapped["can_hold"] is False, "swap did not enter cooldown")
        session["swapped"] = swapped
        return "lock reset hold; swap preserved preview, score and line count"

    case("S2-03/S2-12", lock_and_swap)

    def restart():
        status, state = call(base, "POST", "/api/games")
        check(status == 201, f"restart/new game HTTP {status}")
        check(state["id"] != game_id, "restart did not create a new session")
        check(board_valid(state), "restart board invalid")
        expected = {"score": 0, "total_lines": 0, "level": 1, "gravity_interval_ms": 500, "hold_piece": None, "can_hold": True, "status": "playing"}
        for key, value in expected.items():
            check(state.get(key) == value, f"restart {key}: {state.get(key)}")
        check(state["next_piece"] in TYPES, "restart preview invalid")
        return "restart restored all Stage 2 defaults"

    case("S2-15", restart)

    def api_contract():
        status, _ = call(base, "GET", "/api/games/not-a-real-session")
        check(status == 404, f"missing game GET HTTP {status}")
        status, _ = call(base, "POST", "/api/games/not-a-real-session/hold")
        check(status == 404, f"missing game hold HTTP {status}")
        return "missing game GET and hold return 404"

    case("S2-16", api_contract)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = {"base_url": args.base_url, "cases": run(args.base_url.rstrip("/"))}
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if all(case["status"] == "pass" for case in result["cases"]) else 1)
