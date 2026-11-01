"""Small official-ACP driver. Default is configuration-only: never sends a prompt.

Protocol: https://kiro.dev/docs/cli/v3/acp-migration/
Prompt schema: https://agentclientprotocol.com/protocol/v1/prompt-turn
"""
import argparse
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

from kiro_research import DOCS, ROOT, digest, seed_info, stamp, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True)
    parser.add_argument("--phase", choices=("specify", "spec_revision", "implement", "clarify"))
    parser.add_argument("--prompt-file", type=Path)
    parser.add_argument("--execute", action="store_true", help="Explicitly allow one model prompt after verified configuration")
    parser.add_argument("--allow-tools", action="store_true", help="For authorized generation only: select offered one-time allow options; never persist consent")
    args = parser.parse_args()
    if not args.label or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in args.label):
        raise ValueError("Unsafe label")
    if bool(args.prompt_file) != args.execute or args.allow_tools and not args.execute:
        raise ValueError("Prompt requires both --prompt-file and --execute; tools require --execute")
    if args.execute and not args.phase:
        raise ValueError("Explicit execution phase required")
    folder = DOCS if args.execute else DOCS / "researcher-setup"
    folder.mkdir(exist_ok=True)
    paths = {name: folder / f"{args.label}.{suffix}" for name, suffix in {"stream": "stdout.jsonl", "rpc": "rpc.jsonl", "stderr": "stderr.txt", "result": "run.json" if args.execute else "acp-preflight.json", "started": "started.json"}.items()}
    if any(p.exists() for p in paths.values()):
        raise FileExistsError("Use a new immutable label")
    exe = Path(os.environ["USERPROFILE"]) / "AppData/Local/Kiro-Cli/kiro-cli.exe"
    runtime = {"path": str(exe), "version": subprocess.check_output([str(exe), "--version"], text=True).strip(), "sha256": digest(exe.read_bytes())}
    pin = json.loads((DOCS / "kiro-runtime-pin.json").read_text())
    if pin != runtime:
        raise RuntimeError("Runtime differs from controlled pin")
    prompt = None
    seed, seed_meta = seed_info()
    if seed_meta["seed_file_sha256"] != "63919779DD4104076FBABCB130CE296A160FA840E0B4755A2AA5D90757ADA8EF":
        raise RuntimeError("Frozen common seed changed")
    if args.execute:
        prompt = args.prompt_file.read_text(encoding="utf-8-sig")
        if seed not in prompt.replace("\r\n", "\n"):
            raise RuntimeError("Full common seed missing; refusing prompt")
        target = DOCS / f"{args.label}.prompt.txt"
        if target.exists() and target.read_text(encoding="utf-8-sig") != prompt:
            raise RuntimeError("Existing prompt differs")
        if not target.exists():
            target.write_text(prompt, encoding="utf-8")
    record = {"researcher_created": True, "label": args.label, "phase": args.phase or "configuration_only", "started": stamp(), "runtime": runtime, "submission_method": "official ACP stdio; verified advertised spec/auto before optional prompt", "requested_model": "auto", "requested_mode": "spec", "model_prompt_sent": False, **seed_meta}
    if args.execute:
        record.update(prompt_characters=len(prompt), prompt_sha256=digest(target.read_bytes()), resume_id=None, stdout=str(paths["stream"]), stderr=str(paths["stderr"]))
    started = time.perf_counter()
    command = [str(exe), "acp", "--agent-engine=v3", "--auth-method=cli"]
    env = os.environ.copy()
    env["LOCALAPPDATA"] = str(exe.parent.parent)
    env["APPDATA"] = str(Path(os.environ["USERPROFILE"]) / "AppData/Roaming")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PATH"] = str(ROOT / "backend/.venv/Scripts") + os.pathsep + env["PATH"]
    messages = queue.Queue()
    state = {"options": {}, "mode": None, "session_id": None}
    code = 1
    with paths["stream"].open("x", encoding="utf-8") as stream, paths["rpc"].open("x", encoding="utf-8") as rpc, paths["stderr"].open("xb") as err:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err, text=True, encoding="utf-8", errors="replace")
        record["owned_process_id"] = child.pid
        if args.execute:
            write(paths["started"], record)
        def emit(kind, data):
            stream.write(json.dumps({"type": kind, "data": data}, ensure_ascii=False) + "\n")
            stream.flush()
        def reader():
            for line in child.stdout:
                messages.put(line)
            messages.put(None)
        threading.Thread(target=reader, daemon=True).start()
        sequence = 0
        def send(value):
            rpc.write(json.dumps({"direction": "sent", "at_utc": stamp(), "message": value}, ensure_ascii=False) + "\n")
            rpc.flush()
            child.stdin.write(json.dumps(value, ensure_ascii=False) + "\n")
            child.stdin.flush()
        def adopt_options(result):
            for option in result.get("configOptions", []):
                state["options"][option["id"]] = option
            modes = result.get("modes", {})
            if modes.get("currentModeId"):
                state["mode"] = modes["currentModeId"]
            if modes.get("availableModes"):
                state["available_modes"] = modes["availableModes"]
        def call(method, params, timeout=60):
            nonlocal sequence
            sequence += 1
            request_id = sequence
            send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
            deadline = time.monotonic() + timeout
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("ACP request deadline expired")
                line = messages.get(timeout=remaining)
                if line is None:
                    raise RuntimeError("ACP transport closed before request response")
                value = json.loads(line)
                # Auth is CLI-owned; never relay or log credential requests.
                if "auth" in value.get("method", "").lower():
                    raise RuntimeError("Unexpected client authentication request; no credential relay supported")
                rpc.write(json.dumps({"direction": "received", "at_utc": stamp(), "message": value}, ensure_ascii=False) + "\n")
                rpc.flush()
                if value.get("method") == "session/update":
                    params_update = value["params"]
                    emit("sessionUpdate", params_update)
                    update = params_update["update"]
                    adopt_options(update)
                    if update.get("sessionUpdate") == "current_mode_update":
                        state["mode"] = update.get("currentModeId")
                elif "method" in value and "id" in value:
                    if value["method"] == "session/request_permission":
                        options = value.get("params", {}).get("options", [])
                        option = next((o for o in options if o.get("kind") == "allow_once"), None) if args.allow_tools and record["model_prompt_sent"] else None
                        outcome = {"outcome": "selected", "optionId": option["optionId"]} if option else {"outcome": "cancelled"}
                        send({"jsonrpc": "2.0", "id": value["id"], "result": {"outcome": outcome}})
                    else:
                        send({"jsonrpc": "2.0", "id": value["id"], "error": {"code": -32601, "message": "Client method not supported"}})
                elif value.get("id") == request_id:
                    if "error" in value:
                        raise RuntimeError(json.dumps(value["error"]))
                    result = value.get("result", {})
                    adopt_options(result)
                    return result
        try:
            emit("runStarted", {"payloadSchema": "acp", "acpProtocolVersion": 1, "engine": "v3", "transport": "official stdio", "model_prompt_sent": False})
            initialized = call("initialize", {"protocolVersion": 1, "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False}, "clientInfo": {"name": "tetris-research-driver", "version": "1"}})
            record["initialize"] = initialized
            created = call("session/new", {"cwd": str(ROOT), "mcpServers": []})
            sid = created["sessionId"]
            state["session_id"] = sid
            record["session_id"] = sid
            for config_id, desired in (("mode", "spec"), ("model", "auto")):
                option = state["options"].get(config_id)
                choices = option.get("options", []) if option else []
                if not option or desired not in {item.get("value") for item in choices}:
                    raise RuntimeError(f"Required advertised config choice unavailable: {config_id}={desired}")
                call("session/set_config_option", {"sessionId": sid, "configId": config_id, "value": desired})
                if state["options"].get(config_id, {}).get("currentValue") != desired:
                    raise RuntimeError(f"Server did not verify {config_id}={desired}")
            record["verified_configuration"] = {key: state["options"][key]["currentValue"] for key in ("mode", "model")}
            record["configuration_verified_before_prompt_at_utc"] = stamp()
            if args.execute:
                record["model_prompt_sent"] = True
                write(paths["started"], record)
                result = call("session/prompt", {"sessionId": sid, "prompt": [{"type": "text", "text": prompt}]}, timeout=14400)
                record["prompt_result"] = result
                reason = result.get("stopReason")
                record.update(rpc_prompt_request_succeeded=True, generation_stop_reason=reason, generation_turn_ended=reason == "end_turn")
                status = "success" if reason == "end_turn" else ("refused" if reason == "refusal" else "cancelled" if reason == "cancelled" else "incomplete")
                emit("runFinished", {"sessionId": sid, "status": status, "stopReason": reason, "finalTextTruncated": False, "status_scope": "RPC result/stopReason; not application acceptance"})
                code = 0 if reason == "end_turn" else 2
            else:
                code = 0
        except Exception as exc:
            record["error"] = str(exc)
        finally:
            child.stdin.close()
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.terminate()  # Only this driver-owned transport process.
                child.wait(timeout=8)
    record.update(ended=stamp(), duration_seconds=round(time.perf_counter() - started, 3), exit_code=code, transport_exit_code=child.returncode, inference_scope="no session/prompt sent" if not record["model_prompt_sent"] else "one explicit prompt after verified configuration")
    write(paths["result"], record)
    print(json.dumps({key: record.get(key) for key in ("label", "session_id", "verified_configuration", "model_prompt_sent", "error", "exit_code")}, ensure_ascii=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
