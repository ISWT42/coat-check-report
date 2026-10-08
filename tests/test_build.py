"""Tests for the report build. Run: python -m unittest discover -s tests -v

These tests plant faults on purpose. Each one must make the build fail; if a
check stops catching its fault, the test goes red. Do not weaken them to make a
build pass (fix the data instead).
"""
import copy
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402


def project():
    return build.load_project(ROOT)


def next_version(P):
    # one patch above the latest real release, so fixtures never collide with a real version
    major, minor, patch = (int(x) for x in P["changelog"][-1]["version"].split("."))
    return "%d.%d.%d" % (major, minor, patch + 1)


class Clean(unittest.TestCase):
    def test_current_project_has_no_errors(self):
        self.assertEqual(build.validate(project()), [])

    def test_every_rendered_number_is_in_a_finding_file(self):
        P = project()
        self.assertEqual(build.check_rendered_numbers(P, build.render_sections(P)), [])

    def test_render_is_deterministic(self):
        P = project()
        a = build.compose_md(P)
        b = build.compose_md(project())
        self.assertEqual(a, b)
        self.assertEqual(build.build_html(P, build.render_sections(P)), build.build_html(project(), build.render_sections(project())))

    def test_html_has_citation_tags_and_anchors(self):
        P = project()
        doc = build.build_html(P, build.render_sections(P))
        self.assertEqual(build.html_checks(doc), [])
        self.assertIn('name="citation_author" content="Joshua Bauer"', doc)
        self.assertIn("prefers-color-scheme:dark", doc)
        self.assertIn('name="viewport"', doc)

    def test_word_cap_holds(self):
        P = project()
        # the cap applies to the paper extract (VERSIONING.md); cards flagged paper:false stay in the full report
        S = build.paper_sections(P)
        self.assertLessEqual(build.count_words(build.counted_scope(S)), P["config"]["word_cap"])

    def test_cards_are_in_id_order(self):
        P = project()
        ids = [f["id"] for f in P["findings"]]
        self.assertEqual(ids, sorted(ids))
        md = build.compose_md(P)
        pos = [md.index("### %s." % i) for i in ids]
        self.assertEqual(pos, sorted(pos))


class Disclosure(unittest.TestCase):
    """Version 1.3.0: the disclosure and the narrowed bench wording must stay in."""

    def test_interests_section_is_in_the_report_and_the_paper_extract(self):
        P = project()
        full = build.compose_md(P)
        paper = "\n\n".join(md for _, md in build.paper_sections(P))
        for md in (full, paper):
            self.assertIn("### Interests and independence", md)
            self.assertIn("developer-led, not independent validation", md)
            self.assertIn("I hold no investments in AI companies", md)

    def test_acknowledgement_names_an_outside_methods_review_and_no_tool(self):
        ack = project()["config"]["acknowledgement"]
        self.assertIn("outside methods review", ack)
        self.assertNotIn("peer review", ack)

    def test_bench_cards_keep_their_narrowed_claims_and_limits(self):
        P = project()
        for fid in ("F010", "F011"):
            md = build.render_card(P, P["by_id"][fid])
            for phrase in ("not assumption-free", "exchangeability", "combined policy" if fid == "F011" else "deterministic-gate control",
                           "easy case", "privileged information"):
                self.assertIn(phrase, md, "%s lost %r" % (fid, phrase))
            for old in ("did not know", "found every failing job", "stopped false done", "ticket alone did not help", "before any model call"):
                self.assertNotIn(old, md, "%s still says %r" % (fid, old))
        self.assertIn("a benefit from the ticket alone was not shown", build.render_card(P, P["by_id"]["F010"]).lower())

    def test_bench_seals_say_before_the_scored_run(self):
        P = project()
        for fid in ("F010", "F011"):
            for s in P["by_id"][fid]["seal"]:
                self.assertNotIn("before any model call", s["role"])
            self.assertIn("sealed before the scored run", P["by_id"][fid]["seal"][0]["role"])


