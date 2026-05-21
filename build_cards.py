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
ANKI_MODEL = "Chinese Animecards"  # Updated to Animecards format
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
    """Call OpenAI to get the definition and explanation"""
    print(f"🧠 Asking AI for definition of: {target}")
    
    if DRY_RUN:
        return {
            "definition": f"[MOCK] 这是一个测试定义 (Definition for {target}).",
            "explanation": f"[MOCK] 这是一个测试解释 (Explanation of {target} in context)."
        }

    prompt = f"""
    You are an ultra-minimalist Chinese flashcard generator for an advanced C1 learner.
    Target word: {target}
    Context sentence: {sentence}
    
    Return a JSON object with exactly three keys:
    "pinyin": The pinyin for the target word using standard tone marks.
    "definition": A very concise but still clear definition of the target word, written in mandarin suitable for a C1 learner. Do not use the target word's component characters in the definition itself.
    *SPECIAL RULE*: If the word is a specialized technical term (like '空集'), prefix the definition with its domain (e.g., '数学用语。') and include the English equivalent in parentheses at the end. Do NOT do this for common words.
    "explanation": Further explanation, also in Mandarin, anything relevant to elucidating the word in contetx
    """     
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Standardizing to current stable mini model
            response_format={ "type": "json_object" },
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        print(f"❌ AI Text Error: {e}")
        return {"definition": "Error generating definition", "explanation": "Error"}

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
        print(f"🎯 Processing: {target}")
        print(f"📝 Context: {sentence}")
        print("="*40)
        
        # 1. Get Text Data
        ai_data = get_ai_data(target, sentence)
        
        # ALWAYS print the AI's output so you can audit it
        print("\n✨ AI Generated Content:")
        print(json.dumps(ai_data, indent=2, ensure_ascii=False))
        print("-" * 40)
        
        # 2. Build the Anki Card payload
        note = {
            "deckName": ANKI_DECK,
            "modelName": ANKI_MODEL,
            "fields": {
                "Expression": target,
                "Sentence": sentence,
                "Reading": ai_data.get("pinyin", ""),
                "Explanation": ai_data.get("definition", ""),
                "Notes": ai_data.get("explanation", ""),
                "Hint": ""
            },
            "options": {
                "allowDuplicate": False
            },
            "tags": ["ai"]  # Updated tag
        }

        # 3. Push to Anki
        if DRY_RUN:
            print("🛑 [DRY RUN] Skipping Anki injection. Process completed safely.\n")
            continue

        print(f"📥 Pushing to Anki...")
        anki_id = anki_invoke("addNote", note=note)

        if anki_id:
            print(f"✅ Card created successfully! (ID: {anki_id})\n")

if __name__ == "__main__":
    main()
