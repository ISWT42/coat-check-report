#!/usr/bin/env python3
"""Build the living report from data.

    python build.py                   build + all checks, write dist/
    python build.py --pdf             also print dist/report.pdf (needs a local PDF tool)
    python build.py --verify-sources  also check every quoted line against the local copy
    python build.py --check-only      checks only, write nothing
    python build.py --release         copy dist/ to releases/vX.Y.Z/ (refuses placeholders)

Standard library only. The source of truth is findings/*.json, changelog/*.json,
next.json and prose/*.md. Prose never types a number: numbers come from
{{placeholders}} that resolve to finding files, and a check fails the build if a
raw number or number word is left in prose.
"""
import argparse, datetime, hashlib, html, json, os, pathlib, re, shutil, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent
STATUSES = ["shown", "not shown", "against", "exploratory"]
LIFECYCLES = ["active", "superseded", "retracted"]
VERDICTS = ["shown", "not shown", "exploratory"]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
NUM_WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen "
    "sixteen seventeen eighteen nineteen twenty".split())}
# number words that count as hand-typed numbers in prose ("one" is left out: it is mostly a pronoun)
WORD_CHECK = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
              "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred "
              "thousand million zero twice thrice").split()


class BuildError(Exception):
    pass


# ----------------------------------------------------------------- loading
def read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_text(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read().replace("\r\n", "\n")


def semver_key(v):
    return tuple(int(x) for x in v.split("."))


def load_project(root=ROOT):
    root = pathlib.Path(root)
    P = {"root": root}
    P["config"] = read_json(root / "report.config.json")
    P["names"] = read_json(root / "names.json")["terms"]
    P["registry"] = read_json(root / "registry.json")["issued"]
    P["findings"] = []
    P["finding_files"] = {}
    for p in sorted((root / "findings").glob("F*.json")):
        f = read_json(p)
        P["findings"].append(f)
        P["finding_files"][f.get("id")] = p.name
    P["findings"].sort(key=lambda f: f.get("id", ""))
    P["by_id"] = {f["id"]: f for f in P["findings"] if "id" in f}
    P["changelog"] = [read_json(p) for p in sorted((root / "changelog").glob("*.json"))]
    P["changelog"].sort(key=lambda c: semver_key(c["version"]) if SEMVER.match(c.get("version", "")) else (0, 0, 0))
    nx = root / "next.json"
    P["next"] = read_json(nx)["questions"] if nx.exists() else []
    P["prose"] = {p.stem: read_text(p) for p in sorted((root / "prose").glob("*.md"))}
    loc = root / "local.config.json"
    P["local"] = read_json(loc) if loc.exists() else {}
    return P


# ----------------------------------------------------------------- numbers
NUM_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:e-?\d+)?(?![\w])")
DATE_PATTERNS = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}:\d{2}Z?)?"),
    re.compile(r"\b\d{1,2} (?:%s)(?: \d{4})?\b" % "|".join(MONTHS)),
    re.compile(r"\b(?:%s) \d{4}\b" % "|".join(MONTHS)),
    re.compile(r"\b\d{4}/\d{2}/\d{2}\b"),
    re.compile(r"\b\d{2}:\d{2}:\d{2}Z?\b"),
]
HEX_RE = re.compile(r"\b[0-9a-f]{12,}\b", re.I)
URL_RE = re.compile(r"https?://[^\s)>\]]+")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s)>\]]+")
SEMVER_RE = re.compile(r"\b\d+\.\d+\.\d+\b")
ID_RE = re.compile(r"\b[FQ]\d{3}\b")


def norm_num(tok):
    return tok.replace(",", "")


def tokens_of(text):
    """Numeric tokens in a quote (digits glued to letters count too), plus number words."""
    t = set(norm_num(x) for x in re.findall(r"\d[\d,]*(?:\.\d+)?(?:e-?\d+)?", text))
    for w, d in NUM_WORDS.items():
        if re.search(r"\b%s\b" % w, text, re.I):
            t.add(d)
    return t


def mask(text, P, extra_literals=()):
    """Remove everything that is not a typed claim number: code, URLs, dates, ids, names."""
    s = text
    s = re.sub(r"```.*?```", " ", s, flags=re.S)
    s = re.sub(r"^#{1,6} .*$", " ", s, flags=re.M)
    s = re.sub(r"^\s*\d+\. ", " ", s, flags=re.M)
    s = re.sub(r"`[^`\n]*`", " ", s)
    s = re.sub(r"\{\{.*?\}\}", " ", s)
    s = re.sub(r"\]\([^)]*\)", "] ", s)
    s = URL_RE.sub(" ", s)
    s = DOI_RE.sub(" ", s)
    for pat in DATE_PATTERNS:
        s = pat.sub(" ", s)
    s = SEMVER_RE.sub(" ", s)
    s = HEX_RE.sub(" ", s)
    s = ID_RE.sub(" ", s)
    lits = [x["text"] for x in P["config"].get("allowed_literals", [])] + list(extra_literals)
    for term in sorted(P["names"] + lits, key=len, reverse=True):
        s = s.replace(term, " ")
    return s


def raw_numbers(text, P):
    s = mask(text, P)
    found = [m.group(0) for m in NUM_RE.finditer(s)]
    words = [w for w in WORD_CHECK if re.search(r"\b%s\b" % w, s, re.I)]
    return found, words


# ----------------------------------------------------------------- data access
def count_text(c, part=None):
    if part == "n":
        return str(c["n"])
    if part == "d":
        return str(c["d"])
    return "%s of %s" % (c["n"], c["d"]) if c.get("d") is not None else str(c["n"])


