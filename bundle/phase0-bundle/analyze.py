#!/usr/bin/env python3
"""
Phase 0 analysis script.

Task 1: mine transcripts under transcripts/{cursor,claude-code} -> stats/sessions.csv,
        stats/tool_calls.csv, and claude usage/cache splits -> stats/claude_turns.csv
Task 3: rough compressibility filters over corpus/ -> folded into stats/summary.json

Everything is path-relative to this script's directory (the bundle root), so the
bundle is portable and the analysis can be re-run on another machine.

Usage: python3 analyze.py [bundle_root]
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(__file__))
TRANSCRIPTS = os.path.join(ROOT, "transcripts")
STATS = os.path.join(ROOT, "stats")
CORPUS = os.path.join(ROOT, "corpus")
os.makedirs(STATS, exist_ok=True)


def est_tokens(chars):
    return round(chars / 4)


# ----------------------------------------------------------------------------
# command-family classification (for Shell commands)
# ----------------------------------------------------------------------------
def command_family(cmd):
    c = (cmd or "").strip()
    low = c.lower()
    # Salesforce CLI families
    if re.search(r'\b(sf|sfdx)\b', low):
        if re.search(r'\b(project deploy|force:source:deploy|project:deploy)\b', low):
            return "sf-deploy"
        if re.search(r'\bapex (run test|test run|run)\b|force:apex:test', low):
            return "sf-apex-test"
        if re.search(r'\bdata (query|get|create|update|delete)\b|force:data', low):
            return "sf-data-query"
        if re.search(r'\borg \b|force:org', low):
            return "sf-org"
        return "sf-other"
    if re.match(r'^git\b', low) or re.search(r'\bgit \b', low):
        return "git"
    if re.match(r'^(npm|npx|node|yarn|pnpm)\b', low):
        return "npm/node"
    if re.match(r'^(grep|rg|find|cat|head|tail|ls|sed|awk)\b', low) or re.search(r'\b(grep|find|cat)\b', low):
        return "grep/find/cat"
    return "other"


SELF_TRUNC = re.compile(r'\|\s*(head|tail|grep)\b|\bhead\s+-|\btail\s+-|--json\s*\|\s*jq|\|\s*jq\b')
SF_CMD = re.compile(r'\b(sf|sfdx)\b')
DEPLOY_CMD = re.compile(r'\b(sf|sfdx)\b.*\b(project deploy|force:source:deploy|project:deploy)\b')


def iter_jsonl(path):
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


# ----------------------------------------------------------------------------
# Cursor parsing
#   line: {"role": "...", "message": {"content": [ {type: text|thinking|tool_use} ]}}
#   NOTE: cursor transcripts do NOT persist tool results.
# ----------------------------------------------------------------------------
def parse_cursor(path, project, session_rows, toolcall_rows):
    sid = os.path.splitext(os.path.basename(path))[0]
    n_turns = n_tool_calls = total_chars = n_sf = n_deploy = n_trunc = 0
    for obj in iter_jsonl(path):
        role = obj.get("role")
        msg = obj.get("message", {})
        content = msg.get("content") if isinstance(msg, dict) else None
        if role in ("user", "assistant"):
            n_turns += 1
        if not isinstance(content, list):
            if isinstance(content, str):
                total_chars += len(content)
            continue
        for blk in content:
            if not isinstance(blk, dict):
                continue
            t = blk.get("type")
            if t in ("text", "thinking"):
                total_chars += len(blk.get("text") or blk.get("thinking") or "")
            elif t == "tool_use":
                name = blk.get("name", "")
                inp = blk.get("input", {}) or {}
                args_str = json.dumps(inp, ensure_ascii=False)
                args_chars = len(args_str)
                total_chars += args_chars
                n_tool_calls += 1
                if name == "Shell":
                    cmd = inp.get("command", "")
                    fam = command_family(cmd)
                    first80 = cmd[:80]
                    if SF_CMD.search(cmd or ""):
                        n_sf += 1
                    if DEPLOY_CMD.search(cmd or ""):
                        n_deploy += 1
                    if SELF_TRUNC.search(cmd or ""):
                        n_trunc += 1
                else:
                    fam = "tool:" + name
                    # first-80 chars of most descriptive arg
                    first80 = args_str[:80]
                    # non-shell self-truncation: head_limit / offset+limit on reads
                    if name in ("Grep", "Read") and ("head_limit" in inp or "limit" in inp):
                        n_trunc += 1
                toolcall_rows.append([sid, name, fam, first80, args_chars, ""])
    session_rows.append([
        sid, "cursor", project, n_turns, n_tool_calls, total_chars,
        est_tokens(total_chars), n_sf, max(0, n_deploy - 1), n_trunc,
    ])


# ----------------------------------------------------------------------------
# Claude Code parsing
#   entries typed user/assistant; message.content list of blocks incl tool_use;
#   tool results carried on separate entries as top-level "toolUseResult";
#   assistant messages carry message.usage with cache splits.
# ----------------------------------------------------------------------------
def result_to_str(tur):
    if isinstance(tur, str):
        return tur
    if isinstance(tur, dict):
        parts = []
        for k in ("stdout", "stderr"):
            if tur.get(k):
                parts.append(str(tur[k]))
        return "\n".join(parts) if parts else json.dumps(tur, ensure_ascii=False)
    return json.dumps(tur, ensure_ascii=False)


def parse_claude(path, project, session_rows, toolcall_rows, claude_turn_rows):
    sid = os.path.splitext(os.path.basename(path))[0]
    n_turns = n_tool_calls = total_chars = n_sf = n_deploy = n_trunc = 0
    # map tool_use id -> pending row so we can attach the result chars later
    pending = {}
    last_usage = None  # dedupe consecutive identical usage (streaming re-logs)
    for obj in iter_jsonl(path):
        typ = obj.get("type")
        msg = obj.get("message", {}) if isinstance(obj.get("message"), dict) else {}
        # usage / cache splits per assistant turn (dedupe consecutive identical)
        usage = msg.get("usage") if isinstance(msg, dict) else None
        if usage:
            u = (usage.get("input_tokens", 0),
                 usage.get("cache_creation_input_tokens", 0),
                 usage.get("cache_read_input_tokens", 0),
                 usage.get("output_tokens", 0))
            if u != last_usage:
                claude_turn_rows.append([sid, project, obj.get("timestamp", ""), *u])
                last_usage = u
        if typ in ("user", "assistant"):
            n_turns += 1
        content = msg.get("content")
        result_id = None       # tool_use_id of a tool_result block in this entry
        block_result_len = 0   # chars of the tool_result block (fallback)
        if isinstance(content, str):
            total_chars += len(content)
        elif isinstance(content, list):
            for blk in content:
                if not isinstance(blk, dict):
                    continue
                bt = blk.get("type")
                if bt in ("text", "thinking"):
                    total_chars += len(blk.get("text") or blk.get("thinking") or "")
                elif bt == "tool_use":
                    name = blk.get("name", "")
                    inp = blk.get("input", {}) or {}
                    args_str = json.dumps(inp, ensure_ascii=False)
                    args_chars = len(args_str)
                    total_chars += args_chars
                    n_tool_calls += 1
                    if name == "Bash":
                        cmd = inp.get("command", "")
                        fam = command_family(cmd)
                        first80 = cmd[:80]
                        if SF_CMD.search(cmd or ""):
                            n_sf += 1
                        if DEPLOY_CMD.search(cmd or ""):
                            n_deploy += 1
                        if SELF_TRUNC.search(cmd or ""):
                            n_trunc += 1
                    else:
                        fam = "tool:" + name
                        first80 = args_str[:80]
                    row = [sid, name, fam, first80, args_chars, ""]
                    toolcall_rows.append(row)
                    tuid = blk.get("id")
                    if tuid:
                        pending[tuid] = row
                elif bt == "tool_result":
                    rc = blk.get("content")
                    if isinstance(rc, list):
                        s = "".join(x.get("text", "") for x in rc if isinstance(x, dict))
                    else:
                        s = rc if isinstance(rc, str) else json.dumps(rc, ensure_ascii=False)
                    result_id = blk.get("tool_use_id")
                    block_result_len = len(s)
        # Result char accounting: a result entry carries BOTH a top-level
        # toolUseResult and a tool_result block (they co-occur). Count once,
        # preferring the richer top-level toolUseResult payload.
        if "toolUseResult" in obj:
            s = result_to_str(obj["toolUseResult"])
            rlen = len(s)
        else:
            rlen = block_result_len
        if rlen:
            total_chars += rlen
            if result_id and result_id in pending:
                pending[result_id][5] = rlen
    session_rows.append([
        sid, "claude_code", project, n_turns, n_tool_calls, total_chars,
        est_tokens(total_chars), n_sf, max(0, n_deploy - 1), n_trunc,
    ])


# ----------------------------------------------------------------------------
# Task 1 driver
# ----------------------------------------------------------------------------
def mine_transcripts():
    session_rows, toolcall_rows, claude_turn_rows = [], [], []
    cur_root = os.path.join(TRANSCRIPTS, "cursor")
    if os.path.isdir(cur_root):
        for proj in sorted(os.listdir(cur_root)):
            pdir = os.path.join(cur_root, proj)
            if not os.path.isdir(pdir):
                continue
            for dp, _, fns in os.walk(pdir):
                for fn in fns:
                    if fn.endswith(".jsonl"):
                        parse_cursor(os.path.join(dp, fn), proj, session_rows, toolcall_rows)
    cc_root = os.path.join(TRANSCRIPTS, "claude-code")
    if os.path.isdir(cc_root):
        for proj in sorted(os.listdir(cc_root)):
            pdir = os.path.join(cc_root, proj)
            if not os.path.isdir(pdir):
                continue
            for dp, _, fns in os.walk(pdir):
                for fn in fns:
                    if fn.endswith(".jsonl"):
                        parse_claude(os.path.join(dp, fn), proj, session_rows,
                                     toolcall_rows, claude_turn_rows)

    with open(os.path.join(STATS, "sessions.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["session_id", "source", "project", "n_turns", "n_tool_calls",
                    "total_chars", "est_tokens", "n_sf_commands",
                    "n_deploy_retries", "n_self_truncations"])
        w.writerows(session_rows)

    with open(os.path.join(STATS, "tool_calls.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["session_id", "tool_name", "command_family",
                    "command_first_80_chars", "args_chars", "result_chars"])
        w.writerows(toolcall_rows)

    with open(os.path.join(STATS, "claude_turns.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["session_id", "project", "timestamp", "input_tokens",
                    "cache_creation_input_tokens", "cache_read_input_tokens",
                    "output_tokens"])
        w.writerows(claude_turn_rows)

    return session_rows, toolcall_rows, claude_turn_rows


# ----------------------------------------------------------------------------
# Task 3: compressibility prototype filters over the corpus
# ----------------------------------------------------------------------------
DEBUG_KEEP = re.compile(r'USER_DEBUG|EXCEPTION|FATAL|SOQL_EXECUTE|DML_|LIMIT_USAGE|CODE_UNIT_STARTED')


def family_for_corpus(fname, text):
    n = fname.lower()
    head = text[:300].lower()
    if n.endswith(".log") or "debug" in n:
        return "debug-log"
    if "deploy" in n or "validate" in n:
        return "sf-deploy/validate"
    if "apex-run-test" in n or ("apex" in n and "test" in n):
        return "sf-apex-test"
    if "git" in n:
        return "git"
    if "npm" in n:
        return "npm"
    if "query" in n or "describe" in n or n.endswith(".json") or '"result"' in head or "--json" in head:
        return "sf-json"
    if "retrieve" in n or "preview" in n:
        return "sf-retrieve-preview"
    if "org" in n or "metadata" in n or "list" in n:
        return "sf-org"
    return "other"


def filter_deploy(lines):
    kept, succeeded = [], 0
    for ln in lines:
        low = ln.lower()
        if re.search(r'\bsucceed(ed)?\b', low) and "error" not in low:
            succeeded += 1
            continue
        if re.search(r'error|fail|status|elapsed|components|deploy id|=== |warning', low) or re.match(r'\s*\d+\.', ln):
            kept.append(ln)
    if succeeded:
        kept.append(f"[collapsed] {succeeded} components Succeeded")
    return kept


def filter_apex(lines):
    kept = []
    for ln in lines:
        low = ln.lower()
        if re.search(r'fail|error|pass rate|tests ran|outcome|summary|=== ', low):
            kept.append(ln)
            continue
        m = re.search(r'(\d{1,3})\s*%', ln)
        if m and int(m.group(1)) < 75:
            kept.append(ln)
    return kept


def filter_debug(lines):
    return [ln for ln in lines if DEBUG_KEEP.search(ln)]


def _extract_json(text):
    """Corpus JSON files prepend a '$ command' line and maybe a CLI warning.
    Locate and parse the actual JSON object/array."""
    for i, ch in enumerate(text):
        if ch in "{[":
            try:
                return json.loads(text[i:])
            except Exception:
                continue
    raise ValueError("no json")


def filter_json(text):
    try:
        obj = _extract_json(text)
        minified = json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        minified = re.sub(r'\s+', ' ', text)
    # also estimate a CSV/tabular projection when it's a query result
    csv_tokens = None
    try:
        obj = _extract_json(text)
        records = None
        if isinstance(obj, dict):
            res = obj.get("result", obj)
            if isinstance(res, dict):
                records = res.get("records")
        if isinstance(records, list) and records and isinstance(records[0], dict):
            cols = [k for k in records[0].keys() if k != "attributes"]
            rows = [",".join(str(r.get(c, "")) for c in cols) for r in records]
            csv_text = ",".join(cols) + "\n" + "\n".join(rows)
            csv_tokens = est_tokens(len(csv_text))
    except Exception:
        pass
    return minified, csv_tokens


def filter_table(lines):
    """Collapse box-drawing table data rows to a count; keep summaries/headers.
    Used for retrieve-preview and metadata listings (thousands of padded rows)."""
    kept, data_rows = [], 0
    type_counts = {}
    for ln in lines:
        s = ln.strip()
        # box-drawing border lines -> drop
        if s and all(ch in "┌┐└┘├┤┬┴┼─│ " for ch in s):
            continue
        # data rows: start with │ and are not the header row (header has 'Full Name'/'Type')
        if s.startswith("│") and "Full Name" not in ln and "Created By" not in ln and "Type " not in ln:
            data_rows += 1
            cells = [c.strip() for c in s.strip("│").split("│")]
            if cells:
                type_counts[cells[0]] = type_counts.get(cells[0], 0) + 1
            continue
        if s:
            kept.append(ln)
    if data_rows:
        top = sorted(type_counts.items(), key=lambda x: -x[1])[:8]
        kept.append(f"[collapsed] {data_rows} table rows; top types: " +
                    ", ".join(f"{k}={v}" for k, v in top if k))
    return kept


def filter_generic_noise(lines):
    kept = []
    for ln in lines:
        low = ln.lower()
        if not ln.strip():
            continue
        if re.search(r'unchanged|up to date|deduped|added \d+ package|progress|\bresolving\b|\bfetching\b', low):
            continue
        kept.append(ln)
    return kept


def compressibility():
    families = {}

    def add(fam, raw_chars, filt_chars, extra_csv=None):
        d = families.setdefault(fam, {"files": 0, "raw_tokens": 0, "filtered_tokens": 0,
                                       "csv_tokens": 0, "has_csv": False})
        d["files"] += 1
        d["raw_tokens"] += est_tokens(raw_chars)
        d["filtered_tokens"] += est_tokens(filt_chars)
        if extra_csv is not None:
            d["csv_tokens"] += extra_csv
            d["has_csv"] = True

    scan_dirs = [os.path.join(CORPUS, "sf-outputs"), os.path.join(CORPUS, "debug-logs")]
    for d in scan_dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            fp = os.path.join(d, fn)
            if not os.path.isfile(fp):
                continue
            try:
                text = open(fp, "r", errors="replace").read()
            except Exception:
                continue
            if not text.strip():
                continue
            fam = family_for_corpus(fn, text)
            lines = text.splitlines()
            raw_chars = len(text)
            if fam == "sf-deploy/validate":
                filt = "\n".join(filter_deploy(lines))
                add(fam, raw_chars, len(filt))
            elif fam == "sf-apex-test":
                filt = "\n".join(filter_apex(lines))
                add(fam, raw_chars, len(filt))
            elif fam == "debug-log":
                filt = "\n".join(filter_debug(lines))
                add(fam, raw_chars, len(filt))
            elif fam == "sf-json":
                minified, csv_tokens = filter_json(text)
                add(fam, raw_chars, len(minified), extra_csv=csv_tokens)
            elif fam in ("git", "npm"):
                filt = "\n".join(filter_generic_noise(lines))
                add(fam, raw_chars, len(filt))
            elif fam in ("sf-retrieve-preview", "sf-org"):
                filt = "\n".join(filter_table(lines))
                add(fam, raw_chars, len(filt))
            else:  # other -> light noise filter
                filt = "\n".join(filter_generic_noise(lines))
                add(fam, raw_chars, len(filt))

    for fam, d in families.items():
        rt, ft = d["raw_tokens"], d["filtered_tokens"]
        d["ratio_kept"] = round(ft / rt, 3) if rt else None
        d["pct_reduction"] = round(100 * (1 - ft / rt), 1) if rt else None
        if not d["has_csv"]:
            d.pop("csv_tokens", None)
        d.pop("has_csv", None)
    return families


def build_summary(session_rows, toolcall_rows, claude_turn_rows, families):
    # aggregate tool-call families
    fam_counts = {}
    fam_args = {}
    fam_result = {}
    for r in toolcall_rows:
        fam = r[2]
        fam_counts[fam] = fam_counts.get(fam, 0) + 1
        fam_args[fam] = fam_args.get(fam, 0) + (r[4] or 0)
        if r[5] not in ("", None):
            fam_result[fam] = fam_result.get(fam, 0) + int(r[5])

    n_sessions = len(session_rows)
    total_est = sum(r[6] for r in session_rows)
    cursor_sessions = [r for r in session_rows if r[1] == "cursor"]
    claude_sessions = [r for r in session_rows if r[1] == "claude_code"]

    claude_usage = {
        "turns": len(claude_turn_rows),
        "input_tokens": sum(r[3] for r in claude_turn_rows),
        "cache_creation_input_tokens": sum(r[4] for r in claude_turn_rows),
        "cache_read_input_tokens": sum(r[5] for r in claude_turn_rows),
        "output_tokens": sum(r[6] for r in claude_turn_rows),
    }
    tot_in = (claude_usage["input_tokens"] + claude_usage["cache_creation_input_tokens"]
              + claude_usage["cache_read_input_tokens"])
    claude_usage["cache_hit_rate"] = (
        round(claude_usage["cache_read_input_tokens"] / tot_in, 3) if tot_in else None)

    summary = {
        "sessions": {
            "total": n_sessions,
            "cursor": len(cursor_sessions),
            "claude_code": len(claude_sessions),
            "total_est_tokens_visible": total_est,
            "total_tool_calls": sum(r[4] for r in session_rows),
            "total_sf_commands": sum(r[7] for r in session_rows),
            "total_deploy_retries": sum(r[8] for r in session_rows),
            "total_self_truncations": sum(r[9] for r in session_rows),
        },
        "tool_call_families": {
            fam: {
                "calls": fam_counts[fam],
                "args_est_tokens": est_tokens(fam_args.get(fam, 0)),
                "result_est_tokens_claude": est_tokens(fam_result.get(fam, 0)) if fam in fam_result else None,
            } for fam in sorted(fam_counts, key=lambda k: -fam_counts[k])
        },
        "claude_code_usage": claude_usage,
        "compressibility": families,
    }
    with open(os.path.join(STATS, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    return summary


def build_corpus_index():
    """Write corpus/index.csv: file, command, chars, lines, est_tokens."""
    rows = []
    for sub in ("sf-outputs", "debug-logs", "metadata-samples"):
        d = os.path.join(CORPUS, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            fp = os.path.join(d, fn)
            if not os.path.isfile(fp):
                continue
            try:
                text = open(fp, "r", errors="replace").read()
            except Exception:
                continue
            first = text.splitlines()[0] if text else ""
            cmd = first[2:].strip() if first.startswith("$ ") else ""
            rows.append([os.path.join(sub, fn), cmd, len(text),
                         text.count("\n"), est_tokens(len(text))])
    with open(os.path.join(CORPUS, "index.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["file", "command", "chars", "lines", "est_tokens"])
        w.writerows(rows)
    return rows


if __name__ == "__main__":
    sessions, toolcalls, claude_turns = mine_transcripts()
    corpus_index = build_corpus_index()
    fams = compressibility()
    summ = build_summary(sessions, toolcalls, claude_turns, fams)
    print(f"sessions: {len(sessions)}  tool_calls: {len(toolcalls)}  claude_turns: {len(claude_turns)}")
    print(f"corpus families analyzed: {list(fams.keys())}")
    print("summary.json written to", os.path.join(STATS, "summary.json"))
