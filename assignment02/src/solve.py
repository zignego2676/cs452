# Benjamin Zignego
# 11/19/2025
import argparse
import time
import sys
import pathlib
from collections import defaultdict, namedtuple

# python data stucture wowee
Variable = namedtuple("Variable", ["name", "cells", "length", "number", "direction"])
# direction: "across" or "down"

# Begin file parsing helpers #
def load_dictionary(filename):
    words = []

    with open(filename, 'r') as f:
        for line in f:
            w = line.strip()
            if w:
                words.append(w.upper())

    return words

def load_puzzle(filename):
    with open(filename, 'r') as f:
        tokens = []
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            for p in parts:
                tokens.append(p)

    rows = int(tokens[0])
    cols = int(tokens[1])
    grid = []
    numbers = {}
    idx = 2

    for r in range(rows):
        row = []
        for c in range(cols):
            tok = tokens[idx]
            idx += 1
            if tok == '#':
                row.append('#')
            elif tok == '_':
                row.append('_')
            else:
                num = int(tok)
                row.append('_')
                numbers[(r, c)] = num
        grid.append(row)

    return rows, cols, grid, numbers
# End file parsing helpers #

# CSP shenanigans
def extract_variables(rows, cols, grid, numbers):
    varsByNumber = defaultdict(list)
    variables = []
    # function in a function for helping to find blank
    def blank(r, c):
        return 0 <= r < rows and 0 <= c < cols and grid[r][c] != '#'

    # scan cells for numbers 
    for (r, c), num in numbers.items():
        # check across
        if (c == 0 or grid[r][c-1] == '#') and (c+1 < cols and blank(r, c+1)):
            cells = []
            cc = c

            while cc < cols and blank(r, cc):
                cells.append((r, cc))
                cc += 1

            v = Variable(name=f"{num}-A", cells=cells, length=len(cells), number=num, direction='across')
            varsByNumber[num].append(('across', v))
            variables.append(v)
        # check down
        if (r == 0 or grid[r-1][c] == '#') and (r+1 < rows and blank(r+1, c)):
            cells = []
            rr = r

            while rr < rows and blank(rr, c):
                cells.append((rr, c))
                rr += 1

            v = Variable(name=f"{num}-D", cells=cells, length=len(cells), number=num, direction='down')
            varsByNumber[num].append(('down', v))
            variables.append(v)

    orderedVars = []

    for num in sorted(varsByNumber.keys()):
        entries = varsByNumber[num]
        entries.sort(key=lambda x: 0 if x[0] == 'across' else 1)
        for _, v in entries:
            orderedVars.append(v)

    return orderedVars

def build_csp(variables, dictionary):
    domains = {}

    for var in variables:
        domains[var.name] = sorted([word for word in dictionary if len(word) == var.length])

    neighbors = defaultdict(set)
    intersections = dict()  
    cells = defaultdict(list)

    for var in variables:
        for i, cell in enumerate(var.cells):
            cells[cell].append((var.name, i))

    for cell, lst in cells.items():
        if len(lst) > 1:
            for a in range(len(lst)):
                for b in range(a+1, len(lst)):
                    v1, i1 = lst[a]
                    v2, i2 = lst[b]
                    neighbors[v1].add(v2)
                    neighbors[v2].add(v1)
                    intersections[(v1, v2)] = (i1, i2)
                    intersections[(v2, v1)] = (i2, i1)

    constraintEdges = len({frozenset([a,b]) for (a,b) in intersections.keys()}) // 1

    return domains, neighbors, intersections

# Heuristic shenanigans
def select_variable(variablesOrder, domains, neighbors, assignment, var_selection):
    unassigned = [var for var in variablesOrder if var not in assignment]

    if not unassigned:
        return None

    if var_selection == 'static':
        return unassigned[0]

    if var_selection == 'mrv':
        return min(unassigned, key=lambda v: len(domains[v]))

    if var_selection == 'deg':
        return max(unassigned, key=lambda v: sum(1 for n in neighbors[v] if n not in assignment))

    if var_selection == 'mrv+deg':
        best = None
        bestTuple = None
        for v in unassigned:
            t = (len(domains[v]), -sum(1 for n in neighbors[v] if n not in assignment))
            if best is None or t < bestTuple:
                best = v
                bestTuple = t
        return best

def order_domain_values(var, domains, neighbors, intersections, assignment, valueOrder):
    vals = domains[var]

    if valueOrder == 'static':
        return list(vals)

    if valueOrder == 'lcv':
        scores = []

        for val in vals:
            elim = 0

        return list(vals)

# Consistency thingies
def is_consistent(var, val, assignment, domains, neighbors, intersections, lfc):
    for n in neighbors[var]:
        if n in assignment:
            if (var, n) in intersections:
                i, j = intersections[(var, n)]
                if val[i] != assignment[n][j]:
                    return False
    if not lfc:
        return True

    # limited forward check
    for n in neighbors[var]:
        if n not in assignment:
            if (var, n) in intersections:
                i, j = intersections[(var, n)]
                found_support = False

                for cand in domains[n]:
                    ok = True

                    if cand[j] != val[i]:
                        ok = False

                    if not ok:
                        continue

                    for other in neighbors[n]:
                        if other in assignment and other != var and (n, other) in intersections:
                            in_j, in_k = intersections[(n, other)]
                            if cand[in_j] != assignment[other][in_k]:
                                ok = False
                                break

                    if ok:
                        found_support = True
                        break

                if not found_support:
                    return False
    return True