def meta_values(P):
    fs = P["findings"]
    m = {"version": P["config"]["version"], "date": P["config"]["date"], "n_findings": str(len(fs))}
    parts = []
    for st in STATUSES:
        k = sum(1 for f in fs if f["status"] == st)
        m["n_" + st.replace(" ", "_")] = str(k)
        if k:
            parts.append("%d %s" % (k, st))
    m["status_counts"] = ", ".join(parts) if parts else "none"
    return m


def resolve(text, P, where, errs):
    meta = meta_values(P)

    def rep(m):
        ref = m.group(1).strip()
        parts = ref.split(".")
        try:
            if parts[0] == "meta":
                return meta[parts[1]]
            f = P["by_id"][parts[0]]
            if parts[1] == "c":
                c = next(c for c in f["counts"] if c["key"] == parts[2])
                return count_text(c, parts[3] if len(parts) > 3 else None)
            if parts[1] == "t":
                t = next(t for t in f["tests"] if t["key"] == parts[2])
                return str(t[parts[3]])
        except (KeyError, StopIteration, IndexError):
            pass
        errs.append("%s: placeholder {{%s}} does not resolve" % (where, ref))
        return "??"
    return re.sub(r"\{\{(.*?)\}\}", rep, text)


def ref_cell(P, f, cell):
    """'@key' or '@F003.key' -> the count dict."""
    key = cell[1:]
    fid = f["id"]
    if "." in key:
        fid, key = key.split(".", 1)
    g = P["by_id"].get(fid)
    if not g:
        return None
    return next((c for c in g["counts"] if c["key"] == key), None)


def finding_numbers(P):
    """Every number that appears as data in a finding file (plus derived report numbers)."""
    nums = set()
    for f in P["findings"]:
        for c in f.get("counts", []):
            for k in ("n", "d"):
                if c.get(k) is not None:
                    nums.add(norm_num(str(c[k])))
        for t in f.get("tests", []):
            for k in ("a", "b", "p"):
                nums |= tokens_of(str(t[k]))
        for tb in f.get("tables", []):
            if tb.get("of") is not None:
                nums.add(str(tb["of"]))
            for r in tb["rows"]:
                for cell in r["cells"]:
                    if not str(cell).startswith("@"):
                        nums |= tokens_of(str(cell))
        for s in f.get("seal", []):
            for b in s.get("bitcoin_blocks", []):
                nums.add(str(b))
    nums |= set(meta_values(P)[k] for k in meta_values(P) if k.startswith("n_"))
    return nums


# ----------------------------------------------------------------- validation
def prose_fields(f):
    out = []
    for k in ("title", "question", "status_note", "summary_line", "headline", "plain_meaning", "setup", "seal_note"):
        if f.get(k):
            out.append((k, f[k]))
    for i, l in enumerate(f.get("limits", [])):
        out.append(("limits[%d]" % i, l))
    for i, r in enumerate(f.get("record_corrections", [])):
        out.append(("record_corrections[%d]" % i, r["text"]))
    for tb in f.get("tables", []):
        out.append(("table %s caption" % tb["key"], tb["caption"]))
    return out


