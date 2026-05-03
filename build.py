"""Build app/questions.json from one or more source markdown set pairs.

Run from the aphug-practice/ folder:
    py build.py

Output: aphug-practice/app/questions.json

Sets are configured below. Each set has its own questions and answers
markdown file. Set 1 keeps the original ids (q01..q60) so existing
mastery in localStorage survives. Sets 2+ are prefixed (s2-q01...) so
ids never collide.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "source"
OUTPUT = ROOT / "app" / "questions.json"

SETS = [
    {
        "set": 1,
        "label": "Set 1",
        "id_prefix": "",
        "questions": SOURCE / "AP_HuG_Practice_Questions.md",
        "answers":   SOURCE / "AP_HuG_Practice_Answers.md",
    },
    {
        "set": 2,
        "label": "Set 2",
        "id_prefix": "s2-",
        "questions": SOURCE / "AP_HuG_Practice_Questions_Set2.md",
        "answers":   SOURCE / "AP_HuG_Practice_Answers_Set2.md",
    },
]

UNITS = {
    1: {"label": "Thinking Geographically",          "short": "Unit 1"},
    2: {"label": "Population & Migration",           "short": "Unit 2"},
    3: {"label": "Cultural Patterns & Processes",    "short": "Unit 3"},
    4: {"label": "Political Patterns & Processes",   "short": "Unit 4"},
    5: {"label": "Agriculture & Rural Land Use",     "short": "Unit 5"},
    6: {"label": "Cities & Urban Land Use",          "short": "Unit 6"},
    7: {"label": "Industrial & Economic Development","short": "Unit 7"},
}

UNIT_HEADER_RE = re.compile(r"^##\s+Unit\s+(\d+)\s*:\s*(.+?)\s*$", re.MULTILINE)

# Question header — supports both formats:
#   "### Question 7"            (Set 1)
#   "**Q7.** A geographer..."   (Set 2; stem may follow on same line)
QUESTION_HEADER_RE = re.compile(
    r"^(?:###\s+Question\s+(\d+)\s*$|\*\*Q(\d+)\.\*\*\s*(.*)$)",
    re.MULTILINE,
)
# Options — supports "A)" and "A."
OPTION_RE = re.compile(r"^([A-E])[.)]\s+(.+)$", re.MULTILINE)


def parse_questions(text):
    """Return list of dicts: {n, unit, stem_md, options:[{letter,text}]}."""
    unit_spans = []
    for m in UNIT_HEADER_RE.finditer(text):
        unit_spans.append((int(m.group(1)), m.start(), m.end()))
    if not unit_spans:
        raise SystemExit("No '## Unit N:' headers found in questions file.")

    def unit_for_pos(pos):
        current = unit_spans[0][0]
        for unit_num, start, _end in unit_spans:
            if start <= pos:
                current = unit_num
            else:
                break
        return current

    out = []
    headers = list(QUESTION_HEADER_RE.finditer(text))
    for i, m in enumerate(headers):
        qnum = int(m.group(1) or m.group(2))
        same_line_stem = (m.group(3) or "").strip()
        body_start = m.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[body_start:body_end].strip()

        # Strip trailing horizontal rule and unit headers / end-of-test markers.
        body = re.sub(r"\n---\s*$", "", body).strip()
        body = re.sub(r"^##\s+Unit\s+\d+\s*:.*$", "", body, flags=re.MULTILINE).strip()
        body = re.sub(r"\*End of practice test\.[^\n]*", "", body).strip()

        if same_line_stem:
            body = same_line_stem + ("\n\n" + body if body else "")

        opt_matches = list(OPTION_RE.finditer(body))
        if not opt_matches:
            print(f"WARNING: Q{qnum} has no A./A) options")
            stem_md = body
            options = []
        else:
            stem_md = body[: opt_matches[0].start()].rstrip()
            options = [
                {"letter": om.group(1), "text": om.group(2).strip()}
                for om in opt_matches
            ]

        out.append({
            "n": qnum,
            "unit": unit_for_pos(m.start()),
            "stem_md": stem_md,
            "options": options,
        })
    return out


# Answer header — supports both formats:
#   "**Q12: B — Situation**"   (Set 1, with headline)
#   "**Q12. B.** explanation"  (Set 2, no headline; explanation continues inline)
ANSWER_HEADER_RE = re.compile(
    r"^(?:"
    r"\*\*Q(\d+)\s*:\s*([A-E])\s*[—–-]\s*(.+?)\*\*\s*$"     # set 1
    r"|"
    r"\*\*Q(\d+)\.\s+([A-E])\.\*\*\s*(.*)$"                  # set 2
    r")",
    re.MULTILINE,
)
# Footer line "*Topic 1.5 | Skill 1.A*" (set 1).
TOPIC_SKILL_FOOTER_RE = re.compile(
    r"^\*Topic\s+(\d+(?:\.\d+)?)\s*\|\s*Skill\s+(\d+\.[A-Z]+)\*\s*$",
    re.MULTILINE,
)
# Inline trailing "Topic 1.1. Skill 4.A." (set 2). Trailing period is part of
# the prose, not the code, so strip it via the optional \. outside the group.
TOPIC_SKILL_INLINE_RE = re.compile(
    r"\s*Topic\s+(\d+(?:\.\d+)?)\.?\s+Skill\s+(\d+\.[A-Z]+)\.?\s*$",
)


def parse_answers(text):
    """Return dict keyed by question number → {letter, headline, explanation_md, topic, skill}."""
    out = {}
    headers = list(ANSWER_HEADER_RE.finditer(text))
    for i, m in enumerate(headers):
        if m.group(1):  # Set 1 format
            qnum = int(m.group(1))
            letter = m.group(2)
            headline = m.group(3).strip()
            same_line_body = ""
        else:           # Set 2 format
            qnum = int(m.group(4))
            letter = m.group(5)
            headline = ""
            same_line_body = (m.group(6) or "").strip()

        body_start = m.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[body_start:body_end].strip()

        if same_line_body:
            body = same_line_body + ("\n\n" + body if body else "")

        # Strip trailing horizontal rule and the scoring/how-to-review tail FIRST,
        # so the topic/skill regex's end-of-text anchor sees the real end.
        body = re.sub(r"\n##\s+(Scoring Guide|Scoring Rubric|How to Review).*\Z",
                      "", body, flags=re.DOTALL).strip()
        body = re.sub(r"\n---\s*$", "", body).strip()

        # Pull topic/skill from a footer line first, fall back to inline trailing.
        topic = skill = None
        ts = TOPIC_SKILL_FOOTER_RE.search(body)
        if ts:
            topic = ts.group(1)
            skill = ts.group(2)
            body = body[: ts.start()].rstrip()
        else:
            ts2 = TOPIC_SKILL_INLINE_RE.search(body)
            if ts2:
                topic = ts2.group(1)
                skill = ts2.group(2)
                body = body[: ts2.start()].rstrip()

        # Set 2 answers have no explicit headline; synthesize one from the first
        # short clause of the explanation so the green callout still reads well.
        if not headline and body:
            first_sentence = re.split(r"(?<=[.!?])\s", body, maxsplit=1)[0]
            if len(first_sentence) > 110:
                first_sentence = first_sentence[:107].rstrip() + "..."
            headline = first_sentence

        out[qnum] = {
            "letter": letter,
            "headline": headline,
            "explanation_md": body,
            "topic": topic,
            "skill": skill,
        }
    return out


def main():
    records = []
    missing_total = []
    set_meta = {}

    for spec in SETS:
        if not spec["questions"].exists() or not spec["answers"].exists():
            print(f"Skipping {spec['label']}: missing source file(s)")
            continue
        qtext = spec["questions"].read_text(encoding="utf-8")
        atext = spec["answers"].read_text(encoding="utf-8")
        questions = parse_questions(qtext)
        answers = parse_answers(atext)
        prefix = spec["id_prefix"]

        for q in questions:
            a = answers.get(q["n"])
            if not a:
                missing_total.append(f"{spec['label']} Q{q['n']}")
                continue
            records.append({
                "id": f"{prefix}q{q['n']:02d}",
                "set": spec["set"],
                "set_label": spec["label"],
                "question_number": q["n"],
                "unit": q["unit"],
                "type": "multiple-choice",
                "question_text": q["stem_md"],
                "options": q["options"],
                "correct_letters": [a["letter"]],
                "answer": a["letter"],
                "answer_headline": a["headline"],
                "explanation_md": a["explanation_md"],
                "topic_code": a["topic"],
                "skill_code": a["skill"],
            })
        set_meta[spec["set"]] = {"label": spec["label"], "count": len(questions)}

    sets_payload = {str(k): v for k, v in sorted(set_meta.items())}

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            {
                "questions": records,
                "total": len(records),
                "units": UNITS,
                "sets": sets_payload,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    by_set_unit = {}
    for r in records:
        key = (r["set"], r["unit"])
        by_set_unit[key] = by_set_unit.get(key, 0) + 1

    print(f"Wrote {len(records)} questions to {OUTPUT.relative_to(ROOT)}")
    for s in sorted(set_meta):
        total_in_set = sum(c for (sn, _), c in by_set_unit.items() if sn == s)
        print(f"\n{set_meta[s]['label']} ({total_in_set} questions):")
        for u in sorted(UNITS):
            n = by_set_unit.get((s, u), 0)
            print(f"  Unit {u}: {n}")
    if missing_total:
        print(f"\nWARNING: {len(missing_total)} question(s) had no matching answer:")
        for line in missing_total:
            print(f"  - {line}")


if __name__ == "__main__":
    main()
