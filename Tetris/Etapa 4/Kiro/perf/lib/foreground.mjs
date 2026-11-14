// READ-ONLY Win32 / native PowerShell foreground telemetry (task 20.1).
//
// This module reads the OS foreground window's HWND, owning PID, title,
// visibility, and rectangle using ONLY read-only Win32 calls through native
// PowerShell (design.md "Read-only foreground telemetry"; Req 26.5, 26.6). It
// NEVER activates, moves, resizes, or fakes a foreground window: there is no
// SetForegroundWindow, no SendKeys, and no PowerShell UI-automation here. It
// only observes. The harness uses it to record whether the actual actor window
// holds the OS foreground throughout a measured window.
//
// Importing this module spawns NO process. PowerShell is spawned only when a
// function is called, and only to run the read-only probe script below.

import { spawn } from "node:child_process";

// The read-only probe script. It P/Invokes user32 functions that only READ
// window state:
//   GetForegroundWindow, GetWindowThreadProcessId, GetWindowTextLength/Text,
//   IsWindowVisible, GetWindowRect.
// It emits a single JSON object on stdout. There is deliberately NO
// SetForegroundWindow, ShowWindow, SetWindowPos, MoveWindow, keybd_event,
// SendInput, or SendKeys reference anywhere in this string.
const READ_ONLY_PROBE = String.raw`
$ErrorActionPreference = 'Stop'
$sig = @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class FgRead {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);
  [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr hWnd);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
}
'@
Add-Type -TypeDefinition $sig | Out-Null
$h = [FgRead]::GetForegroundWindow()
$pid2 = 0
$tid = [FgRead]::GetWindowThreadProcessId($h, [ref]$pid2)
$len = [FgRead]::GetWindowTextLength($h)
$sb = New-Object System.Text.StringBuilder ($len + 1)
[void][FgRead]::GetWindowText($h, $sb, $sb.Capacity)
$vis = [FgRead]::IsWindowVisible($h)
$rect = New-Object FgRead+RECT
[void][FgRead]::GetWindowRect($h, [ref]$rect)
$obj = [ordered]@{
  hwnd    = [Int64]$h
  pid     = $pid2
  threadId = $tid
  title   = $sb.ToString()
  visible = [bool]$vis
  rect    = [ordered]@{ left = $rect.Left; top = $rect.Top; right = $rect.Right; bottom = $rect.Bottom }
  readOnly = $true
}
$obj | ConvertTo-Json -Compress
`;

// Spawn native PowerShell to run the read-only probe once and resolve its
// parsed JSON. Resolves to null fields (never fabricated numbers) if the probe
// cannot run (e.g. non-Windows host) so the caller records "unknown", not 0.
// `timeoutMs` bounds the probe so it can never hang a measured window.
export function readForegroundWindow({ powershellPath = "powershell", timeoutMs = 4000 } = {}) {
  return new Promise((resolve) => {
    let child;
    let settled = false;
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };
    const unknown = (reason) => ({
      hwnd: null,
      pid: null,
      threadId: null,
      title: null,
      visible: null,
      rect: null,
      readOnly: true,
      error: reason,
      sampledAt: new Date().toISOString(),
    });

    try {
      child = spawn(
        powershellPath,
        ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", READ_ONLY_PROBE],
        { windowsHide: true },
      );
    } catch (err) {
      finish(unknown(`spawn_failed: ${err && err.message ? err.message : String(err)}`));
      return;
    }

    let out = "";
    let errOut = "";
    const timer = setTimeout(() => {
      try { child.kill(); } catch (_) {}
      finish(unknown("timeout"));
    }, timeoutMs);

    child.stdout.on("data", (d) => { out += d.toString(); });
    child.stderr.on("data", (d) => { errOut += d.toString(); });
    child.on("error", (err) => {
      clearTimeout(timer);
      finish(unknown(`process_error: ${err && err.message ? err.message : String(err)}`));
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        finish(unknown(`exit_${code}: ${errOut.trim().slice(0, 200) || "no stderr"}`));
        return;
      }
      try {
        const parsed = JSON.parse(out.trim());
        parsed.readOnly = true;
        parsed.sampledAt = new Date().toISOString();
        finish(parsed);
      } catch (parseErr) {
        finish(unknown(`parse_failed: ${parseErr && parseErr.message ? parseErr.message : String(parseErr)}`));
      }
    });
  });
}