def lcv_order(var, domains, neighbors, intersections, assignment):
    vals = domains[var]
    scores = []

    for val in vals:
        elim = 0

        for n in neighbors[var]:
            if n in assignment:
                continue

            if (var, n) not in intersections:
                continue

            i, j = intersections[(var, n)]
            compatible = 0

            for cand in domains[n]:
                ok = True
                if cand[j] != val[i]:
                    ok = False

                if not ok:
                    continue

                for other in neighbors[n]:
                    if other in assignment and (n, other) in intersections:
                        in_j, in_k = intersections[(n, other)]
                        if cand[in_j] != assignment[other][in_k]:
                            ok = False
                            break

                if ok:
                    compatible += 1

            elim += (len(domains[n]) - compatible)

        scores.append((elim, val))

    scores.sort(key=lambda x: (x[0], x[1]))

    return [v for _, v in scores]

# the big backtrack search
def backtracking_search(variables, domains, neighbors, intersections,
                        variableSelection, valueOrder, lfc,
                        verbosity):
    variablesOrder = [v.name for v in variables]
    assignment = {}
    nodes = 0
    startTime = time.perf_counter()
    constraint_set = set()

    for (a, b) in intersections.keys():
        constraint_set.add(tuple(sorted((a, b))))
    numConstraints = len(constraint_set)

    def backtrack(depth=0):
        # can do some crazy shenanigans in python man
        nonlocal nodes
        nodes += 1
        if len(assignment) == len(variablesOrder):
            return assignment.copy()

        var = select_variable(variablesOrder, domains, neighbors, assignment, variableSelection)
        if var is None:
            return assignment.copy()

        if valueOrder == 'lcv':
            vals = lcv_order(var, domains, neighbors, intersections, assignment)
        else:
            vals = list(domains[var])  # static alphabetical

        if verbosity >= 2:
            indent = "  " * depth
            print(f"{indent}Select {var}; trying values: {', '.join(vals)}")

        for val in vals:
            ok = is_consistent(var, val, assignment, domains, neighbors, intersections, lfc)

            if verbosity >= 2:
                indent = "  " * depth
                print(f"{indent}Try {var}={val} -> {'consistent' if ok else 'inconsistent'}")

            if not ok:
                continue

            assignment[var] = val
            result = backtrack(depth + 1)

            if result is not None:
                return result

            del assignment[var]

        return None

    solution = backtrack(0)
    endTime = time.perf_counter()
    elapsed = endTime - startTime

    return solution, elapsed, nodes, len(variablesOrder), numConstraints

# Output printing
def print_solution_grid(rows, cols, grid, numbers, variables, assignment):
    # i love python inline statements
    mat = [[' ' if grid[r][c] != '#' else '#' for c in range(cols)] for r in range(rows)]
    varMap = {v.name: v for v in variables}

    for vname, word in assignment.items():
        v = varMap[vname]
        for i, (r, c) in enumerate(v.cells):
            mat[r][c] = word[i]

    # Just replace the # with spaces for readability
    for r in range(rows):
        line = ''

        for c in range(cols):
            ch = mat[r][c]
            if ch == '#':
                line += ' '
            else:
                line += ch

        print(line)

def main():
    # Begin arg parsing #
    parser = argparse.ArgumentParser(prog="Python Crossword Search",
                                     description="")
    parser.add_argument("-d", "--dictionary", help="path to text file containing dictionary data", required=True, type=pathlib.Path)
    parser.add_argument("-p", "--puzzle", help="path to text file containing puzzle data", required=True, type=pathlib.Path)
    parser.add_argument("-v", "--verbosity", default = 0, help="how much info to stdout (default=0)", type=int, choices=[0, 1, 2])
    parser.add_argument("-vs", "--variable-selection", default="static", help="how variables should be ordered in backtracking (default=static)", choices=["static", "mrv", "deg", "mrv+deg"])
    parser.add_argument("-vo", "--value-order", default="static", help="order in which a variable's values will be iterated (default=static)", choices=["static", "lcv"])
    parser.add_argument("-lfc", "--limited-forward-check", help="if limited forward checking should be used for consistency", action='store_true')

    args = parser.parse_args()
    # End arg parsing #

    dictionary = load_dictionary(args.dictionary)
    rows, cols, grid, numbers = load_puzzle(args.puzzle)

    variables = extract_variables(rows, cols, grid, numbers)
    domains, neighbors, intersections = build_csp(variables, dictionary)

    if args.verbosity > 0:
        print(f"Variables: {len(variables)}, Constraints (pairs): {len({tuple(sorted((x,y))) for (x,y) in intersections.keys()})}")
    if args.verbosity > 1:
        print(f"Dictionary words: {len(dictionary)}")
        print(f"Puzzle size: {rows}x{cols}, variables: {len(variables)}")
        for var in variables:
            print(f"Variable {var.name} ({var.direction}, len={var.length}): domain size {len(domains[var.name])}")

    # Search
    solution, elapsed, calls, numVars, numConstraints = backtracking_search(variables, domains, neighbors, intersections, args.variable_selection, args.value_order, args.limited_forward_check, args.verbosity)

    if solution is not None:
        print("SUCCESS!")
        print(f"Time: {elapsed:.6f} seconds")
        print(f"Backtracking calls: {calls}")
        if args.verbosity == 0:
            print()
            print_solution_grid(rows, cols, grid, numbers, variables, solution)
        else:
            print("Solution grid:")
            print_solution_grid(rows, cols, grid, numbers, variables, solution)
    else:
        print("FAILED")
        print(f"Time: {elapsed:.6f} seconds")
        print(f"Backtracking calls: {calls}")

if __name__ == "__main__":
    main()

