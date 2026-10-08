# The Coat Check: a living technical report

By Joshua Bauer (ISWT42), independent researcher. Contact: joshua@iswt.ca. Built with Claude (Anthropic) as research assistant. Local repository only; nothing here has been published.

The report asks whether an AI agent's "done" can be trusted. It is built from data: every number comes from a finding file that names the sealed record and the exact line it was copied from.

## Build

```
python build.py --pdf --verify-sources
python -m unittest discover -s tests
```

Python 3, standard library only. `--pdf` prints `dist/report.pdf` with the Edge browser that is already installed (headless, no window), if `local.config.json` names it; without it the build stops at HTML and Markdown. `--verify-sources` checks every quoted line and seal list against the local copies named in `local.config.json` (not committed).

Outputs in `dist/`: `report.md`, `report.html` (self-contained, light and dark, phone width, Google Scholar `citation_*` tags), `report.pdf`, `paper.md` (the extract for a word-capped writeup).

## Layout

| Path | What it holds |
|---|---|
| `findings/Fnnn-*.json` | One file per finding: counts with denominators, source path and quoted line, tests, limits, seal, links, status, version. The source of truth. |
| `prose/*.md` | Hand-written sections (summary intro, method, limits, appendix A). They may not type a number; they use `{{F005.c.chain_records}}`-style placeholders. |
| `next.json` | Open questions. Items change status; they are not deleted. |
| `changelog/X.Y.Z.json` | One file per version: findings added, changed, superseded, retracted. |
| `registry.json` | Every finding id ever issued. Append only. |
| `names.json`, `report.config.json` | Model names that contain digits; title, author, version, DOI placeholders, word cap. |
| `build.py` | The only build script: checks, renders, writes `dist/`. |
| `tools/` | `seal_info.py` (reads a seal list, its FreeTSA time and Bitcoin height, no network), `make_pdf.js`, `check_layout.js`. |
| `tests/` | Planted-fault tests: each check must fail when its fault is planted. |
| `VERSIONING.md` | Zenodo concept and version DOIs, semantic versions, release triggers. |

## The checks (all must pass)

1. Structure: ids unique, registry matches the files, changelog covers every card and the version.
2. Numbers: every count's number and denominator is in its quoted line; no raw number or number word typed in prose; every placeholder resolves.
3. Rendered numbers: every number in sections 1 to 5 of the output exists in a finding file.
4. Word cap on the paper extract.
5. Citation tags, anchors, no unresolved placeholder in the HTML.
6. With `--verify-sources`: each quote is found in its source file and each seal list still has its recorded SHA-256.

## Adding a finding

Copy the shape of an existing file in `findings/`. Take each count's line from the sealed record, not from memory. Append the id to `registry.json`, add it to the next `changelog/` file, run the build.