// Decide whether a foreground telemetry sample belongs to a given owned PID
// (and optionally matches an expected window-title substring). Used to record
// whether the OS foreground is the actual actor window WITHOUT ever forcing it:
// if it is not foreground, the sample is recorded honestly as not-foreground,
// not corrected.
export function foregroundMatchesActor(sample, actorPid, titleSubstring) {
  if (!sample || sample.pid == null) {
    return { isActorForeground: null, titleMatches: null };
  }
  const isActorForeground = typeof actorPid === "number" ? sample.pid === actorPid : null;
  let titleMatches = null;
  if (typeof titleSubstring === "string" && typeof sample.title === "string") {
    titleMatches = sample.title.includes(titleSubstring);
  }
  return { isActorForeground, titleMatches };
}

// The READY_FOR_FOREGROUND signal payload. The harness emits this AFTER both
// clients open/join, carrying the ACTUAL actor identity (owned Chrome PID,
// window title, and HWND if known), then waits BOUNDEDLY for a real foreground
// transition performed by the controller/user. The harness does not perform the
// transition itself.
export function readyForForegroundSignal({ actorPid, actorTitle, actorHwnd }) {
  return {
    signal: "READY_FOR_FOREGROUND",
    actorPid: typeof actorPid === "number" ? actorPid : null,
    actorTitle: typeof actorTitle === "string" ? actorTitle : null,
    actorHwnd: typeof actorHwnd === "number" ? actorHwnd : null,
    note:
      "Both duel clients are open/joined. Bring the actor window to the OS foreground. " +
      "This harness NEVER activates, moves, or fakes foreground; it only observes read-only " +
      "telemetry and waits boundedly for a real foreground transition.",
    emittedAt: new Date().toISOString(),
  };
}

