#!/usr/bin/env python3
"""Continuum golden-path operator console.

One control surface so we never hand-repair the demo database minutes before
presenting. Every command drives the SAME canonical machinery.

    python scripts/demo_console.py health
    python scripts/demo_console.py reset
    python scripts/demo_console.py seed
    python scripts/demo_console.py ask "Who owns Acme?"
    python scripts/demo_console.py apply gmail-transition
    python scripts/demo_console.py apply gmail-aug5
    python scripts/demo_console.py status
    python scripts/demo_console.py run            # scripted frozen narrative
    python scripts/demo_console.py gates          # acceptance gates (runs 3x)
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# ASCII-only markers so output is safe on any terminal codepage (Windows cp1252).
OK, BAD, DOT, OFF = "[OK]", "[X] ", " *  ", " -  "

# Best-effort UTF-8 stdout (harmless if unsupported); output stays ASCII anyway.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scripts.demo_golden_path as gp  # noqa: E402


def line(s: str = "") -> None:
    print(s, flush=True)


class _Client:
    """HydraDB client context; raises a friendly error if unreachable."""

    def __enter__(self):
        from continuum.hydradb import HydraDBClient

        self.client = HydraDBClient()
        self.client.__enter__()
        self.client.health_check()
        return self.client

    def __exit__(self, *exc):
        self.client.__exit__(*exc)


def _fmt_state(res: dict) -> str:
    owner = res.get("owner") or "-"
    eff = res.get("valid_from") or "-"
    status = res.get("status") or "-"
    srcs = " + ".join(res.get("sources") or []) or "-"
    return f"{owner}  (effective {eff}, status={status}, evidence: {srcs})"


# -- Commands ---------------------------------------------------------------

def cmd_reset(scenario):
    with _Client() as c:
        gp.reset(c, scenario)
    line(f"{OK} demo reset - cleared: " + ", ".join(scenario["entity_keys"]))


def cmd_seed(scenario):
    with _Client() as c:
        gp.seed(c, scenario)
        res = gp.ask(c, scenario, "Who owns Acme?")
    line(f"{OK} demo seeded (initial Slack state)")
    line(f"     Who owns Acme?  ->  {_fmt_state(res)}")


def cmd_apply(scenario, key):
    with _Client() as c:
        gp.apply(c, scenario, key)
        res = gp.ask(c, scenario, "Who owns Acme now?")
    ev = gp.find_event(scenario, key)
    line(f"{OK} applied '{key}' - {ev.get('narrative', '')}")
    line(f"     Who owns Acme now?  ->  {_fmt_state(res)}")


def cmd_ask(scenario, question):
    with _Client() as c:
        res = gp.ask(c, scenario, question)
    line(f"Q: {question}")
    line(f"A: {_fmt_state(res)}")


def cmd_status(scenario):
    with _Client() as c:
        state = gp.mcp_state(c, scenario)
        graph = gp.graph_summary(c, scenario)
        hist = gp.mcp_history(c, scenario)
    value = (state or {}).get("value") or {}
    line("CURRENT COMPANY MEMORY")
    line(f"  {scenario['focus_entity']} owner: {value.get('name', '-')} "
         f"(effective {state.get('valid_from', '-')}, status={state.get('status', '-')})")
    line(f"  graph: entities={graph['entities']} sources={graph['sources']} "
         f"({graph['node_count']} nodes, {graph['edge_count']} edges)")
    rows = hist if isinstance(hist, list) else (hist or {}).get("history", [])
    line("  history:")
    for h in rows or []:
        nm = (h.get("value") or {}).get("name") or h.get("subject_name") or h.get("name") or "-"
        line(f"    - {nm}: {h.get('valid_from', '-')} -> {h.get('valid_to') or 'now'}")


def cmd_run(scenario):
    """The frozen demo narrative, printed cleanly."""
    with _Client() as c:
        line("---- Continuum golden path ------------------------------")
        gp.reset(c, scenario)
        gp.seed(c, scenario)
        line("STEP 1  Slack: Morgan owns the Acme account.")
        r = gp.ask(c, scenario, "Who owns Acme?")
        line(f"STEP 2  Q: Who owns Acme?  ->  {_fmt_state(r)}")

        gp.apply(c, scenario, "gmail-transition")
        line("STEP 3  Gmail: ownership transfers Morgan -> Priya, effective Aug 3.")
        r = gp.ask(c, scenario, "Who owns Acme now?")
        line(f"STEP 4  Q: Who owns Acme now?  ->  {_fmt_state(r)}")
        b = gp.ask(c, scenario, "Who owned Acme before Priya?")
        line(f"STEP 5  Q: Who owned Acme before Priya?  ->  {b.get('owner')}")

        gp.apply(c, scenario, "gmail-aug5")
        line("STEP 6  Gmail: correction - effective Aug 5.")
        r = gp.ask(c, scenario, "Who owns Acme now?")
        line(f"STEP 7  Q: Who owns Acme now?  ->  {_fmt_state(r)}")

        g = gp.graph_summary(c, scenario)
        line(f"STEP 8  Graph: entities={g['entities']}  sources={g['sources']}")
        m = gp.mcp_state(c, scenario)
        mv = (m or {}).get("value") or {}
        line(f"STEP 9  MCP: get_current_state -> {mv.get('name')} (effective {m.get('valid_from')})")
    line("--------------------------------------------------------")
    line("Web == Slack == Graph == MCP: the same canonical state.")


def _one_run(c, scenario) -> dict:
    gp.reset(c, scenario)
    gp.seed(c, scenario)
    initial = gp.ask(c, scenario, "Who owns Acme?")
    gp.apply(c, scenario, "gmail-transition")
    after_t = gp.ask(c, scenario, "Who owns Acme now?")
    before = gp.ask(c, scenario, "Who owned Acme before Priya?")
    gp.apply(c, scenario, "gmail-aug5")
    after_5 = gp.ask(c, scenario, "Who owns Acme now?")
    graph = gp.graph_summary(c, scenario)
    mcp = gp.mcp_state(c, scenario)
    mv = (mcp or {}).get("value") or {}
    return {
        "initial_owner": initial.get("owner"),
        "t_owner": after_t.get("owner"),
        "t_effective": after_t.get("valid_from"),
        "before_owner": before.get("owner"),
        "aug5_owner": after_5.get("owner"),
        "aug5_effective": after_5.get("valid_from"),
        "aug5_sources": after_5.get("sources"),
        "graph_entities": graph["entities"],
        "mcp_owner": mv.get("name"),
        "mcp_effective": mcp.get("valid_from"),
    }


def cmd_gates(scenario) -> int:
    line("Running acceptance gates (3x for determinism)...")
    runs = []
    with _Client() as c:
        for i in range(3):
            runs.append(_one_run(c, scenario))
            line(f"  run {i + 1} complete")
    r = runs[0]
    deterministic = all(x == r for x in runs)
    checks = [
        ("Gate 1  Initial memory (Slack -> Morgan)", r["initial_owner"] == "Morgan"),
        ("Gate 2  Cross-source update (Gmail -> Priya, Aug 3)",
         r["t_owner"] == "Priya" and r["t_effective"] == "2026-08-03"),
        ("Gate 3  Temporal memory (before Priya -> Morgan)", r["before_owner"] == "Morgan"),
        ("Gate 4  Evidence (Slack + Gmail)",
         {s.lower() for s in (r["aug5_sources"] or [])} >= {"slack", "gmail"}),
        ("Gate 5  Graph reflects state (Acme, Morgan, Priya)",
         {"acme", "morgan", "priya"} <= {e.lower() for e in r["graph_entities"]}),
        ("Gate 6  MCP parity (== web current owner)",
         r["mcp_owner"] == r["aug5_owner"] == "Priya"),
        ("Gate 8  Live update (Aug 5 supersedes)", r["aug5_effective"] == "2026-08-05"),
        ("Gate 7  Repeatable (3x identical)", deterministic),
    ]
    line("")
    ok = True
    for label, passed in checks:
        line(f"  {OK if passed else BAD} {label}")
        ok = ok and passed
    line("")
    line("ALL GATES PASSED" if ok else "SOME GATES FAILED")
    return 0 if ok else 2


def cmd_parity(scenario) -> int:
    """Prove Web == Slack == MCP == Graph all read the same canonical state."""
    q = "Who owns Acme now?"
    with _Client() as c:
        web = gp.ask(c, scenario, q)                       # QueryService / /v1/ask
        mcp = gp.mcp_state(c, scenario)                    # MCP adapter
        slack = gp.slack_answer(c, scenario, q)            # Slack Block Kit formatter
        graph = gp.graph_summary(c, scenario)              # canonical graph export
    web_owner = web.get("owner")
    mcp_owner = (mcp.get("value") or {}).get("name")
    slack_text = slack.get("text", "")
    slack_ok = bool(web_owner) and web_owner in slack_text
    graph_ok = bool(web_owner) and web_owner in graph["entities"]

    line("Surface parity for: \"" + q + "\"")
    line(f"  Web/API (QueryService) : {web_owner}  (effective {web.get('valid_from')})")
    line(f"  MCP  (get_current_state): {mcp_owner}  (effective {mcp.get('valid_from')})")
    line(f"  Slack (Block Kit)       : {slack_text.splitlines()[0] if slack_text else '-'}")
    line(f"  Graph (entity nodes)    : {graph['entities']}")
    line("")
    checks = [
        ("Web == MCP", web_owner == mcp_owner and web.get("valid_from") == mcp.get("valid_from")),
        ("Slack answer matches Web owner", slack_ok),
        ("Graph contains current owner", graph_ok),
        ("Owner is Priya (current scenario state)", web_owner == "Priya"),
    ]
    ok = True
    for label, passed in checks:
        line(f"  {OK if passed else BAD} {label}")
        ok = ok and passed
    line("")
    line("PARITY OK - one memory, every surface." if ok else "PARITY FAILED - a surface diverged.")
    return 0 if ok else 2


def cmd_recovery(scenario) -> int:
    """Gate 9: memory survives a full client/process teardown + reconnect."""
    line("Recovery: set state, tear down connection, reconnect, verify intact...")
    with _Client() as c:
        gp.reset(c, scenario)
        gp.seed(c, scenario)
        gp.apply(c, scenario, "gmail-transition")
        gp.apply(c, scenario, "gmail-aug5")
        before = gp.mcp_state(c, scenario)
    # connection closed above == process/worker teardown
    with _Client() as c2:  # fresh connection == restart
        after = gp.mcp_state(c2, scenario)
    b = (before.get("value") or {}).get("name"), before.get("valid_from")
    a = (after.get("value") or {}).get("name"), after.get("valid_from")
    line(f"  before teardown: {b[0]} (effective {b[1]})")
    line(f"  after reconnect: {a[0]} (effective {a[1]})")
    ok = a == b == ("Priya", "2026-08-05")
    line("")
    line(f"  {OK if ok else BAD} Gate 9  Memory intact across restart")
    line("")
    line("RECOVERY OK - company memory persists (HydraDB is the source of truth)."
         if ok else "RECOVERY FAILED")
    line("Note: queue replay / idempotent re-ingest is covered by "
         "tests/pipeline/test_memory_worker_reliability.py")
    return 0 if ok else 2


def cmd_health(scenario) -> int:
    line("Continuum Demo Health")
    required: list[tuple[str, bool, str]] = []
    optional: list[tuple[str, bool, str]] = []

    try:
        assert scenario["events"] and scenario["entity_keys"]
        required.append(("scenario loads", True, f"{len(scenario['events'])} events"))
    except Exception as exc:  # noqa: BLE001
        required.append(("scenario loads", False, str(exc)))

    try:
        import continuum.benchmark  # noqa: F401
        from continuum.delivery.mcp_adapter import ContinuumMCPAdapter  # noqa: F401
        required.append(("query/MCP layer importable", True, ""))
    except Exception as exc:  # noqa: BLE001
        required.append(("query/MCP layer importable", False, str(exc)))

    hydradb_ok = False
    try:
        with _Client() as c:
            hydradb_ok = True
            required.append(("HydraDB reachable", True, "127.0.0.1:7687"))
            try:
                gp.graph_summary(c, scenario)
                required.append(("graph readable", True, ""))
            except Exception as exc:  # noqa: BLE001
                required.append(("graph readable", False, str(exc)))
            try:
                gp.ask(c, scenario, "Who owns Acme?")
                required.append(("QueryService + evidence readable", True, ""))
            except Exception as exc:  # noqa: BLE001
                required.append(("QueryService + evidence readable", False, str(exc)))
    except Exception as exc:  # noqa: BLE001
        required.append(("HydraDB reachable", False, f"{exc.__class__.__name__}: run `make hydradb-up`"))

    optional.append(("Slack bot token", bool(os.environ.get("SLACK_BOT_TOKEN")),
                     "set" if os.environ.get("SLACK_BOT_TOKEN") else "unset (fixtures mode ok)"))
    gmail_tok = (ROOT / "gmail_token.json").exists() or bool(os.environ.get("GMAIL_TOKEN"))
    optional.append(("Gmail credentials", gmail_tok,
                     "present" if gmail_tok else "unset (fixtures mode ok)"))

    line("")
    line("  REQUIRED")
    all_required_ok = True
    for label, ok, detail in required:
        all_required_ok = all_required_ok and ok
        line(f"    {OK if ok else BAD} {label}{('  - ' + detail) if detail else ''}")
    line("  OPTIONAL (live mode only)")
    for label, ok, detail in optional:
        line(f"    {DOT if ok else OFF} {label}{('  - ' + detail) if detail else ''}")
    line("")
    if all_required_ok:
        line("HEALTH: GREEN - safe to run the golden path.")
        return 0
    line("HEALTH: RED - fix the [X] items above before demoing.")
    return 1 if not hydradb_ok else 2


# -- CLI --------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    sub.add_parser("reset")
    sub.add_parser("seed")
    sub.add_parser("status")
    sub.add_parser("run")
    sub.add_parser("gates")
    sub.add_parser("parity")
    sub.add_parser("recovery")
    p_apply = sub.add_parser("apply")
    p_apply.add_argument("event", help="event key, e.g. gmail-transition")
    p_ask = sub.add_parser("ask")
    p_ask.add_argument("question", help="natural-language question")
    args = parser.parse_args()

    scenario = gp.load_scenario()

    try:
        if args.cmd == "health":
            return cmd_health(scenario)
        if args.cmd == "reset":
            cmd_reset(scenario)
        elif args.cmd == "seed":
            cmd_seed(scenario)
        elif args.cmd == "apply":
            cmd_apply(scenario, args.event)
        elif args.cmd == "ask":
            cmd_ask(scenario, args.question)
        elif args.cmd == "status":
            cmd_status(scenario)
        elif args.cmd == "run":
            cmd_run(scenario)
        elif args.cmd == "gates":
            return cmd_gates(scenario)
        elif args.cmd == "parity":
            return cmd_parity(scenario)
        elif args.cmd == "recovery":
            return cmd_recovery(scenario)
        return 0
    except Exception as exc:  # noqa: BLE001
        line(f"ERROR: {exc.__class__.__name__}: {exc}")
        if "hydradb" in str(exc).lower() or "7687" in str(exc) or "ServiceUnavailable" in exc.__class__.__name__:
            line("Hint: HydraDB is not running. Start it with `make hydradb-up` (needs Docker).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
