from z3 import *
import os

from DefineState import define_state

class State:
    def __init__(self, name):
        self.name = name
        self.table = Function(f'{name}_table', IntSort(), BoolSort())
        self.hand = Function(f'{name}_hand', IntSort(), BoolSort())
        self.stacked = Function(f'{name}_stacked', IntSort(), IntSort(), BoolSort())
        self.clear = Function(f'{name}_clear', IntSort(), BoolSort())
        self.handsfree = Function(f'{name}_handsfree', BoolSort())

def print_state(state, solver, num_blocks):

    if solver.check() == sat:
        model = solver.model()
        print(f"--- State {state.name} ---")
        for i in range(1, num_blocks + 1):
            print(f"table({i}) = {model.eval(state.table(i), model_completion=True)}")
            print(f"hand({i}) = {model.eval(state.hand(i), model_completion=True)}")
            print(f"clear({i}) = {model.eval(state.clear(i), model_completion=True)}")
        print(f"handsfree = {model.eval(state.handsfree(), model_completion=True)}")
    else:
        print("State is unsat.")

def parse_plan(plan_text):

    actions = []
    for line in plan_text.split("\n"):
        line = line.strip()
        if not line or "(" not in line or ")" not in line:
            continue
        action = line.split("(")[0].strip()
        params = line.split("(")[1].split(")")[0].replace(" ", "").split(",")
        #print(f"Parsed action: {action}, Params: {params}")
        actions.append((action, *params))
    return actions

def inherit_state(current, next_state, solver, num_blocks, affected=None):

    if affected is None:
        affected = {}
    for i in range(1, num_blocks + 1):
        if 'table' not in affected or i not in affected.get('table', []):
            solver.add(next_state.table(i) == current.table(i))
        if 'hand' not in affected or i not in affected.get('hand', []):
            solver.add(next_state.hand(i) == current.hand(i))
        if 'clear' not in affected or i not in affected.get('clear', []):
            solver.add(next_state.clear(i) == current.clear(i))
        for j in range(1, num_blocks + 1):
            if 'stacked' not in affected or (i, j) not in affected.get('stacked', []):
                solver.add(next_state.stacked(i, j) == current.stacked(i, j))
    if 'handsfree' not in affected:
        solver.add(next_state.handsfree() == current.handsfree())