def validate(P):
    errs = []
    cfg = P["config"]
    fs = P["findings"]
    if not SEMVER.match(cfg.get("version", "")):
        errs.append("config version is not semantic: %r" % cfg.get("version"))
    # ids and registry
    seen = set()
    for f in fs:
        fid = f.get("id", "")
        if not re.match(r"^F\d{3}$", fid):
            errs.append("bad finding id %r" % fid)
        if fid in seen:
            errs.append("duplicate finding id %s" % fid)
        seen.add(fid)
        fn = P["finding_files"].get(fid, "")
        if not fn.startswith(fid + "-"):
            errs.append("%s: file name %s does not start with the id" % (fid, fn))
    reg = P["registry"]
    if len(set(reg)) != len(reg):
        errs.append("registry has a repeated id")
    for rid in reg:
        if rid not in seen:
            errs.append("registry id %s has no finding file: cards are never deleted" % rid)
    for fid in seen:
        if fid not in reg:
            errs.append("finding %s is not in registry.json: add it (append only)" % fid)
    # changelog
    versions = [c["version"] for c in P["changelog"]]
    for v in versions:
        if not SEMVER.match(v):
            errs.append("changelog version %r is not semantic" % v)
    if len(set(versions)) != len(versions):
        errs.append("changelog has a repeated version")
    if versions and versions[-1] != cfg["version"]:
        errs.append("config version %s is not the latest changelog version %s" % (cfg["version"], versions[-1]))
    clog = {c["version"]: c for c in P["changelog"]}
    for c in P["changelog"]:
        for k in ("added", "retracted", "superseded"):
            for fid in c.get(k, []):
                if fid not in P["by_id"]:
                    errs.append("changelog %s lists unknown finding %s in %s" % (c["version"], fid, k))
    # per-finding checks
    required = ["id", "slug", "title", "question", "status", "date_added", "version_first_included", "lifecycle",
                "headline", "summary_line", "plain_meaning", "limits", "counts", "tables", "tests", "seal", "links"]
    for f in fs:
        fid = f.get("id", "?")
        for k in required:
            if k not in f:
                errs.append("%s: missing field %s" % (fid, k))
        if f.get("status") not in STATUSES:
            errs.append("%s: status %r not in %s" % (fid, f.get("status"), STATUSES))
        if f.get("lifecycle") not in LIFECYCLES:
            errs.append("%s: lifecycle %r not in %s" % (fid, f.get("lifecycle"), LIFECYCLES))
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(f.get("date_added", ""))):
            errs.append("%s: date_added must be YYYY-MM-DD" % fid)
        v = f.get("version_first_included", "")
        if v not in clog:
            errs.append("%s: version_first_included %s has no changelog entry" % (fid, v))
        elif fid not in clog[v].get("added", []):
            errs.append("%s: changelog %s does not list it under added" % (fid, v))
        if f.get("lifecycle") == "superseded":
            if f.get("superseded_by") not in P["by_id"]:
                errs.append("%s: superseded_by must name an existing finding" % fid)
            sv = f.get("superseded_in")
            if sv not in clog or fid not in clog[sv].get("superseded", []):
                errs.append("%s: superseded_in version must list it under superseded in the changelog" % fid)
        if f.get("lifecycle") == "retracted":
            r = f.get("retraction") or {}
            if not (r.get("version") and r.get("date") and r.get("reason")):
                errs.append("%s: retraction needs version, date and reason" % fid)
            elif r["version"] not in clog or fid not in clog[r["version"]].get("retracted", []):
                errs.append("%s: retraction version must list it under retracted in the changelog" % fid)
        # counts
        keys = set()
        for c in f.get("counts", []):
            k = c.get("key")
            if k in keys:
                errs.append("%s: duplicate count key %s" % (fid, k))
            keys.add(k)
            where = "%s.c.%s" % (fid, k)
            q = c.get("quote", "")
            if not q or not c.get("source", {}).get("path"):
                errs.append("%s: needs a source path and a quoted line" % where)
                continue
            qt = tokens_of(q)
            if norm_num(str(c["n"])) not in qt:
                errs.append("%s: n=%s is not in the quoted line" % (where, c["n"]))
            if c.get("d") is not None and norm_num(str(c["d"])) not in qt and not c.get("d_basis"):
                errs.append("%s: denominator %s is not in the quoted line and no d_basis explains it" % (where, c["d"]))
        # tests
        tkeys = set()
        for t in f.get("tests", []):
            where = "%s.t.%s" % (fid, t.get("key"))
            if t["key"] in tkeys:
                errs.append("%s: duplicate test key" % where)
            tkeys.add(t["key"])
            if t.get("verdict") not in VERDICTS:
                errs.append("%s: verdict %r not in %s" % (where, t.get("verdict"), VERDICTS))
            qt = tokens_of(t.get("quote", ""))
            for k in ("a", "b", "p"):
                for tok in tokens_of(str(t[k])):
                    if tok not in qt:
                        errs.append("%s: %s=%s is not in the quoted line" % (where, k, t[k]))
        # tables
        for tb in f.get("tables", []):
            for r in tb["rows"]:
                if len(r["cells"]) != len(tb["columns"]):
                    errs.append("%s: table %s row %r has %d cells for %d columns" % (fid, tb["key"], r["label"], len(r["cells"]), len(tb["columns"])))
                for cell in r["cells"]:
                    cell = str(cell)
                    if cell.startswith("@"):
                        if ref_cell(P, f, cell) is None:
                            errs.append("%s: table %s cell %s does not name a count" % (fid, tb["key"], cell))
                    else:
                        if not r.get("quote"):
                            errs.append("%s: table %s row %r has literal cells and no quote" % (fid, tb["key"], r["label"]))
                        elif norm_num(cell) not in tokens_of(r["quote"]):
                            errs.append("%s: table %s cell %s is not in the row's quoted line" % (fid, tb["key"], cell))
        # seals
        for s in f.get("seal", []):
            if not re.match(r"^[0-9a-f]{64}$", s.get("sha256", "")):
                errs.append("%s: seal %s has no valid sha256" % (fid, s.get("list_file")))
    # next questions
    for q in P["next"]:
        if not re.match(r"^Q\d{3}$", q.get("id", "")):
            errs.append("bad question id %r" % q.get("id"))
        for r in q.get("related", []):
            if r not in P["by_id"]:
                errs.append("%s relates to unknown finding %s" % (q["id"], r))
    # placeholders resolve and prose has no raw numbers
    texts = []
    for f in fs:
        for k, t in prose_fields(f):
            texts.append(("%s.%s" % (f["id"], k), t))
    for name, t in P["prose"].items():
        texts.append(("prose/%s.md" % name, t))
    for q in P["next"]:
        texts.append((q["id"], q["text"]))
    for c in P["changelog"]:
        texts.append(("changelog %s summary" % c["version"], c.get("summary", "")))
        for ch in c.get("changed", []):
            texts.append(("changelog %s changed" % c["version"], ch.get("what", "")))
        for ch in c.get("retracted_notes", []):
            texts.append(("changelog %s retracted" % c["version"], ch))
    for where, t in texts:
        resolve(t, P, where, errs)
        found, words = raw_numbers(t, P)
        for n in found:
            errs.append("%s: raw number %r typed in prose. Use a {{placeholder}} that resolves to a finding file." % (where, n))
        for w in words:
            errs.append("%s: number word %r typed in prose. Use a {{placeholder}}, or allow the phrase in report.config.json with a reason." % (where, w))
    return errs


# ----------------------------------------------------------------- rendering (markdown)
def seal_summary(f):
    s = f.get("seal", [])
    if not s:
        return "No seal files of its own."
    times = sorted(x["freetsa_utc"] for x in s if x.get("freetsa_utc"))
    blocks = sorted(set(b for x in s for b in x.get("bitcoin_blocks", [])))
    out = []
    if times:
        d0, d1 = times[0][:10], times[-1][:10]
        out.append("FreeTSA %s" % (d0 if d0 == d1 else "%s to %s" % (d0, d1)))
    out.append(("Bitcoin %s" % (str(blocks[0]) if len(blocks) == 1 else "%s to %s" % (blocks[0], blocks[-1]))) if blocks else ("FreeTSA only, no Bitcoin proof" if all(x.get("ots") == "none" for x in s) else "Bitcoin pending"))
    return "; ".join(out) + " (Appendix C)."


