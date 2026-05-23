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

def get_ai_data(raw_input):
    """Call OpenAI to extract the target and generate the card back"""
    print(f"🧠 Asking AI to process: {raw_input}")
    
    if DRY_RUN:
        return {
            "target": "测试词",
            "context": raw_input,
            "front_hint": "[测试]",
            "back": f"「测试词」的解释。<br><br>英文: 'test word'"
        }
        
    prompt = """

    You are an adaptive Chinese-English dictionary and flashcard generator for an advanced C1 Mandarin learner whose native language is English.

    User Input:

    {raw_input}

    ====================

    TASK 1 — TARGET EXTRACTION

    ====================

    Identify ONE primary target word or phrase the user most likely wants to learn.

    Priority rules:

    1. If a word/expression is explicitly quoted or bracketed, use that.

    2. If the input is a sentence, select the most advanced, unusual, technical, literary, or contextually important word.

    3. If the input is already a standalone word/phrase, use it directly.

    4. Prefer:

    - uncommon vocabulary

    - domain-specific terminology

    - literary/chengyu-style wording

    - words with nuanced usage

    5. Avoid selecting:

    - basic grammar

    - very common function words

    - names unless linguistically important

    ====================

    TASK 2 — CARD GENERATION

    ====================

    Generate the flashcard back dynamically according to the word type.

    CLASSIFICATION RULES:

    A. TECHNICAL / SCIENTIFIC / ACADEMIC TERMS

    Examples: 空集, 胎盘, 模式识别

    Format:

    - English equivalent first

    - Brief Chinese clarification only if needed

    - Add domain tag when relevant

    Example style:

    “empty set。数学用语。”

    B. NUANCED EVERYDAY WORDS / NEAR-SYNONYMS

    Examples: 注销, 节选, 推脱

    Format:

    1. concise Chinese definition

    2. short contrast with a common synonym, if and only if it is a commonly
    confused word

    Example style:

    “正式取消并使失效。<br><br>

    与「取消」相比，更强调记录、资格或账户被正式作废。”

    C. LITERARY / RARE / IDIOMATIC WORDS

    Examples: 婆娑, 氤氲

    Format:

    1. pinyin with tone marks

    2. concise definition

    3. short usage or register note

    Example style:

    “pó suō<br><br>

    形容盘旋起舞、枝叶摇曳等优美姿态。<br><br>

    多用于文学描写。”

    D. CONTEXT-DEPENDENT / POLYSEMIC WORDS

    Examples: 注释, 清唱

    Format:

    - Explain the meaning specifically in THIS context

    - English is acceptable if clearer/faster

    - Mention alternate meaning only if important

    Example style:

    “In this context, 注释 means ‘code comments’, not footnotes or annotations in a book.”

    ====================

    PINYIN RULE

    ====================

    Do NOT include pinyin unless:

    - the word is literary/rare

    - pronunciation is genuinely non-obvious

    - the word is commonly misread

    ====================

    STYLE RULES

    ====================

    - Be concise. And then be even more concise.

    - Avoid dictionary overload.

    - Prefer learner usefulness over completeness.

    - Maximum length for "back": ~80 English words OR ~120 Chinese characters.

    - Do not include numbered lists.

    - Use natural learner-facing explanations, not academic dictionary prose.

    - Use HTML <br><br> for line breaks.

    - Do not use markdown.

    ====================

    OUTPUT FORMAT

    ====================

    Return EXACTLY this JSON schema:

    {

    "target": "...",

    "context": "...",

    "front_hint": "...",

    "back": "..."

    }

    FIELD RULES:

    - "target": extracted target word only, no quotes/brackets

    - "context": full original sentence if applicable; otherwise ""

    - "front_hint": short optional tag like "[数学]" or "[代码]"; otherwise ""

    - "back": formatted flashcard back using HTML line breaks

    """
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        response = client.chat.completions.create(
            model="gpt-5.4", 
            response_format={ "type": "json_object" },
            messages=[{"role": "user", "content": prompt}]
        )
        # THE BUG WAS HERE: Added so Python extracts the message properly!
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ AI Text Error: {e}")
        return {"target": "Error", "context": "", "front_hint": "", "back": "Error"}

def main():
    if not DRY_RUN and OPENAI_API_KEY == "your_api_key_here":
        print("⚠️ Please set your OPENAI_API_KEY in the script or environment.")
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        print(f"\n" + "="*40)
        
        # Pass the raw string directly to the AI
        ai_data = get_ai_data(line)
        
        print("✨ AI Generated Content:")
        print(json.dumps(ai_data, indent=2, ensure_ascii=False))
        print("-" * 40)
        
        target = ai_data.get("target", "").strip()
        context = ai_data.get("context", "").strip()
        hint = ai_data.get("front_hint", "").strip()
        formatted_back = ai_data.get("back", "")
        
        front_text = f"{target} {hint}".strip()
        
        # Only add the context string to the back if the AI determined one existed
        if context:
            full_back = f"<i>{context}</i><br><br><hr><br>{formatted_back}"
        else:
            full_back = formatted_back
            
        note = {
            "deckName": ANKI_DECK,
            "modelName": ANKI_MODEL,
            "fields": {
                "Front": front_text,
                "Back": full_back
            },
            "options": {"allowDuplicate": False},
            "tags": ["ai"]
        }

        if DRY_RUN:
            print("🛑 [DRY RUN] Final Anki fields preview:")
            print(f"Front: {note['fields']['Front']}")
            print(f"Back:  {note['fields']['Back']}\n")
            continue
            
        # print(f"📥 Pushing to Anki...")
        # anki_id = anki_invoke("addNote", note=note)
        
        # if anki_id:
        #     print(f"✅ Card created successfully! (ID: {anki_id})\n")

if __name__ == "__main__":
    main()