def apply_action(current_state, action_tuple, solver, step, num_blocks):
    action, *params = action_tuple
    params = list(map(int, params))
    next_state = State(f"s{step}")
    num_blocks = num_blocks
    
    if action == "unstack":
        if len(params) != 2:
            print(f"Error: Invalid format for action '{action_tuple}'")
            return None
        i, j = params

        affected = {
            'hand': [i],
            'stacked': [(i, j)],
            'clear': [i, j],
            'table': [],    
            'handsfree': True
        }
        inherit_state(current_state, next_state, solver, num_blocks, affected)

        solver.assert_and_track(current_state.clear(i) == True, f"pre_unstack_clear_step_{step}_block_{i}")
        solver.assert_and_track(current_state.table(i) == False, f"pre_unstack_not_table_step_{step}_block_{i}")
        solver.assert_and_track(current_state.stacked(i, j) == True, f"pre_unstack_stacked_step_{step}_block_{i}_{j}")
        solver.assert_and_track(current_state.handsfree() == True, f"pre_unstack_handsfree_step_{step}")

        solver.assert_and_track(next_state.hand(i) == True, f"post_unstack_hand_step_{step}_block_{i}")
        solver.assert_and_track(next_state.stacked(i, j) == False, f"post_unstack_not_stacked_step_{step}_block_{i}_{j}")
        solver.assert_and_track(next_state.handsfree() == False, f"post_unstack_not_handsfree_step_{step}")
        solver.assert_and_track(next_state.clear(j) == True, f"post_unstack_clear_step_{step}_block_{j}")
        solver.assert_and_track(next_state.clear(i) == False, f"post_unstack_not_clear_step_{step}_block_{i}")

    elif action == "stack":
        if len(params) != 2:
            print(f"Error: Invalid format for action '{action_tuple}'")
            return None
        i, j = params

        affected = {
            'hand': [i],
            'stacked': [(i, j)],
            'clear': [i, j],
            'table': [],
            'handsfree': True
        }
        inherit_state(current_state, next_state, solver, num_blocks, affected)

        solver.assert_and_track(current_state.hand(i) == True, f"pre_stack_hand_step_{step}_block_{i}")
        solver.assert_and_track(current_state.handsfree() == False, f"pre_stack_not_handsfree_step_{step}")
        solver.assert_and_track(current_state.clear(j) == True, f"pre_stack_clear_step_{step}_block_{j}")

        solver.assert_and_track(next_state.stacked(i, j) == True, f"post_stack_stacked_step_{step}_block_{i}_{j}")
        solver.assert_and_track(next_state.hand(i) == False, f"post_stack_not_hand_step_{step}_block_{i}")
        solver.assert_and_track(next_state.handsfree() == True, f"post_stack_handsfree_step_{step}")
        solver.assert_and_track(next_state.clear(j) == False, f"post_stack_not_clear_step_{step}_block_{j}")
        solver.assert_and_track(next_state.clear(i) == True, f"post_stack_clear_step_{step}_block_{i}")

    elif action == "pick-up":
        if len(params) != 1:
            print(f"Error: Invalid format for action '{action_tuple}'")
            return None
        i = params[0]

        affected = {
            'table': [i],
            'hand': [i],
            'handsfree': True
        }
        inherit_state(current_state, next_state, solver, num_blocks, affected)

        solver.assert_and_track(current_state.table(i) == True, f"pre_pickup_table_step_{step}_block_{i}")
        solver.assert_and_track(current_state.handsfree() == True, f"pre_pickup_handsfree_step_{step}")
        solver.assert_and_track(current_state.clear(i) == True, f"pre_pickup_clear_step_{step}_block_{i}")

        solver.assert_and_track(next_state.hand(i) == True, f"post_pickup_hand_step_{step}_block_{i}")
        solver.assert_and_track(next_state.handsfree() == False, f"post_pickup_not_handsfree_step_{step}")
        solver.assert_and_track(next_state.table(i) == False, f"post_pickup_not_table_step_{step}_block_{i}")

    elif action == "put-down":
        if len(params) != 1:
            print(f"Error: Invalid format for action '{action_tuple}'")
            return None
        i = params[0]
        affected = {
            'table': [i],
            'hand': [i],
            'clear': [i],
            'handsfree': True
        }
        inherit_state(current_state, next_state, solver, num_blocks, affected)

        solver.assert_and_track(current_state.hand(i) == True, f"pre_putdown_hand_step_{step}_block_{i}")
        solver.assert_and_track(current_state.handsfree() == False, f"pre_putdown_not_handsfree_step_{step}")

        solver.assert_and_track(next_state.table(i) == True, f"post_putdown_table_step_{step}_block_{i}")
        solver.assert_and_track(next_state.hand(i) == False, f"post_putdown_not_hand_step_{step}_block_{i}")
        solver.assert_and_track(next_state.handsfree() == True, f"post_putdown_handsfree_step_{step}")
        solver.assert_and_track(next_state.clear(i) == True, f"post_putdown_clear_step_{step}_block_{i}")

    else:
        print(f"Error: Unknown action '{action}'")
        return None

    if solver.check() == sat:
        #print(f"Action '{action_tuple}' is valid at step {step}.")
        return next_state
    else:
        #print(f"Action '{action_tuple}' is invalid at step {step}.")
        return None

