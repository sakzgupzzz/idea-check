"""Offline tests for the API runner and the shared prompt file.

No network and no SDK needed:
    python -m unittest discover -s tests
"""

import contextlib
import io
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

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


class PromptFileShape(unittest.TestCase):
    """The runner takes the first fenced block under each heading and fills a
    fixed set of placeholders. These fail if the files drift from that."""

    def test_each_prompt_heading_has_exactly_one_fenced_block(self):
        text = ic.PROMPTS_FILE.read_text(encoding="utf-8")
        parts = re.split(r"^## +(.+?)[ \t]*$", text, flags=re.M)
        fences = {h: len(re.findall(r"^```", body, flags=re.M)) // 2
                  for h, body in zip(parts[1::2], parts[2::2])}
        for heading in ic.SECTIONS:
            self.assertEqual(fences.get(heading), 1, heading)

    def test_prompts_use_only_known_placeholders(self):
        blocks, _ = ic.load_prompts()
        known = {"IDEA", "TYPE", "NOTES_DIR", "FILENAME", "LABEL_DEFINITIONS", "NOTES"}
        for heading, block in blocks.items():
            used = set(ic.PLACEHOLDER.findall(block))
            self.assertLessEqual(used, known, heading)

    def test_template_has_exactly_the_slots_the_runner_fills(self):
        template = ic.TEMPLATE_FILE.read_text(encoding="utf-8")
        self.assertEqual(set(ic.PLACEHOLDER.findall(template)),
                         {"META", "TITLE", "IDEA", "DATE", "LABEL", "SCALE", "SECTIONS"})

    def test_template_loads_nothing_from_other_sites(self):
        template = ic.TEMPLATE_FILE.read_text(encoding="utf-8")
        self.assertNotRegex(template, r"(?i)<link|<script|@import|url\(\s*['\"]?https?:")


class Sanitizer(unittest.TestCase):
    def test_hostile_markup_is_removed_and_text_kept(self):
        out = ic.sanitize_sections(
            '<section id="idea" onmouseover="x()"><h2>T</h2>'
            '<p onclick="alert(1)" style="color:red">hi &amp; bye</p>'
            '<iframe src="//evil">framed</iframe><img src=x onerror=alert(1)>'
            '<script>alert(2)</script><style>p{display:none}</style>'
            '<a href="javascript:alert(3)">bad</a> <a href="https://ok.example/a?b=1&amp;c=2">good</a>'
            '</section>')
        for gone in ("onclick", "onmouseover", "onerror", "style", "<iframe", "<img",
                     "<script", "alert(2)", "display:none", "javascript:"):
            self.assertNotIn(gone, out)
        self.assertIn('<section id="idea"><h2>T</h2><p>hi &amp; bye</p>', out)
        self.assertIn("framed", out)
        self.assertIn("<a>bad</a>", out)
        self.assertIn('<a href="https://ok.example/a?b=1&amp;c=2">good</a>', out)

    def test_markup_the_template_styles_survives(self):
        src = ('<section id="occupants"><h2>Who</h2><div class="scroll"><table><thead><tr>'
               '<th>A</th></tr></thead><tbody><tr><td><strong>x</strong> <code>y</code> '
               '<span class="tag vendor">vendor claim</span></td></tr></tbody></table></div>'
               '<ol><li><em>one</em><br>two</li></ol><blockquote>q</blockquote><h3>s</h3></section>')
        self.assertEqual(ic.sanitize_sections(src), src)

    def test_unknown_ids_and_classes_are_dropped(self):
        out = ic.sanitize_sections('<section id="x"><span class="tag evil">t</span>'
                                   '<div class="other">d</div></section>')
        self.assertEqual(out, "<section><span>t</span><div>d</div></section>")


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
        self.assertRegex(ic.slugify("!!!"), r"^idea-[0-9a-f]{6}$")
        self.assertNotEqual(ic.slugify("\u65e5\u672c\u8a9e"), ic.slugify("\u4e2d\u6587"))
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