def render_table(P, f, tb):
    cap = tb["caption"] + (" (of %s)" % tb["of"] if tb.get("of") is not None else "")
    lines = ["**%s**" % cap, "", "| | " + " | ".join(tb["columns"]) + " |", "|---|" + "---|" * len(tb["columns"])]
    for r in tb["rows"]:
        cells = []
        for cell in r["cells"]:
            cell = str(cell)
            if cell.startswith("@"):
                cells.append(str(ref_cell(P, f, cell)["n"]))
            else:
                cells.append(cell)
        lines.append("| %s | %s |" % (r["label"], " | ".join(cells)))
    return "\n".join(lines)


def render_card(P, f):
    errs = []
    R = lambda t: resolve(t, P, f["id"], errs)
    L = []
    L.append("### %s. %s" % (f["id"], f["title"]))
    L.append("")
    L.append(("**Status: %s** (since %s). %s" % (f["status"], f["version_first_included"], R(f.get("status_note", "")))).rstrip())
    L.append("")
    if f["lifecycle"] == "superseded":
        L.append("> **Superseded by %s** in version %s. This card stays as written." % (f["superseded_by"], f.get("superseded_in", "")))
        L.append("")
    if f["lifecycle"] == "retracted":
        r = f["retraction"]
        L.append("> **RETRACTED in version %s on %s.** %s This card stays visible as written." % (r["version"], r["date"], r["reason"]))
        L.append("")
    L.append("*Question.* " + R(f["question"]))
    L.append("")
    L.append("**Result.** " + R(f["headline"]))
    for tb in f.get("tables", []):
        L.append("")
        L.append(render_table(P, f, tb))
    if f.get("tests"):
        L.append("")
        for t in f["tests"]:
            pv = ("p %s" % t["p"]) if t["p"][:1] in "<>" else ("p = %s" % t["p"])
            L.append("- %s: %s against %s, %s%s." % (t["name"], t["a"], t["b"], pv, "" if t["verdict"] == "shown" else " (%s)" % t["verdict"]))
    L.append("")
    L.append("*Meaning.* " + R(f["plain_meaning"]))
    if f.get("setup"):
        L.append("")
        L.append("*Setup.* " + R(f["setup"]))
    for r in f.get("record_corrections", []):
        L.append("")
        L.append("*Record correction.* %s" % R(r["text"]))
    L.append("")
    L.append("*Limits.* " + " ".join(R(l) for l in f["limits"]))
    L.append("")
    L.append("*Seal.* " + seal_summary(f))
    if errs:
        raise BuildError("; ".join(errs))
    return "\n".join(L)


def render_sections(P):
    """Return an ordered dict-like list of (key, md)."""
    cfg = P["config"]
    errs = []
    R = lambda t, w: resolve(t, P, w, errs)
    S = []
    # 1 summary (regenerated)
    L = ["## 1. Summary", "", R(P["prose"]["summary"].strip(), "summary"), ""]
    for f in P["findings"]:
        flag = {"active": "", "superseded": " (superseded)", "retracted": " (RETRACTED)"}[f["lifecycle"]]
        L.append("- **%s** [%s]%s %s" % (f["id"], f["status"], flag, R(f["summary_line"], f["id"])))
    S.append(("summary", "\n".join(L)))
    S.append(("method", "## 2. Method\n\n" + R(P["prose"]["method"].strip(), "method")))
    cards = [render_card(P, f) for f in P["findings"]]
    S.append(("findings", "## 3. Findings\n\n" + "\n\n".join(cards)))
    S.append(("limits", "## 4. Limits and threats to validity\n\n" + R(P["prose"]["limits"].strip(), "limits")))
    L = ["## 5. What's next", ""]
    for q in P["next"]:
        L.append("- **%s** [%s] %s" % (q["id"], q["status"], R(q["text"], q["id"])))
    S.append(("next", "\n".join(L)))
    S.append(("ack", "**Acknowledgement.** " + cfg["acknowledgement"]))
    # 6 changelog
    L = ["## 6. Changelog", ""]
    for c in reversed(P["changelog"]):
        L.append("### Version %s (%s)" % (c["version"], c["date"]))
        L.append("")
        L.append(R(c.get("summary", ""), "changelog"))
        L.append("")
        L.append("- Findings added: %s" % (", ".join(c.get("added", [])) or "none"))
        ch = c.get("changed", [])
        L.append("- Changed: %s" % ("; ".join("%s: %s" % (x["id"], R(x["what"], "changelog")) for x in ch) if ch else "none"))
        sp = c.get("superseded", [])
        if sp:
            L.append("- Superseded (card kept): %s" % ", ".join(sp))
        rt = c.get("retracted", [])
        L.append("- Retracted (card kept, marked): %s" % (", ".join(rt) if rt else "none"))
        L.append("")
    S.append(("changelog", "\n".join(L).rstrip()))
    # appendices
    S.append(("appA", "## Appendix A. How to verify\n\n" + appendix_a(P)))
    S.append(("appB", "## Appendix B. Evidence lines\n\n" + appendix_b(P)))
    S.append(("appC", "## Appendix C. Seals\n\n" + appendix_c(P)))
    if errs:
        raise BuildError("; ".join(errs))
    return S


def appendix_a(P):
    cfg = P["config"]
    t = P["prose"]["appendix"].strip()
    links = "\n".join("- [%s](%s)" % (l["label"], l["url"]) for l in cfg["public_links"])
    return t + "\n\n### A.6 Public links\n\n" + links


