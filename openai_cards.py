# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai>=1.0.0",
#     "requests>=2.31.0",
# ]
# ///
"""
Create concise Chinese flashcard back-side explanations from stdin.

Default mode prints one explanation per input line. Add --anki to create notes via
AnkiConnect. This is meant to be the card-back generation stage in a CLI pipeline.

Examples:
  echo '雅典的屋顶之间，从来都是如此遥远的天堑么？' | python openai_card_back.py

  cat lines.txt | python openai_card_back.py --tsv > cards.tsv

  echo '日志显示：「吕枯耳戈斯」注销了管理员权限。' | \
    python openai_card_back.py --anki --deck Chinese --note-type "Chinese Basic"
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass

import requests
from typing import Any


DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")
ANKI_CONNECT_URL = os.environ.get("ANKI_CONNECT_URL", "http://localhost:8765")

SYSTEM_PROMPT = """你是高级中文学习者的闪卡背面生成器。

任务：根据输入句子，找出最值得解释的一个难点，并只输出一条简洁中文解释。

规则：
1. 如果输入里有英文提示或“想问 X / confused about X”之类说明，优先解释用户提示的点。
2. 只解释一个核心难点，不列多个候选。
3. 不输出 JSON，不输出 target 字段，不写寒暄，不用 Markdown。
4. 输出必须是一行，适合作为 Anki 背面。
5. 解释要让 C1 左右中文学习者 3–5 秒内看懂；可标注“书面语/古风/口语/贬义”等。

优先格式：
- 成语/俗语： 【词语】简明释义。
- 文化/典故： 【词语】来源/本义 -> 本句含义。
- 生僻/文言/书面词： 【词语】(拼音) 语域。释义/近义词。
- 熟词新义： 【词语】本义：…… -> 本句：……。
- 语法/搭配难点： 【核心难点】结构/搭配 -> 具体含义。

例：
输入：什么底牌这么神，要你们三个半神一块儿把自己赔进去？
输出：【赔进去】本义：做生意亏本 -> 本句：付出惨痛代价、把自己也搭进去。
"""


@dataclass(frozen=True)
class Config:
    model: str
    api_key: str | None
    dry_run: bool
    anki: bool
    deck: str
    note_type: str
    front_field: str
    back_field: str
    tag: str
    tsv: bool
    verbose: bool


def anki_invoke(action: str, **params):
    """Send one command to local AnkiConnect."""
    payload = {"action": action, "version": 6, "params": params}
    try:
        r = requests.post(ANKI_CONNECT_URL, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Could not connect to AnkiConnect at {ANKI_CONNECT_URL}: {e}") from e
    except ValueError as e:
        raise RuntimeError("AnkiConnect returned non-JSON data. Is AnkiConnect running?") from e

    if data.get("error"):
        raise RuntimeError(f"AnkiConnect error for {action}: {data['error']}")
    return data.get("result")


def explain_with_openai(client: Any, model: str, sentence: str) -> str:
    """Return a single-line explanation suitable for an Anki Back field."""
    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=f"输入：{sentence}",
        text={"verbosity": "low"},
    )
    text = (response.output_text or "").strip()
    return " ".join(text.splitlines()).strip()


def fake_explanation(sentence: str) -> str:
    """Offline preview for testing the CLI/Anki plumbing."""
    return "【测试】离线预览：这里会替换成 AI 生成的简洁背面解释。"


def create_anki_note(cfg: Config, front: str, back: str) -> int | None:
    note = {
        "deckName": cfg.deck,
        "modelName": cfg.note_type,
        "fields": {
            cfg.front_field: front,
            cfg.back_field: back,
        },
        "options": {"allowDuplicate": False},
        "tags": [cfg.tag] if cfg.tag else [],
    }
    return anki_invoke("addNote", note=note)


def parse_args(argv: list[str]) -> Config:
    p = argparse.ArgumentParser(
        description="Generate concise Chinese Anki back-field explanations from stdin."
    )
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"OpenAI model, default: {DEFAULT_MODEL}")
    p.add_argument("--dry-run", action="store_true", help="Do not call OpenAI; use fake output.")
    p.add_argument("--anki", action="store_true", help="Create Anki notes with AnkiConnect.")
    p.add_argument("--deck", default="Chinese", help="Anki deck name.")
    p.add_argument("--note-type", default="Chinese Basic", help="Anki note type/model name.")
    p.add_argument("--front-field", default="Front", help="Anki field for the source sentence.")
    p.add_argument("--back-field", default="Back", help="Anki field for the generated explanation.")
    p.add_argument("--tag", default="ai_immersion", help="Tag to add to created Anki notes; empty disables tags.")
    p.add_argument("--tsv", action="store_true", help="Print Front<TAB>Back for each input line.")
    p.add_argument("--verbose", action="store_true", help="Print progress to stderr.")
    args = p.parse_args(argv)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not args.dry_run and not api_key:
        p.error("OPENAI_API_KEY is not set. Export it or use --dry-run.")

    return Config(
        model=args.model,
        api_key=api_key,
        dry_run=args.dry_run,
        anki=args.anki,
        deck=args.deck,
        note_type=args.note_type,
        front_field=args.front_field,
        back_field=args.back_field,
        tag=args.tag,
        tsv=args.tsv,
        verbose=args.verbose,
    )


def main(argv: list[str] | None = None) -> int:
    cfg = parse_args(argv or sys.argv[1:])
    if cfg.dry_run:
        client = None
    else:
        from openai import OpenAI
        client = OpenAI(api_key=cfg.api_key)

    had_error = False
    for raw_line in sys.stdin:
        front = raw_line.strip()
        if not front:
            continue

        try:
            if cfg.verbose:
                print(f"Processing: {front}", file=sys.stderr)

            back = fake_explanation(front) if cfg.dry_run else explain_with_openai(client, cfg.model, front)  # type: ignore[arg-type]
            if not back:
                raise RuntimeError("OpenAI returned an empty explanation.")

            if cfg.anki:
                note_id = create_anki_note(cfg, front, back)
                if cfg.verbose:
                    print(f"Created Anki note: {note_id}", file=sys.stderr)

            if cfg.tsv:
                print(f"{front}\t{back}")
            else:
                print(back)

        except Exception as e:
            had_error = True
            print(f"ERROR for input {front!r}: {e}", file=sys.stderr)

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
