"""Build app/questions.json from the two source markdown files.

Run from the aphug-practice/ folder:
    py build.py

Output: aphug-practice/app/questions.json
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
QUESTIONS_MD = ROOT / "source" / "AP_HuG_Practice_Questions.md"
ANSWERS_MD = ROOT / "source" / "AP_HuG_Practice_Answers.md"
OUTPUT = ROOT / "app" / "questions.json"

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
QUESTION_HEADER_RE = re.compile(r"^###\s+Question\s+(\d+)\s*$", re.MULTILINE)
OPTION_RE = re.compile(r"^([A-E])\)\s+(.+)$", re.MULTILINE)


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
        qnum = int(m.group(1))
        body_start = m.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[body_start:body_end].strip()

        # Strip trailing horizontal rule and unit headers that may be in the slice.
        body = re.sub(r"\n---\s*$", "", body).strip()
        body = re.sub(r"^##\s+Unit\s+\d+\s*:.*$", "", body, flags=re.MULTILINE).strip()
        body = re.sub(r"\*End of practice test\.\*", "", body).strip()

        opt_matches = list(OPTION_RE.finditer(body))
        if not opt_matches:
            print(f"WARNING: Q{qnum} has no A)/B)/... options")
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


# Match: **Q12: B — Situation**   or   **Q12: B - Situation**
ANSWER_HEADER_RE = re.compile(
    r"^\*\*Q(\d+)\s*:\s*([A-E])\s*[—–-]\s*(.+?)\*\*\s*$",
    re.MULTILINE,
)
TOPIC_SKILL_RE = re.compile(
    r"^\*Topic\s+([\d.]+)\s*\|\s*Skill\s+([\d.A-Z]+)\*\s*$",
    re.MULTILINE,
)


def parse_answers(text):
    """Return dict keyed by question number → {letter, headline, explanation_md, topic, skill}."""
    out = {}
    headers = list(ANSWER_HEADER_RE.finditer(text))
    for i, m in enumerate(headers):
        qnum = int(m.group(1))
        letter = m.group(2)
        headline = m.group(3).strip()
        body_start = m.end()
        body_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = text[body_start:body_end].strip()

        # Pull out the *Topic X.Y | Skill N.A* footer if present.
        topic = skill = None
        ts = TOPIC_SKILL_RE.search(body)
        if ts:
            topic = ts.group(1)
            skill = ts.group(2)
            body = body[: ts.start()].rstrip()

        # Strip trailing horizontal rule and any "## Scoring Guide" / "## How to Review" tail.
        body = re.sub(r"\n---\s*$", "", body).strip()
        body = re.sub(r"\n##\s+(Scoring Guide|How to Review).*\Z", "", body, flags=re.DOTALL).strip()

        out[qnum] = {
            "letter": letter,
            "headline": headline,
            "explanation_md": body,
            "topic": topic,
            "skill": skill,
        }
    return out


def main():
    qtext = QUESTIONS_MD.read_text(encoding="utf-8")
    atext = ANSWERS_MD.read_text(encoding="utf-8")

    questions = parse_questions(qtext)
    answers = parse_answers(atext)

    records = []
    missing = []
    for q in questions:
        a = answers.get(q["n"])
        if not a:
            missing.append(q["n"])
            continue
        records.append({
            "id": f"q{q['n']:02d}",
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

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(
            {"questions": records, "total": len(records), "units": UNITS},
            f,
            indent=2,
            ensure_ascii=False,
        )

    by_unit = {}
    for r in records:
        by_unit[r["unit"]] = by_unit.get(r["unit"], 0) + 1

    print(f"Wrote {len(records)} questions to {OUTPUT.relative_to(ROOT)}")
    print("\nBy unit:")
    for u in sorted(UNITS):
        print(f"  Unit {u} ({UNITS[u]['label']}): {by_unit.get(u, 0)}")
    if missing:
        print(f"\nWARNING: {len(missing)} question(s) had no matching answer:")
        for n in missing:
            print(f"  - Q{n}")


if __name__ == "__main__":
    main()