def evidence_entries(P):
    out = []
    for f in P["findings"]:
        entries = {}
        order = []

        def add(src, quote, what):
            k = (src["root"], src["path"], quote)
            if k not in entries:
                entries[k] = (src, quote, [])
                order.append(k)
            entries[k][2].append(what)
        for c in f["counts"]:
            add(c["source"], c["quote"], "%s (%s)" % (c["key"], count_text(c)))
        for tb in f["tables"]:
            for r in tb["rows"]:
                if r.get("quote"):
                    add(r["source"], r["quote"], "table %s, row %s" % (tb["key"], r["label"]))
        for t in f["tests"]:
            add(t["source"], t["quote"], "test %s" % t["key"])
        if f.get("setup_quote"):
            add(f["setup_quote"]["source"], f["setup_quote"]["quote"], "setup sentence")
        out.append((f, [entries[k] for k in order]))
    return out


def appendix_b(P):
    L = ["Each count, table row and test below rests on the quoted line from the named file. Paths are relative to the author's working folder; the public copy is named where known.", ""]
    for f, ents in evidence_entries(P):
        L.append("### Evidence for %s" % f["id"])
        L.append("")
        if f.get("links"):
            L.append("Links: " + " · ".join("[%s](%s)" % (l["label"], l["url"]) for l in f["links"]))
            L.append("")
        for i, (src, quote, whats) in enumerate(ents, 1):
            pub = (" Public copy: %s." % src["public"]) if src.get("public") else ""
            L.append("**%s.%d** `%s`.%s" % (f["id"], i, src["path"], pub))
            L.append("")
            L.append("```")
            L.append(quote)
            L.append("```")
            L.append("")
            L.append("Supports: " + "; ".join(whats) + ".")
            L.append("")
    return "\n".join(L).rstrip()


def appendix_c(P):
    L = ["Seal lists as read from the local files by `tools/seal_info.py` (no network). FreeTSA times come from the time-stamp token; Bitcoin blocks are the heights written in the proof file, not verified here. A proof with none is still waiting for a block. Verify with the steps in Appendix A.", ""]
    for f in P["findings"]:
        if not f.get("seal"):
            continue
        L.append("### Seals for %s" % f["id"])
        L.append("")
        L.append("| Role | List file | SHA-256 | FreeTSA (UTC) | Bitcoin blocks |")
        L.append("|---|---|---|---|---|")
        for s in f["seal"]:
            L.append("| %s | `%s` | `%s` | %s | %s |" % (s["role"], s["list_file"], s["sha256"], (s["freetsa_utc"] or "none").replace("T", " "),
                                                      ", ".join(str(b) for b in s.get("bitcoin_blocks", [])) or ("none (FreeTSA only)" if s.get("ots") == "none" else "pending")))
        L.append("")
        if f.get("seal_note"):
            L.append(resolve(f["seal_note"], P, f["id"], []))
            L.append("")
    return "\n".join(L).rstrip()


def title_block_md(P):
    cfg = P["config"]
    d = datetime.date.fromisoformat(cfg["date"])
    return "\n".join([
        "# " + cfg["title"], "",
        "%s · version %s · %d %s %d" % (cfg["author_line"], cfg["version"], d.day, MONTHS[d.month - 1], d.year), "",
        "Contact: %s. DOI of this version: %s. Concept DOI (always the latest): %s." % (cfg["contact"], cfg["citation"]["doi"], cfg["citation"]["concept_doi"]), "",
        "Licence: " + cfg["license"], ""])


def compose_md(P, sections=None):
    S = sections or render_sections(P)
    fm = P["config"]
    front = "---\ntitle: \"%s\"\nauthor: \"%s\"\nversion: \"%s\"\ndate: \"%s\"\ndoi: \"%s\"\n---\n\n" % (
        fm["title"].replace('"', '\\"'), fm["author"], fm["version"], fm["date"], fm["citation"]["doi"])
    return front + title_block_md(P) + "\n" + "\n\n".join(md for _, md in S) + "\n"


# ----------------------------------------------------------------- checks on output
def count_words(md):
    s = re.sub(r"```.*?```", " ", md, flags=re.S)
    s = re.sub(r"^\|?[\s|:-]+\|?$", " ", s, flags=re.M)
    s = re.sub(r"\{#[^}]*\}", " ", s)
    s = re.sub(r"\]\([^)]*\)", "] ", s)
    return len([t for t in s.split() if re.search(r"[A-Za-z0-9]", t)])


def counted_scope(S):
    keep = ("summary", "method", "findings", "limits", "next", "ack")
    return "\n\n".join(md for k, md in S if k in keep)


def paper_sections(P):
    """Same sections, with cards filtered by paper:true."""
    Q = dict(P)
    Q["findings"] = [f for f in P["findings"] if f.get("paper", True)]
    return render_sections(Q)


def check_rendered_numbers(P, S):
    """Every number in the rendered sections 1-5 must exist in a finding file."""
    allowed = finding_numbers(P)
    bad = []
    for k, md in S:
        if k not in ("summary", "method", "findings", "limits", "next", "ack"):
            continue
        for ln in md.split("\n"):
            if ln.startswith("#"):
                continue
            found, words = raw_numbers(ln, P)
            for n in found:
                if norm_num(n) not in allowed:
                    bad.append("%s: %r in %r" % (k, n, ln[:80]))
    return bad


def html_checks(doc):
    need = ["citation_title", "citation_author", "citation_publication_date", "citation_doi", "citation_pdf_url"]
    miss = [n for n in need if 'name="%s"' % n not in doc]
    if 'content="Joshua Bauer"' not in doc:
        miss.append("author content")
    ids = set(re.findall(r'[\s<]id="([^"]+)"', doc))
    for a in sorted(set(re.findall(r'href="#([^"]+)"', doc))):
        if a not in ids:
            miss.append("anchor #%s has no target" % a)
    if "??" in doc:
        miss.append("unresolved placeholder (??) in the page")
    return miss


def public_gaps(P):
    """Evidence sources that name no public copy. A release needs none."""
    gaps = []
    for f, ents in evidence_entries(P):
        for src, quote, whats in ents:
            if not src.get("public"):
                gaps.append("%s: %s" % (f["id"], src["path"]))
    return sorted(set(gaps))