def generate_feedback(failed_step, actions, core):

    failed_action = actions[failed_step-1][0]
    failed_block = actions[failed_step-1][1]

    feedback = f"""
    **Invalid Action Detected at Step {failed_step}**
    The action `{actions[failed_step-1]}` is invalid in the current state.

    **Issue Explanation**
    This action violates one or more preconditions required for execution.
    UNSAT Core: {core}
    """

    if failed_action == "pick-up":
        feedback += f"""
    **Why is this incorrect?**
    - The block `{failed_block}` is **not clear or not on the table**.
    - `pick-up(i)` requires that:
      1. `{failed_block}` is **clear** (no blocks on top of it).
      2. `{failed_block}` is **directly on the table**.

    **How to fix this?**
    - If `{failed_block}` is **not clear**, first remove any block stacked on it.
    - If `{failed_block}` is **not on the table**, you must `unstack({failed_block}, X)` first, then `put-down({failed_block})`.

    **Example Correction**
    ```plaintext
    unstack({failed_block}, X)  # First, remove it from another block
    put-down({failed_block})     # Place it on the table
    pick-up({failed_block})      # Now, it is clear and on the table
    ```
    """

    elif failed_action == "unstack":
        feedback += f"""
    **Why is this incorrect?**
    - `{failed_block}` **is not stacked on `{actions[failed_step-1][2]}`**.
    - `unstack(x, y)` requires that:
      1. `x` must be **clear** (no block on top).
      2. `x` must **not be on the table** (i.e., it should be stacked on `y`).
      3. The robot's hand must be **empty** before unstacking.

    **How to fix this?**
    - Ensure that `{failed_block}` is actually stacked on `{actions[failed_step-1][2]}` before attempting `unstack({failed_block}, {actions[failed_step-1][2]})`.
    - If `{failed_block}` is already on the table, use `pick-up({failed_block})` instead.

    **Example Correction**
    ```plaintext
    # If `{failed_block}` is on the table, do this instead:
    pick-up({failed_block})  

    # If `{failed_block}` is not clear, first remove its top block:
    unstack(top_block, {failed_block})  
    ```
    """

    elif failed_action == "stack":
        feedback += f"""
    **Why is this incorrect?**
    - `{failed_block}` **cannot be stacked on `{actions[failed_step-1][2]}`** because:
      1. `{actions[failed_step-1][2]}` is **not clear**.
      2. `{failed_block}` is **not in the robot's hand**.
    
    **How to fix this?**
    - If `{actions[failed_step-1][2]}` is not clear, first remove any block stacked on it.
    - Ensure that `{failed_block}` is picked up before attempting to stack it.

    **Example Correction**
    ```plaintext
    # If `{actions[failed_step-1][2]}` is not clear:
    unstack(top_block, {actions[failed_step-1][2]})

    # If `{failed_block}` is not in hand:
    pick-up({failed_block})
    stack({failed_block}, {actions[failed_step-1][2]})
    ```
    """


    elif failed_action == "put-down":
        feedback += f"""
    **Why is this incorrect?**
    - `{failed_block}` **cannot be put down** because:
      1. The robot **is not holding `{failed_block}`**.
      2. `{failed_block}` **is not picked up yet**.
    
    **How to fix this?**
    - Ensure that `{failed_block}` is in hand before using `put-down({failed_block})`.

    **Example Correction**
    ```plaintext
    pick-up({failed_block})  
    put-down({failed_block})  
    ```
    """

    return feedback


