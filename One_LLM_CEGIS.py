import requests
import json
import re
import os
import time
from CheckConstrains import run_plan


API_KEY = "replace it with your own API"
GPT_URL = "https://api.openai.com/v1/chat/completions"

# HTTP Head
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def call_gpt_api(history, model="gpt-4o", max_tokens=8000, temperature=0.7, top_p=0.9, timeout_limit=30):

    payload = {
        "model": model,
        "messages": history,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p
    }

    try:
        # API Time
        start_time = time.time()
        response = requests.post(GPT_URL, json=payload, headers=HEADERS, timeout=timeout_limit)
        end_time = time.time()

        print(f"HTTP code: {response.status_code}")
        print(f"API answer time: {end_time - start_time:.2f} 秒")

        # Check API answer code
        if response.status_code != 200:
            print(f"API request failed: {response.text}")
            return f"ERROR: API request failed ({response.status_code})"

        response_data = response.json()

        if "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0]["message"]["content"]
        else:
            print("JSON Structure Invalid")
            return "ERROR: Invalid JSON structure"

    except requests.exceptions.Timeout:
        print("API request timeout")
        return "ERROR: API request timeout"

    except requests.exceptions.RequestException as e:
        print(f"API request failed")
        return "ERROR: API request failed"

    except json.JSONDecodeError:
        print("Invalid JSON format")
        return "ERROR: Invalid JSON format"

def format_plan_text(plan):

    if isinstance(plan, list):  
        return "\n".join(plan)

    if isinstance(plan, dict) and "plan" in plan:
        return "\n".join(plan["plan"])

    if isinstance(plan, str):
        plan = re.sub(r"```[\w]*\n([\s\S]*?)\n```", r"\1", plan)

        try:
            parsed_json = json.loads(plan)
            if isinstance(parsed_json, list):
                return "\n".join(parsed_json)
            if isinstance(parsed_json, dict) and "plan" in parsed_json:
                return "\n".join(parsed_json["plan"])
        except json.JSONDecodeError:
            pass

        return plan.strip()

    return str(plan).strip()

def iterative_planning(prompt_file="scenario/prompt.txt", blocks_file="scenario/initial.txt", goal_file="scenario/goal.txt"):

    with open(prompt_file, "r", encoding="utf-8") as file:
        initial_prompt = file.read()

    round_count = 0
    history = [{"role": "system", "content": "You are an expert planner for the Blocks World problem."}]
    history.append({"role": "user", "content": initial_prompt})

    while True:
        round_count += 1

        plan = call_gpt_api(history)
        if plan is None:
            print("Fail to generate plan, retring...")
            time.sleep(1)
            continue

        plan_text = format_plan_text(plan)
        print("\nGenerated Plan")
        print(plan)

        is_valid, message = run_plan(plan_text, blocks_file, goal_file)

        if is_valid:
            print("\n✅ ")
            print("It takes ", round_count, " rounds to generate creect answer.")
            break  
        else:
            print("\n❌ ")
            print("**Details for error:**")
            print(message)

            history.append({"role": "assistant", "content": plan_text})
            history.append({"role": "user", "content": f"Your previous plan had an issue:\n{message}\nPlease correct your plan accordingly."})

        time.sleep(1)

if __name__ == "__main__":
    iterative_planning()