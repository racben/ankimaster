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
DRY_RUN = True

# Your Anki Setup
ANKI_DECK = "Chinese"
ANKI_MODEL = "Chinese Basic"  # Change to "Basic" if your Note Type is literally named Basic
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
        print("Is Anki open and AnkiConnect installed?")
        sys.exit(1)

def get_ai_data(target, sentence):
    """Call OpenAI to dynamically classify and generate the card back"""
    print(f"🧠 Asking AI to evaluate: {target}")
    
    if DRY_RUN:
        return {
            "front_hint": "[测试]",
            "back": f"「{target}」这是一个测试卡片。\n\n英文: 'test card'"
        }
        
    prompt = f"""
    You are an adaptive Chinese-English dictionary for an advanced C1 Mandarin learner (native English speaker).
    Target word: {target}
    Context sentence (if any): {sentence}
    
    Analyze the target word and generate the back of a flashcard dynamically. Follow these conditional rules:
    
    1. TECHNICAL/MEDICAL/LOANWORDS (e.g., 模式识别, 胎盘, 空集): 
       Output the English equivalent. If it's a specific domain, add a tag like "数学用语。" Keep Chinese explanations extremely minimal or omit them entirely.
    2. NUANCE & SYNONYMS (e.g., 注销, 节选): 
       Provide a concise Chinese definition. Then, briefly explain the difference between this word and a common near-synonym (e.g., "与「取消」的区别是...").
    3. LITERARY/RARE WORDS (e.g., 婆娑): 
       Include pinyin with tone marks. Provide the definition and a short usage note in English or Chinese (e.g., "used for shadows/dancing").
    4. POLYSEMY/CONTEXT-DEPENDENT (e.g., 注释, 清唱): 
       Explain the specific meaning in this context (e.g., "code comment" vs "footnote"). Use English if it's faster.
    5. PINYIN RULE: 
       Do NOT output pinyin unless the word falls under Rule 3 (rare/literary) or is easily mispronounced.
       
    Return a JSON object with exactly two keys:
    "front_hint": Optional. A short tag to put on the front of the card (e.g., "[数学]" or "[Context: logs]"). Leave empty if not needed.
    "back": The fully formatted text for the back of the card. Use HTML <br><br> tags for line breaks instead of \n. Use standard formatting (e.g. 「」).
    """
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            response_format={ "type": "json_object" },
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.choices.message.content
        return json.loads(content)
        
    except Exception as e:
        print(f"❌ AI Text Error: {e}")
        return {"front_hint": "", "back": "Error generating card data."}

def main():
    if not DRY_RUN and OPENAI_API_KEY == "your_api_key_here":
        print("⚠️ Please set your OPENAI_API_KEY in the script or environment.")
        sys.exit(1)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        try:
            target, sentence = line.split('\t')
        except ValueError:
            print(f"⚠️ Skipping malformed line: {line}")
            continue

        print(f"\n" + "="*40)
        print(f"🎯 Target: {target}")
        print(f"📝 Context: {sentence}")
        print("="*40)
        
        # 1. Get Text Data
        ai_data = get_ai_data(target, sentence)
        
        print("\n✨ AI Generated Content:")
        print(json.dumps(ai_data, indent=2, ensure_ascii=False))
        print("-" * 40)
        
        # 2. Build the exact Front and Back field strings
        hint = ai_data.get("front_hint", "").strip()
        front_text = f"{target} {hint}".strip()
        
        # The AI now outputs <br> directly, so no string replacement is needed
        formatted_back = ai_data.get("back", "")
        
        # Assemble the full Back side
        full_back = f"<i>{sentence}</i><br><br><hr><br>{formatted_back}"
        
        # 3. Build the Anki Card payload mapped strictly to "Front" and "Back"
        note = {
            "deckName": ANKI_DECK,
            "modelName": ANKI_MODEL,
            "fields": {
                "Front": front_text,
                "Back": full_back
            },
            "options": {
                "allowDuplicate": False
            },
            "tags": ["ai"]
        }

        # 4. Push to Anki
        if DRY_RUN:
            print("🛑 [DRY RUN] Skipping Anki injection. Here is the final payload:")
            print(json.dumps(note["fields"], indent=2, ensure_ascii=False))
            continue
            
        print(f"📥 Pushing to Anki...")
        anki_id = anki_invoke("addNote", note=note)
        
        if anki_id:
            print(f"✅ Card created successfully! (ID: {anki_id})\n")

if __name__ == "__main__":
    main()