def verify_sources(P):
    """Check each quote against the local copy of its source file."""
    roots = P["local"].get("source_roots")
    if not roots:
        return None, ["local.config.json has no source_roots"]
    bad, n = [], 0
    cache = {}
    for f, ents in evidence_entries(P):
        for src, quote, whats in ents:
            p = pathlib.Path(roots[src["root"]]) / src["path"]
            if str(p) not in cache:
                cache[str(p)] = read_text(p) if p.exists() else None
            n += 1
            if cache[str(p)] is None:
                bad.append("%s: file not found: %s" % (f["id"], src["path"]))
            elif quote not in cache[str(p)]:
                bad.append("%s: quote not found in %s: %r" % (f["id"], src["path"], quote[:70]))
    # seal hashes
    for f in P["findings"]:
        for s in f.get("seal", []):
            p = pathlib.Path(roots["workbench"]) / s["path"]
            n += 1
            if not p.exists():
                bad.append("%s: seal file not found: %s" % (f["id"], s["path"]))
            elif hashlib.sha256(p.read_bytes()).hexdigest() != s["sha256"]:
                bad.append("%s: seal list changed since it was recorded: %s" % (f["id"], s["path"]))
    return n, bad


# ----------------------------------------------------------------- markdown -> html
def esc(s):
    return html.escape(s, quote=False)


def inline(s):
    codes = []

    def keep(m):
        codes.append("<code>%s</code>" % esc(m.group(1)))
        return "\u0000%d\u0000" % (len(codes) - 1)
    s = re.sub(r"`([^`\n]+)`", keep, s)
    s = esc(s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", lambda m: '<a href="%s">%s</a>' % (m.group(2).replace('"', "%22"), m.group(1)), s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])", r"<em>\1</em>", s)
    # bare urls not already inside an anchor
    s = re.sub(r'(?<!["=>])(https?://[^\s<)]+)', lambda m: '<a href="%s">%s</a>' % (m.group(1), m.group(1)), s)
    # finding / question ids -> anchors (outside tags and anchors)
    parts = re.split(r"(<[^>]+>)", s)
    depth = 0
    for i, p in enumerate(parts):
        if p.startswith("<"):
            if re.match(r"<(a|code)\b", p):
                depth += 1
            elif re.match(r"</(a|code)>", p):
                depth -= 1
        elif depth == 0:
            parts[i] = re.sub(r"\b(F\d{3})\b", r'<a href="#\1">\1</a>', p)
    s = "".join(parts)
    return re.sub(r"\u0000(\d+)\u0000", lambda m: codes[int(m.group(1))], s)


def md_to_html(md):
    lines = md.split("\n")
    out = []
    i = 0
    in_card = False
    para = []

    def flush():
        if para:
            text = " ".join(para)
            m = re.match(r"^\*\*Status: ([^*]+)\*\*(.*)$", text)
            if m:
                cls = "s-" + m.group(1).strip().replace(" ", "-")
                out.append('<p class="status"><span class="badge %s">%s</span>%s</p>' % (cls, esc(m.group(1).strip()), inline(m.group(2))))
            else:
                out.append("<p>%s</p>" % inline(text))
            para.clear()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            flush()
            j = i + 1
            buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j])
                j += 1
            out.append("<pre><code>%s</code></pre>" % esc("\n".join(buf)))
            i = j + 1
            continue
        m = re.match(r"^(#{1,4}) (.*?)(?: \{#([\w-]+)\})?$", ln)
        if m:
            flush()
            lvl = len(m.group(1))
            if in_card and lvl <= 3:
                out.append("</section>")
                in_card = False
            idv = m.group(3) or re.sub(r"[^a-z0-9]+", "-", m.group(2).lower()).strip("-")
            fm = re.match(r"^(F\d{3})\. ", m.group(2))
            if lvl == 3 and fm:
                out.append('<section class="card" id="%s">' % fm.group(1))
                in_card = True
                out.append("<h3>%s</h3>" % inline(m.group(2)))
            else:
                out.append('<h%d id="%s">%s</h%d>' % (lvl, idv, inline(m.group(2)), lvl))
            i += 1
            continue
        if ln.strip() == "":
            flush()
            i += 1
            continue
        if ln.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            head = cells(rows[0])
            body = [cells(r) for r in rows[2:]]
            t = ['<div class="tw"><table><thead><tr>%s</tr></thead><tbody>' % "".join("<th>%s</th>" % inline(c) for c in head)]
            for r in body:
                t.append("<tr>%s</tr>" % "".join(("<th scope=\"row\">%s</th>" if k == 0 else "<td>%s</td>") % inline(c) for k, c in enumerate(r)))
            t.append("</tbody></table></div>")
            out.append("".join(t))
            continue
        if re.match(r"^(\s*)([-*]|\d+\.) ", ln):
            flush()
            ordered = bool(re.match(r"^\s*\d+\. ", ln))
            items = []
            while i < len(lines) and re.match(r"^(\s*)([-*]|\d+\.) ", lines[i]):
                items.append(re.sub(r"^\s*([-*]|\d+\.) ", "", lines[i]))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x) for x in items), tag))
            continue
        if ln.startswith("> "):
            flush()
            buf = []
            while i < len(lines) and lines[i].startswith("> "):
                buf.append(lines[i][2:])
                i += 1
            cls = "retracted" if "RETRACTED" in " ".join(buf) else "superseded"
            out.append('<blockquote class="%s">%s</blockquote>' % (cls, inline(" ".join(buf))))
            continue
        para.append(ln.strip())
        i += 1
    flush()
    if in_card:
        out.append("</section>")
    return "\n".join(out)


