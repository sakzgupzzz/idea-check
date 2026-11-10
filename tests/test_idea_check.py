"""Offline tests for the API runner and the shared prompt file.

No network and no SDK needed:
    python -m unittest discover -s tests
"""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

import idea_check as ic  # noqa: E402

PLACEHOLDER = re.compile(r"\{[A-Z_]+\}")
IDEA = "a tool that turns meeting recordings into Jira tickets"


class Prompts(unittest.TestCase):
    def setUp(self):
        self.blocks, self.orders = ic.load_prompts()

    def test_thread_prompts_are_fully_substituted(self):
        for _, title in ic.THREADS:
            prompt = ic.thread_prompt(self.blocks, title, IDEA, "software product")
            self.assertIsNone(PLACEHOLDER.search(prompt), title)
            self.assertIn(IDEA, prompt)
            self.assertIn("Assume prior art exists", prompt)

    def test_api_threads_reply_in_full_not_with_a_summary(self):
        # Regression: the runner once left the skill's "write a file, reply
        # with a 200-word summary" instruction in place.
        for _, title in ic.THREADS:
            prompt = ic.thread_prompt(self.blocks, title, IDEA, "service")
            self.assertIn("Reply with your full findings", prompt)
            self.assertNotIn("summary under 200 words", prompt)

    def test_skill_output_instruction_uses_only_known_placeholders(self):
        out = ic.fill(self.blocks["Output instruction: skill"],
                      NOTES_DIR="/tmp/notes", FILENAME="prior-art")
        self.assertIn("/tmp/notes/prior-art.md", out)

    def test_reader_prompts_differ_in_wording_and_notes_order(self):
        notes = {k: f"NOTES-{k}" for k, _ in ic.THREADS}
        prompts = [ic.reader_prompt(self.blocks, self.orders, r, IDEA, notes)
                   for r in ic.READERS]
        self.assertEqual(len(set(prompts)), 3)
        seen_orders = set()
        for reader, prompt in zip(ic.READERS, prompts):
            self.assertIsNone(PLACEHOLDER.search(prompt), reader)
            for label in ic.LABELS:
                self.assertIn(f"- {label}:", prompt)
            order = tuple(re.findall(r'<notes thread="([^"]+)">', prompt))
            self.assertEqual(list(order), self.orders[reader])
            seen_orders.add(order)
        self.assertEqual(len(seen_orders), 3)

    def test_synthesis_prompt_carries_the_report_format(self):
        system = ic.synthesis_system(self.blocks)
        self.assertIsNone(PLACEHOLDER.search(system))
        for needle in ("label_reads:", "What would have to be true", "The roast",
                       ic.SUMMARY_MARK, "At most 150 words"):
            self.assertIn(needle, system)

    def test_fill_rejects_a_placeholder_with_no_value(self):
        with self.assertRaises(ic.PromptError):
            ic.fill("about {IDEA} of {TYPE}", IDEA="x")

    def test_fill_does_not_resubstitute_inside_values(self):
        self.assertEqual(ic.fill("{IDEA} / {TYPE}", IDEA="uses {TYPE}", TYPE="service"),
                         "uses {TYPE} / service")

    def test_missing_section_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "prompts.md"
            p.write_text("## Shared block\n\n```\nhello\n```\n", encoding="utf-8")
            with self.assertRaises(ic.PromptError):
                ic.load_prompts(p)


class Labels(unittest.TestCase):
    def test_parse_label_tolerates_formatting(self):
        cases = {
            "Saturated\nBecause.": "Saturated",
            "**Crowded**\nBecause.": "Crowded",
            "\nLabel: open.\nBecause.": "Open",
            "# Saturated": "Saturated",
            "Open or Crowded, hard to say": "Unlabelled",
            "The notes show many vendors.\nSaturated": "Unlabelled",
            "": "Unlabelled",
        }
        for read, want in cases.items():
            self.assertEqual(ic.parse_label(read), want, repr(read))

    def test_overall_label(self):
        self.assertEqual(ic.overall_label(["Open", "Open", "Crowded"]), "Open")
        self.assertEqual(ic.overall_label(["Open", "Crowded", "Saturated"]), "Split")
        self.assertEqual(ic.overall_label(["Open", "Unlabelled", "Unlabelled"]), "Split")
        self.assertEqual(ic.overall_label(["Saturated"] * 3), "Saturated")


