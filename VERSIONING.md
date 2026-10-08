# Versioning and release plan

This report is living: findings are added as studies finish. Each release is a frozen copy with its own DOI. Nothing is released from this repository without my yes.

## Zenodo: one concept DOI, one DOI per version

- The **concept DOI** always resolves to the latest release. Cite it when you mean "the report".
- Each release gets its own **version DOI**. Cite that when you mean "this exact text and these numbers".
- Both DOIs are written into the build: `report.config.json`, keys `citation.concept_doi` and `citation.doi`. Until a release they hold `PENDING-...` placeholders, and `python build.py --release` refuses to run while any remain.
- Zenodo can reserve a version DOI before it is published, so the DOI can be printed inside the PDF of the same release.

## Semantic versions

| Change | Version step | Example |
|---|---|---|
| New findings (cards added, nothing else changed) | **minor**: 1.0.0 to 1.1.0 | F010 and F011 added |
| Correction to an existing card: a count, a quote, a limit, a record correction, a retraction, a supersession | **patch**: 1.1.0 to 1.1.1 | a parser audit moves a count |
| A change in structure: sections, what a status means, how a finding is defined | **major**: 1.x.y to 2.0.0 | not planned |

Cards are never renumbered or deleted. A retracted or superseded card stays in place, marked, and the changelog says in which version it changed.

## What triggers a release

1. **A finding is added.** A sealed result is counted, its numbers are copied exactly from the sealed record into a new `findings/Fnnn-*.json` file (path and quoted line for each count), and the id is appended to `registry.json`. Minor release.
2. **A correction.** Any change to a published number, quote, limit or status. Patch release, soon, because a wrong number should not sit under a DOI.
3. **A retraction.** Patch release. The card stays, marked RETRACTED, with the reason.
4. **Not a trigger:** wording polish alone, a new open question, a newly registered study with no results. Those wait for the next release.

## How to cut a release

1. Edit data only: add or change `findings/`, `next.json`, `prose/`. Add `changelog/X.Y.Z.json` (version, date, summary, added, changed, superseded, retracted). Set `version` in `report.config.json` to the same X.Y.Z.
2. Run `python -m unittest discover -s tests` and `python build.py --pdf --verify-sources`. Every line must say PASS (number check, rendered number check, word cap, citation tags, source quotes).
3. Reserve the version DOI on Zenodo, put it in `citation.doi`, and rebuild.
4. Run `python build.py --release`. It copies `dist/` to `releases/vX.Y.Z/` and refuses to overwrite an existing release.
5. Upload `report.pdf`, `report.html`, `report.md` and a zip of `findings/` to the Zenodo version. Set `citation.pdf_url` to the file's public link for the next build.
6. Commit and tag `vX.Y.Z`.

## Every release's data is also in the public research record

A release is only as checkable as its sources. Before a release:

- Every quoted line must come from a file that is in the public research record (DOI 10.5281/zenodo.23227858 and its later versions) or the public Kaggle datasets. Each evidence entry names its public copy (`source.public`), and `--release` refuses when one is missing.
- The seal lists named in each card must be in the public record too, so that Appendix A's checks can be run by anyone.
- The release's own `findings/*.json` ship with it, so the data behind every number travels with the report.

New sealed studies go into the public research record first (as a new bundle or a new version of it), then into this report.

## The paper extract and the word cap

`dist/paper.md` is the same source cut to sections 1 to 5, for the Gemma 4 paper track writeup. It must stay at or under the cap in `report.config.json` (`word_cap`). When the report outgrows the cap, set `"paper": false` on the cards that are not central; the full report keeps them, the extract drops them, and the build checks the extract.