def run_plan(plan_text, blocks_file="blocks.txt", goal_file="goal.txt"):

    is_valid = False

    solver = Solver()

    initial_state, num_blocks = define_state(solver, blocks_file, "s0")

    if os.path.exists(goal_file):
        goal_state, _ = define_state(solver, goal_file, "goal")
    else:
        goal_state = None

    states = [initial_state]
    all_blocks = list(range(1, num_blocks + 1))

    actions = parse_plan(plan_text)
    current_state = initial_state
    step = 1

    for action in actions:
        new_state = apply_action(current_state, action, solver, step, num_blocks)
        if new_state is None:
            print("Plan failed.")
            break
        else:
            states.append(new_state)
            current_state = new_state
            #print(f"\n=== State after action {action} (step {step}) ===")
            #print_state(current_state, solver, num_blocks)
            step += 1

    #print("\n=== Final State ===")

    if solver.check() == sat:
        #print_state(current_state, solver, num_blocks)

        mismatches = []

        if goal_state:
            print("\nChecking if Final State Matches Goal State:")

            model = solver.model()
            for i in all_blocks:
                table_final = model.eval(current_state.table(i), model_completion=True)
                table_goal = model.eval(goal_state.table(i), model_completion=True)
                if not (table_final == table_goal):
                    mismatches.append(f"table({i}) mismatch: Final({table_final}) ≠ Goal({table_goal})")

                hand_final = model.eval(current_state.hand(i), model_completion=True)
                hand_goal = model.eval(goal_state.hand(i), model_completion=True)
                if not (hand_final == hand_goal):
                    mismatches.append(f"hand({i}) mismatch: Final({hand_final}) ≠ Goal({hand_goal})")

                clear_final = model.eval(current_state.clear(i), model_completion=True)
                clear_goal = model.eval(goal_state.clear(i), model_completion=True)
                if not (clear_final == clear_goal):
                    mismatches.append(f"clear({i}) mismatch: Final({clear_final}) ≠ Goal({clear_goal})")

            handsfree_final = model.eval(current_state.handsfree(), model_completion=True)
            handsfree_goal = model.eval(goal_state.handsfree(), model_completion=True)
            if not (handsfree_final == handsfree_goal):
                mismatches.append(f"handsfree mismatch: Final({handsfree_final}) ≠ Goal({handsfree_goal})")

            if mismatches:
                print("The plan is valid, but the final state does not match the goal state.")
                print("**Mismatches Detected:**")
                for mismatch in mismatches:
                    print(mismatch)
            else:
                is_valid = True
                print("The plan successfully transformed Initial State into Goal State!")

    else:
        print("❌ Final state is unsat.")
        core = solver.unsat_core()
        print("UNSAT Core (Conflicting Constraints):", core)

        pre_steps, post_steps = [], []
        for constraint in core:
            constraint_str = str(constraint)
            if "step_" in constraint_str:
                parts = constraint_str.split("step_")[-1].split("_")
                if parts[0].isdigit():
                    step_num = int(parts[0])
                    if "pre_" in constraint_str:
                        pre_steps.append(step_num)
                    elif "post_" in constraint_str:
                        post_steps.append(step_num)

        if pre_steps:
            failed_step = min(pre_steps)
        else:
            failed_step = min(post_steps) if post_steps else -1

        prev_step = failed_step - 1

        #print(f"\n**Invalid Action at Step {failed_step}:** {actions[failed_step-1]}")
        
        if prev_step >= 0 and prev_step < len(states):
            #print(f"**Previous State after Step {prev_step}:**")
            
            if solver.check() == sat:
                model = solver.model()

                prev_table = {i: model.eval(states[prev_step].table(i), model_completion=True) for i in range(1, num_blocks + 1)}
                prev_hand = {i: model.eval(states[prev_step].hand(i), model_completion=True) for i in range(1, num_blocks + 1)}
                prev_clear = {i: model.eval(states[prev_step].clear(i), model_completion=True) for i in range(1, num_blocks + 1)}
                prev_handsfree = model.eval(states[prev_step].handsfree(), model_completion=True)

                # Print Previous State**
                #print("\n**Previous State (Step {prev_step})**")
                #print(f"- Table Status: {prev_table}")
                #print(f"- Hand Status: {prev_hand}")
                #print(f"- Block Clearance: {prev_clear}")
                #print(f"- Handsfree: {prev_handsfree}")

            else:
                print("**Solver is in `unsat` state, no valid model available.**")
        else:
            print("**Previous state is undefined!**")

        feedback = generate_feedback(failed_step, actions, core)

        #print(feedback)
        return False, feedback
    
    return is_valid, "✅ The plan successfully transformed Initial State into Goal State!"

        

if __name__ == "__main__":

    blocks_file_path = "scenario/initial.txt"
    goal_file_path = "scenario/goal.txt"


    plan_text = """
    unstack(5,9)
    put-down(5)
    unstack(9,1)
    put-down(9)
    unstack(6,4)
    put-down(6)
    unstack(8,3)
    put-down(8)
    unstack(3,7)
    put-down(3)
    unstack(11,2)
    put-down(11)
    unstack(2,10)
    put-down(2)
    unstack(12,13)
    put-down(12)
    pick-up(10)
    stack(10,2)
    pick-up(13)
    stack(13,9)
    pick-up(12)
    stack(12,8)
    pick-up(8)
    stack(8,6)
    pick-up(11)
    stack(11,7)
    pick-up(7)
    stack(7,1)
    pick-up(1)
    stack(1,4)
    """

    run_plan(plan_text, blocks_file=blocks_file_path, goal_file=goal_file_path)