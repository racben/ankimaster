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
        
    prompt = f"""
    You are an adaptive Chinese-English dictionary for an advanced C1 Mandarin learner (native English speaker).
    User Input: {raw_input}
    
    TASK 1: EXTRACTION
    Identify the primary "target word" the user wants to learn from this input. 
    - It might be explicitly quoted (e.g., 「注销」, "节选信息").
    - It might just be the most difficult/salient C1-level word in a raw sentence (e.g., 熔断, 婆娑).
    - If the input is just a single word/phrase (e.g., "空集", "模式识别"), that is the target word.
    
    TASK 2: CARD GENERATION
    Analyze the target word and generate the back of a flashcard dynamically. Follow these conditional rules:
    1. TECHNICAL/MEDICAL/LOANWORDS (e.g., 模式识别, 胎盘, 空集): 
       Output the English equivalent. If it's a specific domain, add a tag like "数学用语。" Keep Chinese minimal.
    2. NUANCE & SYNONYMS (e.g., 注销, 节选): 
       Provide a concise Chinese definition. Then, briefly explain the difference between this word and a common near-synonym (e.g., "与「取消」的区别是...").
    3. LITERARY/RARE WORDS (e.g., 婆娑): 
       Include pinyin with tone marks. Provide the definition and a short usage note.
    4. POLYSEMY/CONTEXT-DEPENDENT (e.g., 注释, 清唱): 
       Explain the specific meaning in this context (e.g., "code comment" vs "footnote"). Use English if it's faster.
    5. PINYIN RULE: 
       Do NOT output pinyin unless the word falls under Rule 3 (rare/literary) or is easily mispronounced.
       
    Return a JSON object with EXACTLY four keys:
    "target": The extracted target word (no quotes/brackets).
    "context": The full context sentence. Leave completely EMPTY ("") if the user input was just a single isolated word.
    "front_hint": Optional. A short tag to put on the front of the card (e.g., "[数学]" or "[Context: logs]"). Leave empty if not needed.
    "back": The fully formatted text for the back of the card. Use HTML <br><br> tags for line breaks instead of \n.
    """
    
    client = OpenAI(api_key=OPENAI_API_KEY)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            response_format={ "type": "json_object" },
            messages=[{"role": "user", "content": prompt}]
        )
        return json.loads(response.choices.message.content)
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