class _Stream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    """Stands in for anthropic.Anthropic(): answers each kind of request the
    runner makes, records what was asked, and can fail or pause on demand."""

    OPENERS = {
        "prior-art": "Research who already ships",
        "incumbents": "Research which established product categories",
        "graveyard-economics": "Be adversarial toward the business case",
        "commodity-floor": "Research how much of this idea",
    }
    SYNTHESIS = (
        "---\nidea: turns meeting recordings into Jira tickets\ntitle: Meeting Ticket Tool\n"
        "slug: model-slug\nlabel: Open\nlabel_reads: [Open, Open, Open]\n"
        "top_occupants: [A, B, C]\n---\n"
        '<section id="idea"><h2>The idea, as understood</h2><p>Body</p></section>\n'
        "=== SUMMARY ===\nSaturated, all three reads agreed."
    )

    def __init__(self, fail=(), pause=()):
        self.fail, self.pause = set(fail), set(pause)
        self.calls, self.requests = [], []
        self.lock = threading.Lock()
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _kind(self, kw):
        if kw.get("system"):
            return "synthesis"
        text = kw["messages"][0]["content"]
        if kw.get("tools"):
            return next(k for k, opener in self.OPENERS.items() if text.startswith(opener))
        return "reader" if "<notes thread=" in text else "type"

    def _stream(self, **kw):
        kind = self._kind(kw)
        with self.lock:
            self.calls.append(kind)
            # the runner appends to this list when it resumes, so snapshot it
            self.requests.append({**kw, "messages": list(kw["messages"])})
        if kind in self.fail:
            raise RuntimeError("boom")
        if kind in self.pause and len(kw["messages"]) == 1:
            return _Stream(SimpleNamespace(stop_reason="pause_turn", stop_details=None,
                                           content=[SimpleNamespace(type="text", text="partial")]))
        text = {"synthesis": self.SYNTHESIS, "reader": "Saturated\nBecause of X.",
                "type": "service"}.get(kind, f"## Findings\n\nNotes for {kind}.")
        return _Stream(SimpleNamespace(stop_reason="end_turn", stop_details=None,
                                       content=[SimpleNamespace(type="text", text=text)]))


class WholeRun(unittest.TestCase):
    """main() end to end against a fake client: no network, no SDK."""

    def run_main(self, argv, client):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = ic.main(argv, client=client)
        return code, out.getvalue(), err.getvalue()

    def test_full_run_writes_the_page_notes_and_reads(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            client = FakeClient(pause={"incumbents"})
            code, stdout, stderr = self.run_main([IDEA, "--out", d], client)
            self.assertEqual(code, 0, stderr)
            self.assertIn("Saturated, all three reads agreed.", stdout)

            (report,) = out.glob("*.html")
            meta = ic.read_front_matter(report)
            self.assertEqual(meta["label"], "Saturated")          # from the parsed reads,
            self.assertEqual(meta["label_reads"], "[Saturated, Saturated, Saturated]")
            self.assertNotEqual(meta["slug"], "model-slug")       # not from the model
            self.assertIn('<section id="idea">', report.read_text(encoding="utf-8"))

            notes = out / "notes" / report.stem
            self.assertEqual(sorted(p.name for p in notes.iterdir()),
                             ["commodity-floor.md", "graveyard-economics.md", "incumbents.md",
                              "prior-art.md", "reader-1.md", "reader-2.md", "reader-3.md",
                              "run.json"])
            self.assertEqual(json.loads((notes / "run.json").read_text())["type"], "service")

            # One request per step, plus one resume of the paused thread.
            self.assertEqual(client.calls.count("incumbents"), 2)
            self.assertEqual(len(client.calls), 1 + 4 + 1 + 3 + 1)
            resumed = [r for r in client.requests if len(r["messages"]) == 2]
            self.assertEqual(len(resumed), 1)
            self.assertEqual(resumed[0]["messages"][1]["role"], "assistant")
            for r in client.requests:
                self.assertEqual(bool(r.get("tools")), r["output_config"]["effort"] == "high"
                                 and not r.get("system"))

    def test_a_failed_thread_keeps_the_rest_and_resume_finishes(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            code, _, stderr = self.run_main([IDEA, "--out", d, "--type", "service"],
                                            FakeClient(fail={"prior-art"}))
            self.assertEqual(code, 1)
            self.assertIn("--resume", stderr)
            self.assertEqual(list(out.glob("*.html")), [])
            (notes,) = (out / "notes").iterdir()
            self.assertEqual(sorted(p.stem for p in notes.glob("*.md")),
                             ["commodity-floor", "graveyard-economics", "incumbents"])

            client = FakeClient()
            code, _, stderr = self.run_main(["--resume", str(notes)], client)
            self.assertEqual(code, 0, stderr)
            self.assertEqual(sorted(client.calls),
                             ["prior-art", "reader", "reader", "reader", "synthesis"])
            self.assertEqual([p.stem for p in out.glob("*.html")], [notes.name])

    def test_a_related_earlier_check_stops_the_run_unless_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            self.assertEqual(self.run_main([IDEA, "--out", d], FakeClient())[0], 0)

            client = FakeClient()
            code, _, stderr = self.run_main([IDEA, "--out", d], client)
            self.assertEqual(code, 3)
            self.assertEqual(client.calls, [])
            self.assertIn("--fresh", stderr)

            self.assertEqual(self.run_main([IDEA, "--out", d, "--fresh"], FakeClient())[0], 0)
            names = sorted(p.stem for p in out.glob("*.html"))
            self.assertEqual(len(names), 2)
            self.assertTrue(names[1].endswith("-2"), names)


if __name__ == "__main__":
    unittest.main()
