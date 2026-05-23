# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai",
#     "requests",
# ]
# ///

import sys
import json
import requests
import os
from openai import OpenAI

# ================= CONFIGURATION =================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your_api_key_here")

# Set to True for a safe test run. Change to False to unleash live APIs and Anki.
DRY_RUN = False

# Your Anki Setup
ANKI_DECK = "Chinese"
ANKI_MODEL = "Chinese Basic" 
# =================================================

def anki_invoke(action, **params):
    """Send a command to local AnkiConnect"""
    payload = {"action": action, "version": 6, "params": params}
    try:
        response = requests.post("http://localhost:8765", json=payload).json()
        if response.get("error"):
            print(f"❌ AnkiConnect Error: {response['error']}")
            return None
        return response.get("result")
    except Exception as e:
        print(f"❌ Failed to connect to Anki: {e}")
        sys.exit(1)

def get_ai_explanation(user_input_line):
    """Call OpenAI using the dynamic diagnostic protocol"""
    print(f"🧠 Diagnostic processing: {user_input_line}")
    
    if DRY_RUN:
        return {
            "target": "测试词",
            "explanation": "【测试词】本义：演示 -> 本句：用于模拟脚本运行。"
        }

    system_prompt = """
    You are the backend engine for a C1-level Mandarin immersion flashcard pipeline. 
    Your job is to analyze the target sentence, isolate the single primary "friction point" (the blind spot), and generate a highly concise, context-aware explanation.

    CRITICAL PROCESSING RULES:
    1. Prioritize User Hints: The user may provide optional English hints or context following the sentence (e.g., "Confused about the usage of X"). You MUST use this hint to instantly determine the friction point and tailor your explanation directly to it.
    2. No Fluff: Do not include conversational filler. Keep all descriptions strictly in Mandarin, concise, and scannable in under 5 seconds.
    3. Strict Isolation: Choose ONLY the ONE specific format block below that best addresses the friction point. Do not combine formats.
    4. Do not use markdown (no asterisks, backticks, or markdown bold).

    ### DIAGNOSTIC PROTOCOL:

    Type 1: Idiom / Slang (Simple metaphor)
    - Format: 【[Word]】[Brief definition]
    - Example Input: 林宇瞪大了眼睛使出吃奶的劲儿
    - Example Output: 【吃奶的劲儿】比喻用尽全身所有的力气。

    Type 2: Historical / Cultural Concept (Abstract metaphor)
    - Format: 【[Word]】[Historical origin] -> [What it means metaphorically in this exact sentence].
    - Example Input: 自陛下颁布逐火号令，世间英雄纷纷递来投名状
    - Example Output: 【投名状】古代加入忠诚集团时写的保证书 -> 这里隐喻表示效忠、加入阵营的决心。

    Type 3: Rare / Archaic / Literary Word (Recherché)
    - Format: 【[Word]】([Pinyin]) [Register Note]。同义词：[Common Word]。
    - Example Input: 梅兰塔开始清算所有变化之物、谪罚破例之人。
    - Example Output: 【谪罚】(zhéfá) 书面语/古风。谴责并惩罚。同义词：惩罚。

    Type 4: Familiar Word, Unfamiliar Usage (Contextual Shift)
    - Format: 【[Word]】本义：[Normal meaning] -> 本句：[How it is used here].
    - Example Input: 什么底牌这么神，要你们三个半神一块儿把自己赔进去？
    - Example Output: 【赔进去】本义：做生意亏本 -> 本句：付出惨痛代价、把命搭进去。

    Type 5: General Friction / Ambiguity (Fallback)
    - Instruction: Use this ONLY if the difficulty does not fit Types 1-4. Identify the single trickiest element (grammar twist, tone, or word combination) and explain it directly.
    - Format: 【核心难点】[The specific word/phrase/structure] -> [Direct, concise explanation in Mandarin].

    ### OUTPUT FORMAT:
    Return EXACTLY this JSON schema:
    {
      "target": "The isolated word or phrase causing the friction",
      "explanation": "The strict single-line output generated from the protocol step above"
    }
    """

    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.5", 
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Input: {user_input_line}"}
            ],
            temperature=0.3
        )
        return json.loads(response.choices.message.content)
    except Exception as e:
        print(f"❌ AI Text Error: {e}")
        return {"target": "Error", "explanation": "处理失败"}

def main():
    if not DRY_RUN and OPENAI_API_KEY == "your_api_key_here":
        print("⚠️ Please set your OPENAI_API_KEY in the script or environment.")
        sys.exit(1)

    print("🚀 Flashcard Pipeline Ready. Paste your text line-by-line via standard input:")
    
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        print(f"\n" + "="*40)
        
        # Get structured breakdown from AI
        ai_data = get_ai_explanation(line)
        
        print("✨ AI Generated Content:")
        print(json.dumps(ai_data, indent=2, ensure_ascii=False))
        print("-" * 40)
        
        target = ai_data.get("target", "").strip()
        explanation = ai_data.get("explanation", "").strip()
        
        # AJATT/Sentence Mining Format: Full input line on Front, explanation on Back
        front_text = line
        back_text = explanation
            
        note = {
            "deckName": ANKI_DECK,
            "modelName": ANKI_MODEL,
            "fields": {
                "Front": front_text,
                "Back": back_text
            },
            "options": {"allowDuplicate": False},
            "tags": ["ai_immersion"]
        }

        if DRY_RUN:
            print("🛑 [DRY RUN] Final Anki fields preview:")
            print(f"Front: {note['fields']['Front']}")
            print(f"Back:  {note['fields']['Back']}\n")
            continue
            
        print(f"📥 Pushing to Anki...")
        anki_id = anki_invoke("addNote", note=note)
        
        if anki_id:
            print(f"✅ Card created successfully! (ID: {anki_id})\n")

if __name__ == "__main__":
    main()
