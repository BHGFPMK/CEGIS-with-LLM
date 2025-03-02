import requests
import json
import re
import os
import time
from CheckConstrains import run_plan


API_KEY = "replace it with your own API"
EXP_API_KEY = "replace it with your own API"
GPT_URL = "https://api.openai.com/v1/chat/completions"

# HTTP Head
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

EXP_HEADERS = {
    "Authorization": f"Bearer {EXP_API_KEY}",
    "Content-Type": "application/json"
}

def call_gpt(history, use_exp_api=False, model="gpt-4o", max_tokens=8000, temperature=0.7, top_p=0.9, timeout_limit=30):
    headers = EXP_HEADERS if use_exp_api else HEADERS  # select different API key

    payload = {
        "model": model,
        "messages": history,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p
    }

    try:
        start_time = time.time()
        response = requests.post(GPT_URL, json=payload, headers=headers, timeout=timeout_limit)
        end_time = time.time()

        print(f"HTTP code: {response.status_code}")
        print(f"API answer time: {end_time - start_time:.2f} 秒")

        if response.status_code != 200:
            print(f"API request failed: {response.text}")
            return f"ERROR: API request failed ({response.status_code})"

        response_data = response.json()

        if "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0]["message"]["content"]
        else:
            print("Invalid JSON structure")
            return "ERROR: Invalid JSON structure"

    except requests.exceptions.Timeout:
        print("API request timeout")
        return "ERROR: API request timeout"

    except requests.exceptions.RequestException as e:
        print(f"API request failed")
        return "ERROR: API request failed"

    except json.JSONDecodeError:
        print("ERROR: Invalid JSON format")
        return "ERROR: Invalid JSON format"
    
def call_answer_api(history):
    return call_gpt(history, use_exp_api=False)

def call_explanation_api(error_message):
    prompt = f"""
    You are a formal verification assistant specializing in the Blocks World problem.

    **Background:**
    The Blocks World is a classic AI planning problem where blocks are stacked on top of each other or placed on a table. A robot arm manipulates the blocks to achieve a goal state by following these rules:
    1. `unstack(x, y)`: Pick up block `x` from `y` if `x` is clear and the hand is empty.
    2. `put-down(x)`: Place block `x` on the table if the hand is holding `x`.
    3. `pick-up(x)`: Pick up block `x` from the table if `x` is clear, the hand is empty, and `x` is directly on the table.
    4. `stack(x, y)`: Stack block `x` on block `y` if `x` is in the hand and `y` is clear.

    Your task is to analyze the following **Blocks World error message** and provide a **clear explanation**.

    **Error Message:**
    {error_message}

    **Instructions:**
    - Explain the issue in plain language.
    - Identify which rule(s) were violated.
    - Provide a concrete example of how the error could have been avoided.
    - Do **not** generate a new plan, only explain why the previous plan failed.
    - Please keep your explanation concise.

    **Explanation:**
    """
    return call_gpt([{"role": "user", "content": prompt}], use_exp_api=True)

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

    max_history_length = 100

    while True:
        round_count += 1
        plan = call_answer_api(history)
        if plan is None:
            print("Fail to generate plans, retring")
            time.sleep(1)
            continue

        plan_text = format_plan_text(plan)
        print("\nGenerated Plan")
        print(plan)

        is_valid, message = run_plan(plan_text, blocks_file, goal_file)

        if is_valid:
            print("\n✅")
            print("It takes ", round_count, " round to generate creect answer.")
            break  
        else:
            print("\n❌")
            print("**Details for error(from Solver):**")
            print(message)

            explanation = call_explanation_api(message)
            print("\n**Details for error(from LLM):**")
            print(explanation)

            history.append({"role": "assistant", "content": plan_text})  
            history.append({"role": "user", "content": f"Your previous plan had an issue:\n{explanation}\nPlease correct your plan accordingly."})
            if len(history) > max_history_length:
                history = history[-max_history_length:]

        time.sleep(1)

if __name__ == "__main__":
    iterative_planning()