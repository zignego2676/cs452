# Benjamin Zignego
# 10/12/2025

import argparse
import os
import sys
import heapq
import time
from collections import defaultdict, deque # dark and evil double duty queue

def search(graph, start, goal, algo):
    # evil string comparison
    if(algo == "bfs"):
        frontier = deque([(start, [start], 0.0)])
        pop = frontier.popleft
        push = frontier.append
    elif(algo == "dfs"):
        frontier = deque([(start, [start], 0.0)])
        pop = frontier.pop
        push = frontier.append
    elif(algo == "dijkstra" or not algo):
        frontier = [(0.0, start, [start])]
        pop = lambda: heapq.heappop(frontier)
        push = lambda item: heapq.heappush(frontier, item)
    else:
        print("error: invalid search algorithm")
        sys.exit(1)

    reached = {start: 0.0}
    nodes = 1  # start node

    while frontier:
        if(algo == "dijkstra"):
            cost, node, path = pop()
        else:
            node, path, cost = pop()

        if(node == goal):
            return path, cost, nodes, len(frontier)

        for neighbor, dist in graph[node].items():
            newCost = cost + (dist if algo == "dijkstra" else 1)
            if neighbor not in reached or newCost < reached[neighbor]:
                reached[neighbor] = newCost
                nodes += 1
                if(algo == "dijkstra"):
                    push((newCost, neighbor, path + [neighbor]))
                else:
                    push((neighbor, path + [neighbor], newCost))

    return None, float('inf'), nodes, len(frontier)



parser = argparse.ArgumentParser(prog="Python Route Search",
                                 description="Compare algorithms to search for the least cost path between 2 nodes in a given file",
                                 epilog="10/12/2025 Benjamin Zignego")
parser.add_argument("-f", "--file", help="path to csv file containing nodes and distances")
parser.add_argument("-i", "--initial", help="node to start searching from")
parser.add_argument("-g", "--goal", help="node to end search at")
parser.add_argument("-s", "--search", default="dijkstra", help="search algorithm to use")

args = parser.parse_args()
filepath = args.file
start = args.initial
goal = args.goal
algo = args.search

if(not os.path.isfile(filepath)):
    print("error: invalid filepath")
    sys.exit(1)
elif(not filepath or not start or not goal):
    print("error: invalid arg or incorrect number of args")
    sys.exit(1)

datafile = open(filepath)
graph = defaultdict(dict)

# hideous python for loop of doom and destruction
# i miss my curly brackets and parentheses :(
for line in datafile:
    line = line.strip()
    if(line and not line.startswith("#")):
        city1, city2, dist = [token.strip() for token in line.split(",")]
        # python dict yippee yay wow
        dist = float(dist)
        graph[city1][city2] = dist
        graph[city2][city1] = dist

if(start not in graph or goal not in graph):
    print("error: start or goal not in given data");
    sys.exit(1)

startTime = time.time()
path, cost, nodes, size = search(graph, start, goal, algo)
endTime = time.time()

if(path):
    print("Route found:", " -> ".join(path))
    if(algo == "dijkstra"):
        print("Distance:", round(cost, 1), "miles")
    else:
        print("Edges:", cost)
else:
    print("NO PATH FOUND")

print("Total nodes generated:", nodes)
print("Nodes remaining on frontier:", size)
print(f"Time algorithm took to run: {(endTime - startTime) * 1000:.6f} ms")

datafile.close()