// Poll read-only foreground telemetry until the actor PID holds the foreground
// or the bounded deadline elapses. Returns the final sample and whether the
// transition was observed. NEVER forces the transition; a timeout is reported
// honestly as "not observed".
export async function waitForForegroundTransition({ actorPid, titleSubstring, deadlineMs = 30000, intervalMs = 500, powershellPath = "powershell" } = {}) {
  const started = Date.now();
  const samples = [];
  let observed = false;
  let last = null;
  while (Date.now() - started < deadlineMs) {
    // eslint-disable-next-line no-await-in-loop
    const sample = await readForegroundWindow({ powershellPath });
    const match = foregroundMatchesActor(sample, actorPid, titleSubstring);
    last = { sample, match, atMs: Date.now() - started };
    samples.push(last);
    if (match.isActorForeground === true) {
      observed = true;
      break;
    }
    // eslint-disable-next-line no-await-in-loop
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return { observed, waitedMs: Date.now() - started, finalSample: last, samples };
}

// ---------------------------------------------------------------------------
// CORRECTION 23 (defect 4): read-only identification of the OWNED actor
// window(s) by PID via EnumWindows + GetWindowThreadProcessId. This is STILL
// read-only: EnumWindows/IsWindowVisible/GetWindowText/GetWindowRect only
// OBSERVE. There is deliberately NO SetForegroundWindow, ShowWindow,
// SetWindowPos, MoveWindow, keybd_event, SendInput, or SendKeys here.
//
// The C# source for Add-Type is assembled from an array joined with newlines so
// this .mjs file contains no nested here-string terminator. The Add-Type body
// still uses PowerShell here-string delimiters at runtime (built below).
const HS_OPEN = String.fromCharCode(64) + String.fromCharCode(39);  // @'
const HS_CLOSE = String.fromCharCode(39) + String.fromCharCode(64); // '@
const ENUM_CSHARP = [
  "using System;",
  "using System.Text;",
  "using System.Collections.Generic;",
  "using System.Runtime.InteropServices;",
  "public static class WinEnum {",
  "  public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);",
  "  [DllImport(\"user32.dll\")] public static extern bool EnumWindows(EnumProc cb, IntPtr lParam);",
  "  [DllImport(\"user32.dll\")] public static extern int GetWindowThreadProcessId(IntPtr hWnd, out int pid);",
  "  [DllImport(\"user32.dll\")] public static extern bool IsWindowVisible(IntPtr hWnd);",
  "  [DllImport(\"user32.dll\")] public static extern int GetWindowTextLength(IntPtr hWnd);",
  "  [DllImport(\"user32.dll\", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, StringBuilder s, int n);",
  "  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }",
  "  [DllImport(\"user32.dll\")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);",
  "  public static List<object> ForPid(int target) {",
  "    var list = new List<object>();",
  "    EnumWindows(delegate(IntPtr h, IntPtr l) {",
  "      int p = 0; GetWindowThreadProcessId(h, out p);",
  "      if (p == target) {",
  "        int len = GetWindowTextLength(h);",
  "        var sb = new StringBuilder(len + 1);",
  "        GetWindowText(h, sb, sb.Capacity);",
  "        RECT r; GetWindowRect(h, out r);",
  "        list.Add(new { hwnd = (long)h, pid = p, title = sb.ToString(), visible = IsWindowVisible(h), rect = new { left = r.Left, top = r.Top, right = r.Right, bottom = r.Bottom } });",
  "      }",
  "      return true;",
  "    }, IntPtr.Zero);",
  "    return list;",
  "  }",
  "}",
].join("\n");

function buildEnumProbe(pid) {
  const safePid = String(Math.trunc(Number(pid)));
  return [
    "$ErrorActionPreference = 'Stop'",
    "$TargetPid = " + safePid,
    "$sig = " + HS_OPEN,
    ENUM_CSHARP,
    HS_CLOSE,
    "Add-Type -TypeDefinition $sig | Out-Null",
    "$windows = [WinEnum]::ForPid($TargetPid)",
    "$obj = [ordered]@{ pid = $TargetPid; readOnly = $true; windows = $windows }",
    "$obj | ConvertTo-Json -Compress -Depth 6",
  ].join("\n");
}

// Enumerate (read-only) the top-level windows owned by a given PID. Resolves to
// { pid, readOnly:true, windows:[{hwnd,title,visible,rect}], error? }. On a
// non-Windows host, a spawn failure, or a timeout it resolves to an `error`
// field with a null `windows` (never a fabricated HWND). `timeoutMs` bounds the
// probe so it can never hang a measured window.
export function enumerateWindowsForPid(pid, { powershellPath = "powershell", timeoutMs = 4000 } = {}) {
  return new Promise((resolve) => {
    let settled = false;
    const finish = (value) => { if (!settled) { settled = true; resolve(value); } };
    const unknown = (reason) => ({ pid: typeof pid === "number" ? pid : null, readOnly: true, windows: null, error: reason, sampledAt: new Date().toISOString() });
    if (typeof pid !== "number") { finish(unknown("no_pid")); return; }
    let child;
    try {
      child = spawn(
        powershellPath,
        ["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", buildEnumProbe(pid)],
        { windowsHide: true },
      );
    } catch (err) {
      finish(unknown("spawn_failed: " + (err && err.message ? err.message : String(err))));
      return;
    }
    let out = "";
    let errOut = "";
    const timer = setTimeout(() => { try { child.kill(); } catch (_) {} finish(unknown("timeout")); }, timeoutMs);
    child.stdout.on("data", (d) => { out += d.toString(); });
    child.stderr.on("data", (d) => { errOut += d.toString(); });
    child.on("error", (err) => { clearTimeout(timer); finish(unknown("process_error: " + (err && err.message ? err.message : String(err)))); });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) { finish(unknown("exit_" + code + ": " + (errOut.trim().slice(0, 200) || "no stderr"))); return; }
      try {
        const parsed = JSON.parse(out.trim() || "{}");
        let windows = parsed.windows ?? [];
        if (windows && !Array.isArray(windows)) windows = [windows];
        finish({ pid, readOnly: true, windows, sampledAt: new Date().toISOString() });
      } catch (parseErr) {
        finish(unknown("parse_failed: " + (parseErr && parseErr.message ? parseErr.message : String(parseErr))));
      }
    });
  });
}

// Decide, from an actor window telemetry sample, whether DOM + OS qualification
// hold TOGETHER for a measured window (defect 4). The actor must hold OS
// foreground (its PID), AND its DOM-side qualification (focus/visibility/exact
// 1280x900 at DPR 1) must all be positively true. Any unknown (null) field is
// NOT qualification: `qualified` is only true when every required signal is
// exactly true. Returns a structured verdict naming the failing signals so an
// invalidated trial records WHY (never a silently ignored flag).
export function qualifyActorWindow({ foregroundSample, actorPid, dom }) {
  const d = dom || {};
  const fgMatch = foregroundMatchesActor(foregroundSample, actorPid);
  const osForeground = fgMatch.isActorForeground === true;
  const domFocus = d.hasFocus === true;
  const domVisible = d.visible === true;
  const sizeOk = d.innerWidth === 1280 && d.innerHeight === 900;
  const dprOk = d.devicePixelRatio === 1;
  const failing = [];
  if (!osForeground) failing.push("os_foreground");
  if (!domFocus) failing.push("dom_focus");
  if (!domVisible) failing.push("dom_visible");
  if (!sizeOk) failing.push("viewport_1280x900");
  if (!dprOk) failing.push("dpr_1");
  return { qualified: failing.length === 0, osForeground, domFocus, domVisible, sizeOk, dprOk, failing };
}
