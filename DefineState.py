from z3 import *

class State:
    def __init__(self, name):
        self.name = name
        self.table = Function(f'{name}_table', IntSort(), BoolSort())
        self.hand = Function(f'{name}_hand', IntSort(), BoolSort())
        self.stacked = Function(f'{name}_stacked', IntSort(), IntSort(), BoolSort())
        self.clear = Function(f'{name}_clear', IntSort(), BoolSort())
        self.handsfree = Function(f'{name}_handsfree', BoolSort())

def define_state(solver, filename, state_name):

    state = State(state_name)

    with open(filename, "r") as f:
        lines = f.readlines()
    
    block_positions = [list(map(int, line.strip().split(","))) for line in lines if line.strip()]

    all_blocks = set(sum(block_positions, [])) 
    num_blocks = len(all_blocks)
    on_table = {row[0] for row in block_positions} 
    clear_blocks = {row[-1] for row in block_positions}

    #print(f"\n=== Total Blocks Detected: {num_blocks} ===")


    for block in all_blocks:
        solver.add(state.table(block) == (block in on_table))

    for block in all_blocks:
        solver.add(state.clear(block) == (block in clear_blocks))

    for row in block_positions:
        for i in range(len(row) - 1):
            solver.add(state.stacked(row[i+1], row[i]) == True)

    solver.add(state.handsfree() == True)

    for block in all_blocks:
        solver.add(state.hand(block) == False)

    '''
    #print(f"\n=== Checking {state_name} State in Z3 ===")
    if solver.check() == sat:
        model = solver.model()
        for block in all_blocks:
            ##print(f"table({block}) = {model.eval(state.table(block), model_completion=True)}")
            print(f"hand({block}) = {model.eval(state.hand(block), model_completion=True)}")
            print(f"clear({block}) = {model.eval(state.clear(block), model_completion=True)}")
        print(f"handsfree = {model.eval(state.handsfree(), model_completion=True)}")

        print("\n=== Stacked Relationships ===")
        for row in block_positions:
            for i in range(len(row) - 1):
                print(f"stacked({row[i+1]}, {row[i]}) = {model.eval(state.stacked(row[i+1], row[i]), model_completion=True)}")
    else:
        print("Z3 failed to solve state initialization.")
    '''
    return state, num_blocks