class PlantedFaults(unittest.TestCase):
    def test_raw_digit_in_prose_fails(self):
        P = project()
        P["prose"]["limits"] += "\n- **Extra.** It failed 17 times.\n"
        self.assertTrue(any("raw number" in e and "17" in e for e in build.validate(P)))

    def test_raw_digit_in_a_finding_headline_fails(self):
        P = project()
        P["findings"][0]["headline"] += " It was 23 of 40."
        self.assertTrue(any("raw number" in e for e in build.validate(P)))

    def test_number_word_in_prose_fails(self):
        P = project()
        P["prose"]["limits"] += "\n- **Extra.** It failed seven times.\n"
        self.assertTrue(any("number word 'seven'" in e for e in build.validate(P)))

    def test_masked_things_are_not_numbers(self):
        P = project()
        P["prose"]["limits"] += "\n- **Extra.** See https://example.org/a/12 and F001, 2026-10-08, Gemini 3.7 Flash.\n"
        self.assertEqual(build.validate(P), [])

    def test_unresolved_placeholder_fails(self):
        P = project()
        P["prose"]["limits"] += "\n- **Extra.** {{F001.c.no_such_key}}\n"
        self.assertTrue(any("does not resolve" in e for e in build.validate(P)))

    def test_deleted_card_fails(self):
        P = project()
        gone = P["findings"].pop()
        P["by_id"].pop(gone["id"])
        self.assertTrue(any("never deleted" in e for e in build.validate(P)))

    def test_unregistered_card_fails(self):
        P = project()
        P["registry"] = P["registry"][:-1]
        self.assertTrue(any("not in registry.json" in e for e in build.validate(P)))

    def test_duplicate_id_fails(self):
        P = project()
        P["findings"].append(copy.deepcopy(P["findings"][0]))
        self.assertTrue(any("duplicate finding id" in e for e in build.validate(P)))

    def test_count_must_appear_in_its_quote(self):
        P = project()
        P["findings"][1]["counts"][0]["n"] = "99"
        self.assertTrue(any("is not in the quoted line" in e for e in build.validate(P)))

    def test_denominator_needs_a_basis_when_not_quoted(self):
        P = project()
        c = next(c for c in P["findings"][7]["counts"] if c.get("d_basis"))
        c.pop("d_basis")
        c["d"] = "61"
        self.assertTrue(any("denominator" in e for e in build.validate(P)))

    def test_table_literal_cell_must_be_in_row_quote(self):
        P = project()
        tb = next(t for f in P["findings"] for t in f["tables"] if any(not str(c).startswith("@") for r in t["rows"] for c in r["cells"]))
        row = next(r for r in tb["rows"] if any(not str(c).startswith("@") for c in r["cells"]))
        row["cells"][0] = "88888"
        self.assertTrue(any("not in the row's quoted line" in e for e in build.validate(P)))

    def test_test_value_must_be_in_its_quote(self):
        P = project()
        f = next(f for f in P["findings"] if f["tests"])
        f["tests"][0]["p"] = "0.4242"
        self.assertTrue(any("is not in the quoted line" in e for e in build.validate(P)))

    def test_version_must_match_latest_changelog(self):
        P = project()
        P["config"]["version"] = next_version(P)
        self.assertTrue(any("latest changelog version" in e for e in build.validate(P)))

    def test_finding_needs_a_changelog_entry(self):
        P = project()
        P["findings"][0]["version_first_included"] = "9.9.9"
        self.assertTrue(any("no changelog entry" in e for e in build.validate(P)))

    def test_bad_status_fails(self):
        P = project()
        P["findings"][0]["status"] = "proven"
        self.assertTrue(any("status" in e for e in build.validate(P)))

    def test_rendered_number_check_catches_a_stray_number(self):
        P = project()
        S = build.render_sections(P)
        S = [(k, md + "\n\nThe team saw 9876 errors." if k == "method" else md) for k, md in S]
        self.assertTrue(build.check_rendered_numbers(P, S))


class Lifecycle(unittest.TestCase):
    def _with_retraction(self):
        P = project()
        f = P["findings"][2]
        f["lifecycle"] = "retracted"
        v = next_version(P)
        f["retraction"] = {"version": v, "date": "2026-10-09", "reason": "The counts were from the wrong run."}
        P["changelog"].append({"version": v, "date": "2026-10-09", "summary": "Correction.", "added": [], "changed": [], "superseded": [], "retracted": [f["id"]]})
        P["config"]["version"] = v
        return P, f

    def test_retracted_card_stays_visible_and_marked(self):
        P, f = self._with_retraction()
        self.assertEqual(build.validate(P), [])
        md = build.compose_md(P)
        self.assertIn("### %s." % f["id"], md)
        self.assertIn("RETRACTED in version " + P["config"]["version"], md)
        self.assertIn("(RETRACTED)", md)
        self.assertIn("Retracted (card kept, marked): %s" % f["id"], md)
        self.assertIn("**Result.**", md.split("### %s." % f["id"])[1].split("### F")[0])

    def test_retraction_needs_a_reason_and_changelog(self):
        P, f = self._with_retraction()
        f["retraction"]["reason"] = ""
        self.assertTrue(any("retraction needs" in e for e in build.validate(P)))

    def test_superseded_needs_an_existing_target(self):
        P = project()
        f = P["findings"][0]
        f["lifecycle"] = "superseded"
        f["superseded_by"] = "F777"
        self.assertTrue(any("superseded_by" in e for e in build.validate(P)))

    def test_superseded_card_is_kept_and_marked(self):
        P = project()
        f = P["findings"][0]
        f["lifecycle"] = "superseded"
        f["superseded_by"] = "F002"
        v = next_version(P)
        f["superseded_in"] = v
        P["changelog"].append({"version": v, "date": "2026-10-09", "summary": "Superseded one card.", "added": [], "changed": [], "superseded": [f["id"]], "retracted": []})
        P["config"]["version"] = v
        self.assertEqual(build.validate(P), [])
        md = build.compose_md(P)
        self.assertIn("Superseded by F002", md)
        self.assertIn("### %s." % f["id"], md)


if __name__ == "__main__":
    unittest.main()
