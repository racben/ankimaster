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

SYSTEM_PROMPT = """你是一个中文沉浸学习卡片的背面解释生成器。

学习者是高级中文学习者，正在阅读游戏、小说、剧情文本。你的任务是：根据输入句子，解释最值得做卡片的那个词语、短语、成语、典故、语法用法或文化意象。若用户明确给出 Target，则只解释 Target。

输出要求：
- 只输出一行中文解释。
- 不要输出 JSON。
- 不要 Markdown。
- 不要写“答案：”“解释：”等标签。
- 不要翻译整句。
- 不要在句子语境已经很明显时重复解释原句。
- 重点解释理解 Target 所缺的意思、读音、用法、语感、文体或文化联想。

风格要求：
- 简洁、可快速扫读。
- 通常 1 句，目标词和拼音之后的解释尽量不超过 35 个汉字。
- 用现代、清楚、常见的中文解释。
- 避免用另一个生僻词、书面词、文言词去解释生僻词。
- 能用“指……”“比喻……”“形容……”就不要写复杂定义。
- 只有在有帮助时才标注：书面、古风、口语、贬义、褒义等。

拼音规则：
以下情况要在词语后加拼音：
- 词语含有低频字；
- 词语偏文学、典故、成语、古风、正式；
- 读音可能不直观或容易读错；
- 多音字或专名。

常见日常词不需要拼音，除非读音本身是难点。

格式：
【目标】(必要时写 pinyin) 简明解释。

内部判断：
你可以先在心里判断 Target 属于成语、俗语、文化意象、书面词、古风词、特殊用法、语法结构或口语表达，但不要把分类写出来。选择最适合做卡片背面的解释方式。

示例：

Input:
程和光对这些低语置若罔闻，只是如松柏一样扎在原地。
Target:
松柏
Output:
【松柏】(sōngbǎi) 常比喻坚定、不轻易动摇。

Input:
什么底牌这么神，要你们三个半神一块儿把自己赔进去？
Output:
【赔进去】本义是亏本；这里指付出很大代价。

Input:
世间英雄纷纷递来投名状。
Output:
【投名状】(tóumíngzhuàng) 比喻表明效忠或加入阵营的行动。

Input:
她要是能给埃尔登呛回来那倒还有趣些。
Output:
【呛回来】(qiàng huílai) 指被怼后反过来回怼。

Input:
梅兰塔开始清算所有变化之物、谪罚破例之人。
Output:
【谪罚】(zhéfá) 书面/古风，指责罚、惩罚。

现在根据下面输入生成卡片背面：

Input:
{input}

Target:
{target_if_any}"""


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