class ReportPage(unittest.TestCase):
    SYNTHESIS = (
        "---\nidea: a thing -- with a dash\ntitle: Thing Check\nslug: wrong\n"
        "label: Open\nlabel_reads: [Open, Open, Open]\ntop_occupants: [A, B]\n---\n\n"
        '<section id="idea"><h2>The idea, as understood</h2><p>Body</p></section>\n'
        "<script>alert(1)</script>\n"
        "=== SUMMARY ===\nShort summary."
    )

    def setUp(self):
        self.template = ic.TEMPLATE_FILE.read_text(encoding="utf-8")

    def render(self, labels):
        fields, sections, summary = ic.parse_synthesis(self.SYNTHESIS)
        page = ic.render_report(self.template, fields, sections,
                                slug="right", date="2026-01-02", labels=labels)
        return page, summary

    def test_page_is_complete_and_script_free(self):
        page, summary = self.render(["Saturated", "Crowded", "Saturated"])
        self.assertEqual(summary, "Short summary.")
        self.assertIsNone(PLACEHOLDER.search(page))
        self.assertNotIn("<script", page)
        self.assertIn("<title>Thing Check</title>", page)
        self.assertIn('<section id="idea">', page)
        self.assertIn('data-label="Saturated"', page)
        # The page publishes as an artifact, which supplies its own skeleton.
        for tag in ("<!doctype", "<html", "<head>", "<body"):
            self.assertNotIn(tag, page.lower())

    def test_runner_values_override_the_models_in_the_metadata(self):
        page, _ = self.render(["Open", "Crowded", "Saturated"])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.html"
            p.write_text(page, encoding="utf-8")
            meta = ic.read_front_matter(p)
        self.assertEqual(meta["slug"], "right")
        self.assertEqual(meta["date"], "2026-01-02")
        self.assertEqual(meta["label"], "Split")
        self.assertEqual(meta["label_reads"], "[Open, Crowded, Saturated]")
        self.assertEqual(meta["top_occupants"], "[A, B]")
        self.assertEqual(meta["idea"], "a thing - with a dash")

    def test_scale_marks_each_read_on_its_stop(self):
        scale = ic.scale_html(["Saturated", "Crowded", "Saturated"])
        self.assertIn('stop-open"><span class="marks"></span>', scale)
        self.assertIn('stop-crowded chosen"><span class="marks"><i>2</i></span>', scale)
        self.assertIn('stop-saturated chosen"><span class="marks"><i>1</i><i>3</i></span>', scale)

    def test_old_markdown_front_matter_is_still_read(self):
        meta = ic.read_front_matter(ROOT / "examples" / "2026-11-03-robotics-lab-startup.md")
        self.assertEqual(meta["label"], "Saturated")


class Runs(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(ic.slugify("An App, that does X!"), "an-app-that-does-x")
        self.assertEqual(ic.slugify("!!!"), "idea")
        self.assertLessEqual(len(ic.slugify("word " * 50)), 40)

    def test_new_run_name_never_reuses_a_taken_name(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertEqual(ic.new_run_name(out, "2026-01-02", "x"), "2026-01-02-x")
            (out / "2026-01-02-x.html").write_text("r", encoding="utf-8")
            self.assertEqual(ic.new_run_name(out, "2026-01-02", "x"), "2026-01-02-x-2")
            (out / "notes" / "2026-01-02-x-2").mkdir(parents=True)
            self.assertEqual(ic.new_run_name(out, "2026-01-02", "x"), "2026-01-02-x-3")

    def test_related_checks_finds_an_overlapping_example(self):
        examples = ROOT / "examples"
        hits = ic.related_checks(
            examples, "a robotics lab training robot learning policies on teleop data")
        self.assertIn("2026-11-03-robotics-lab-startup.md", [p.name for p, _ in hits])
        self.assertEqual(ic.related_checks(examples, "a sourdough bakery subscription"), [])

    def test_cached_reuses_only_when_resuming(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "n.md"
            self.assertEqual(ic.cached(p, lambda: "first", resume=True), "first")
            self.assertEqual(ic.cached(p, lambda: "second", resume=True), "first")
            self.assertEqual(ic.cached(p, lambda: "third", resume=False), "third")

    def test_run_all_finishes_every_job_before_failing(self):
        done = []

        def ok():
            done.append(1)
            return "fine"

        def bad():
            raise RuntimeError("boom")

        with self.assertRaises(ic.StageFailed) as ctx:
            ic.run_all({"a": bad, "b": ok, "c": ok})
        self.assertEqual(list(ctx.exception.errors), ["a"])
        self.assertEqual(len(done), 2)


class DryRun(unittest.TestCase):
    def test_dry_run_prints_complete_prompts_without_the_sdk(self):
        with tempfile.TemporaryDirectory() as d:
            result = subprocess.run(
                [sys.executable, str(ROOT / "api" / "idea_check.py"), IDEA,
                 "--dry-run", "--out", d],
                capture_output=True, text=True, encoding="utf-8",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(PLACEHOLDER.search(result.stdout))
        for needle in ("Thread 4: commodity floor", "Reader 3", "synthesis system prompt"):
            self.assertIn(needle, result.stdout)


if __name__ == "__main__":
    unittest.main()