CSS = """
:root{color-scheme:light dark;--bg:#f3f5f9;--panel:#fff;--soft:#edf0f6;--ink:#192338;--muted:#526078;--line:#d5dce7;--accent:#6238d4;--accent-soft:#eee8ff;--green:#176443;--green-soft:#e5f4eb;--red:#ae2941;--red-soft:#ffeaf0;--amber:#765009;--amber-soft:#fff2d5;--shadow:0 8px 28px rgb(21 33 55 / 5%)}
@media (prefers-color-scheme:dark){:root{--bg:#11151e;--panel:#1b2230;--soft:#252e3e;--ink:#f1f4fb;--muted:#b6c2d7;--line:#3c485e;--accent:#baa4ff;--accent-soft:#34284e;--green:#8ee1b3;--green-soft:#203d32;--red:#ff9eae;--red-soft:#442733;--amber:#f2cc7c;--amber-soft:#403524;--shadow:none}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:860px;margin:0 auto;padding:24px 16px 80px}
a{color:var(--accent);text-underline-offset:3px;overflow-wrap:anywhere}
h1{font-size:1.9rem;line-height:1.2;margin:.2em 0 .4em}
h2{font-size:1.4rem;margin:2.2em 0 .6em;padding-top:.6em;border-top:1px solid var(--line)}
h3{font-size:1.12rem;margin:1.6em 0 .5em}
h4{font-size:1rem;margin:1.4em 0 .4em;color:var(--muted)}
p,li{overflow-wrap:anywhere}
.byline{color:var(--muted);margin:0 0 .3em}
.meta{color:var(--muted);font-size:.9rem}
nav.toc{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:20px 0;box-shadow:var(--shadow);font-size:.92rem}
nav.toc a{margin-right:12px;white-space:nowrap}
section.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:6px 18px 12px;margin:18px 0;box-shadow:var(--shadow)}
.badge{display:inline-block;padding:1px 10px;border-radius:999px;font-weight:700;font-size:.82rem;margin-right:8px;background:var(--soft);color:var(--ink)}
.s-shown{background:var(--green-soft);color:var(--green)}
.s-not-shown{background:var(--amber-soft);color:var(--amber)}
.s-against{background:var(--red-soft);color:var(--red)}
.s-exploratory{background:var(--accent-soft);color:var(--accent)}
.tw{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{border:1px solid var(--line);padding:5px 9px;text-align:left;vertical-align:top}
thead th{background:var(--soft)}
tbody th{font-weight:600}
td{font-variant-numeric:tabular-nums}
pre{background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:10px 12px;overflow-x:auto;font-size:.82rem;white-space:pre-wrap;overflow-wrap:anywhere}
code{font:.88em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--soft);padding:1px 5px;border-radius:5px;overflow-wrap:anywhere;word-break:break-all}
pre code{background:none;padding:0;word-break:normal}
blockquote{margin:12px 0;padding:8px 14px;border-left:4px solid var(--amber);background:var(--amber-soft);border-radius:0 10px 10px 0}
blockquote.retracted{border-color:var(--red);background:var(--red-soft)}
@media (max-width:560px){main{padding:16px 16px 60px}h1{font-size:1.55rem}section.card{padding:2px 12px 10px}}
@media print{:root{color-scheme:light;--bg:#fff;--panel:#fff;--soft:#f1f3f7;--ink:#111;--muted:#444;--line:#bbb;--accent:#3b1d99;--shadow:none}body{font-size:10.5pt}nav.toc{display:none}section.card{break-inside:avoid-page;box-shadow:none}h2{break-after:avoid}a{color:inherit}pre,table{break-inside:avoid}}
"""


def build_html(P, S):
    cfg = P["config"]
    d = datetime.date.fromisoformat(cfg["date"])
    c = cfg["citation"]
    meta = [
        ("citation_title", cfg["title"]), ("citation_author", cfg["author"]),
        ("citation_publication_date", d.strftime("%Y/%m/%d")), ("citation_online_date", d.strftime("%Y/%m/%d")),
        ("citation_doi", c["doi"]), ("citation_pdf_url", c["pdf_url"]), ("citation_keywords", c["keywords"]),
        ("citation_language", "en"), ("description", "A living technical report on whether an AI agent's done can be trusted. Version %s." % cfg["version"]),
        ("author", cfg["author"]),
    ]
    head = "\n".join('<meta name="%s" content="%s">' % (k, html.escape(v, quote=True)) for k, v in meta)
    body = "\n".join(md_to_html(md) for _, md in S)
    toc = ['<nav class="toc" aria-label="Contents">']
    for label, anchor in [("Summary", "1-summary"), ("Method", "2-method"), ("Findings", "3-findings"), ("Limits", "4-limits-and-threats-to-validity"),
                          ("What's next", "5-what-s-next"), ("Changelog", "6-changelog"), ("Verify", "appendix-a-how-to-verify"),
                          ("Evidence", "appendix-b-evidence-lines"), ("Seals", "appendix-c-seals")]:
        toc.append('<a href="#%s">%s</a>' % (anchor, label))
    toc.append("</nav>")
    byline = "%s · version %s · %d %s %d" % (cfg["author_line"], cfg["version"], d.day, MONTHS[d.month - 1], d.year)
    top = ('<h1>%s</h1>\n<p class="byline">%s</p>\n<p class="meta">Contact: %s. DOI of this version: %s. Concept DOI (always the latest): %s. Licence: %s</p>\n%s'
           % (html.escape(cfg["title"], quote=False), html.escape(byline), html.escape(cfg["contact"]), html.escape(c["doi"]), html.escape(c["concept_doi"]), html.escape(cfg["license"]), "\n".join(toc)))
    return ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            "<title>%s</title>\n%s\n<style>%s</style>\n</head>\n<body>\n<main>\n%s\n%s\n</main>\n</body>\n</html>\n"
            % (html.escape(cfg["short_title"] + " " + cfg["version"]), head, CSS, top, body))


# ----------------------------------------------------------------- pdf
def make_pdf(P, html_path, pdf_path):
    for tool in ("pandoc", "wkhtmltopdf"):
        if shutil.which(tool):
            pass  # not used: the Edge route below renders the same HTML with the print stylesheet
    loc = P["local"]
    pw = loc.get("playwright_dir")
    if not pw or not pathlib.Path(pw).exists():
        return False, "no PDF tool configured (local.config.json playwright_dir missing); wrote HTML and Markdown only"
    node = loc.get("node", "node")
    script = ROOT / "tools" / "make_pdf.js"
    env = dict(os.environ, PLAYWRIGHT_DIR=str(pw))
    r = subprocess.run([node, str(script), str(html_path), str(pdf_path)], capture_output=True, text=True, env=env, timeout=180)
    if r.returncode != 0 or not pathlib.Path(pdf_path).exists():
        return False, "PDF step failed: " + (r.stderr or r.stdout).strip()[:300]
    return True, "wrote %s (%d bytes)" % (pdf_path, pathlib.Path(pdf_path).stat().st_size)


# ----------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="store_true")
    ap.add_argument("--verify-sources", action="store_true")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--strict-cap", action="store_true", help="fail when the full report is over the word cap")
    a = ap.parse_args(argv)
    P = load_project()
    cfg = P["config"]
    fail = False
    print("build: version %s, %d findings" % (cfg["version"], len(P["findings"])))
    errs = validate(P)
    for e in errs:
        print("FAIL data/prose check:", e)
    if errs:
        print("NUMBER AND STRUCTURE CHECK: FAIL (%d problems)" % len(errs))
        return 1
    print("NUMBER AND STRUCTURE CHECK: PASS (ids, registry, changelog, quotes hold their numbers, no raw numbers in prose)")
    S = render_sections(P)
    bad = check_rendered_numbers(P, S)
    for b in bad:
        print("FAIL rendered number not in any finding file:", b)
    if bad:
        print("RENDERED NUMBER CHECK: FAIL")
        return 1
    print("RENDERED NUMBER CHECK: PASS (every number in sections 1 to 5 is in a finding file)")
    md = compose_md(P, S)
    full_words = count_words(counted_scope(S))
    PS = paper_sections(P)
    paper_words = count_words(counted_scope(PS))
    cap = cfg["word_cap"]
    print("WORD COUNT: full report %d words in scope, paper extract %d words, cap %d (%s)" % (full_words, paper_words, cap, cfg["word_cap_scope"]))
    if paper_words > cap:
        print("WORD CAP CHECK: FAIL (paper extract is over the cap)")
        fail = True
    elif full_words > cap:
        print("WORD CAP CHECK: PASS for the paper extract; the full report is over the cap (flag cards paper:false to trim the extract)")
        fail = fail or a.strict_cap
    else:
        print("WORD CAP CHECK: PASS")
    doc = build_html(P, S)
    miss = html_checks(doc)
    if miss:
        print("CITATION TAG CHECK: FAIL missing", miss)
        fail = True
    else:
        print("CITATION TAG CHECK: PASS (citation_title, citation_author, citation_publication_date, citation_doi, citation_pdf_url)")
    placeholders = [k for k in ("doi", "concept_doi", "pdf_url") if cfg["citation"][k].startswith("PENDING")]
    if placeholders:
        print("NOTE: citation placeholders still set: %s (fine for a draft; --release refuses)" % ", ".join(placeholders))
    if a.verify_sources:
        n, bad = verify_sources(P)
        for b in bad:
            print("FAIL source check:", b)
        if bad:
            print("SOURCE QUOTE CHECK: FAIL")
            fail = True
        else:
            print("SOURCE QUOTE CHECK: PASS (%d quoted lines and seal lists checked against the local copies)" % n)
    if fail:
        return 1
    if a.check_only:
        return 0
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    (dist / "report.md").write_text(md, encoding="utf-8", newline="\n")
    (dist / "report.html").write_text(doc, encoding="utf-8", newline="\n")
    paper_md = front_paper(P) + "\n\n".join(m for k, m in PS if k in ("summary", "method", "findings", "limits", "next", "ack")) + "\n"
    (dist / "paper.md").write_text(paper_md, encoding="utf-8", newline="\n")
    print("wrote dist/report.md, dist/report.html, dist/paper.md")
    if a.pdf:
        ok, msg = make_pdf(P, dist / "report.html", dist / "report.pdf")
        print(("PDF: " if ok else "PDF NOT PRODUCED: ") + msg)
    gaps = public_gaps(P)
    if gaps:
        print("NOTE: %d evidence sources name no public copy (a release needs none): %s" % (len(gaps), "; ".join(gaps[:3])))
    else:
        print("PUBLIC SOURCE CHECK: PASS (every quoted source names a public copy)")
    if a.release:
        if gaps:
            print("RELEASE REFUSED: evidence sources with no public copy: %s" % "; ".join(gaps))
            return 1
        if placeholders:
            print("RELEASE REFUSED: citation placeholders remain: %s" % ", ".join(placeholders))
            return 1
        rel = ROOT / "releases" / ("v" + cfg["version"])
        if rel.exists():
            print("RELEASE REFUSED: %s already exists; releases are never overwritten" % rel)
            return 1
        shutil.copytree(dist, rel)
        print("copied dist/ to", rel)
    return 0


def front_paper(P):
    cfg = P["config"]
    return "# %s (paper extract)\n\n%s · version %s\n\n" % (cfg["title"], cfg["author_line"], cfg["version"])


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as e:
        print("FAIL build:", e)
        sys.exit(1)
