# CS 452/552 - Assignment 3
# Name: Benjamin Zignego
from agent import Agent
from action import Action
from percept import Percept
from collections import deque

class MyAgent(Agent):
    """
    Rule-based Wumpus World agent.

    Strategy: 
    - Maintain internal map state:
        - visited: cells we've been to
        - safe: cells we believe are safe
        - possible_risky: cells adjacent to a breeze/stench (don't move there unless needed)
        - walls: cells outside the grid (discovered by bump)
    - Keep track of our estimated position and orientation.
    - If GLITTER: GRAB, then plan path back to (0,0) and CLIMB.
    - Exploration: plan a shortest path (BFS) to the nearest safe, unvisited cell.
    - Movement: translate planned path into a small sequence of Actions (turns + move_forwards).
    - Update internal state on each call to next_action using the latest percepts and the last action taken.
    """

    # Directions: 0 = EAST, 1 = NORTH, 2 = WEST, 3 = SOUTH
    DIR_VECTORS = [(1, 0), (0, 1), (-1, 0), (0, -1)]

    def initialize(self, grid_size, num_arrows, **kwargs):
        # World parameters
        self.N = grid_size
        self.num_arrows = num_arrows
        self.max_actions = kwargs.get("max_actions", None)
        self.verbosity = kwargs.get("verbosity", 0)

        # Internal belief state
        self.visited = set()
        self.safe = set()
        self.possible_risky = set()  # cells that might have pit/wumpus (adjacent to breeze/stench)
        self.walls = set()  # cells outside grid discovered by bump (we mark forward cell as wall)
        self.has_gold = False

        # Agent internal state estimate
        self.pos = (0, 0)
        self.dir = 0  # EAST

        # Mark start as safe/visited
        self.safe.add(self.pos)
        self.visited.add(self.pos)

        # Action planning queue
        self.action_queue = deque()

        # For processing effects of the previous step like new percepts
        self.last_action = None

        if self.verbosity > 0:
            print("[AGENT INIT] grid_size", self.N, "arrows", self.num_arrows)


    # Helpers
    def in_bounds(self, cell):
        x, y = cell
        return 0 <= x < self.N and 0 <= y < self.N


    # Keep track of the cells adjacent to us
    def neighbors(self, cell):
        x, y = cell
        for dx, dy in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.N and 0 <= ny < self.N:
                yield (nx, ny)


    # What cell is in front of us
    def forward_cell(self):
        dx, dy = MyAgent.DIR_VECTORS[self.dir]
        x, y = self.pos
        return (x + dx, y + dy)


    # To translate a direction into turn actions
    def face_direction_actions(self, target_dir):
        diff = (target_dir - self.dir) % 4
        if diff == 0:
            return []
        if diff == 1:
            return [Action.TURN_LEFT]
        if diff == 2:
            # two lefts (or two rights)
            return [Action.TURN_LEFT, Action.TURN_LEFT]
        if diff == 3:
            return [Action.TURN_RIGHT]


    # What direction the destination cell is from us
    def dir_to(self, from_cell, to_cell):
        fx, fy = from_cell
        tx, ty = to_cell
        dx, dy = tx - fx, ty - fy
        for i, (vx, vy) in enumerate(MyAgent.DIR_VECTORS):
            if (dx, dy) == (vx, vy):
                return i
        return None


    # Put appropriate actions in the queue to follow a path
    def enqueue_path_actions(self, path):
        if not path or len(path) < 2:
            return
        for i in range(len(path) - 1):
            cur = path[i]
            nxt = path[i + 1]
            needed_dir = self.dir_to(cur, nxt)
            if needed_dir is None:
                continue
            turns = self.face_direction_actions(needed_dir)
            for t in turns:
                self.action_queue.append(t)
            self.action_queue.append(Action.MOVE_FORWARD)


    # Use BFS search to find the shortest safe path
    # Allow unknown is whether we should stick to what we know
    def bfs_shortest_path(self, start, goals, allow_unknown=False):
        q = deque()
        q.append(start)
        parent = {start: None}
        visited = {start}
        while q:
            cur = q.popleft()
            if cur in goals:
                # reconstruct path
                path = []
                node = cur
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                return path
            for nb in self.neighbors(cur):
                if nb in visited:
                    continue
                if nb in self.walls:
                    continue
                if nb in self.safe or (allow_unknown and nb not in self.possible_risky):
                    visited.add(nb)
                    parent[nb] = cur
                    q.append(nb)
        return None


    # Reason about the next safest unvisited cell to visit
    def plan_explore(self):
        # Candidate goals are safe but not visited
        goals = {cell for cell in self.safe if cell not in self.visited}
        if goals:
            path = self.bfs_shortest_path(self.pos, goals)
            if path:
                self.enqueue_path_actions(path)
                return True

        # If no safe unvisited, consider unknown neighbors that aren't marked risky/walls
        unknown_cells = []
        for x in range(self.N):
            for y in range(self.N):
                c = (x, y)
                if c in self.visited or c in self.walls:
                    continue
                if c not in self.safe and c not in self.possible_risky:
                    unknown_cells.append(c)
        if unknown_cells:
            path = self.bfs_shortest_path(self.pos, set(unknown_cells), allow_unknown=True)
            if path:
                self.enqueue_path_actions(path)
                return True

        # Nothing to explore: fallback to return to start if not there
        if self.pos != (0, 0):
            path = self.bfs_shortest_path(self.pos, {(0, 0)})
            if path:
                self.enqueue_path_actions(path)
                return True

        # No plan possible
        return False


    # Plan the path back to (0, 0) and climb out
    def plan_return_home_and_climb(self):
        path = self.bfs_shortest_path(self.pos, {(0, 0)})
        if path:
            self.enqueue_path_actions(path)
            self.action_queue.append(Action.CLIMB)
            return True
        return False


    # Update beliefs based on percepts from environment
    def process_last_action(self, percepts):
        """
        Use last_action and the returned percepts to update internal state:
        - If last action was MOVE_FORWARD and BUMP is in percepts: forward cell is wall
        - If no BUMP: update self.pos to forward cell
        - If last_action was TURN_LEFT / TURN_RIGHT: update self.dir.
        - If last_action was GRAB: if we previously perceived GLITTER, assume we now have gold.
        """
        if self.last_action is None:
            return

        if self.last_action == Action.MOVE_FORWARD:
            if Percept.BUMP in percepts:
                fcell = self.forward_cell()
                if not self.in_bounds(fcell):
                    self.walls.add(fcell)
                else:
                    # sanity check
                    self.walls.add(fcell)
                if self.verbosity > 1:
                    print("[AGENT] bump at", self.pos, "forward:", fcell, "marked as wall")
            else:
                # Update position
                fcell = self.forward_cell()
                if self.in_bounds(fcell):
                    self.pos = fcell
                    self.visited.add(self.pos)
                    self.safe.add(self.pos)
                    if self.verbosity > 1:
                        print("[AGENT] moved to", self.pos)
        elif self.last_action == Action.TURN_LEFT:
            self.dir = (self.dir + 1) % 4
            if self.verbosity > 1:
                print("[AGENT] turned left -> dir", self.dir)
        elif self.last_action == Action.TURN_RIGHT:
            self.dir = (self.dir - 1) % 4
            if self.verbosity > 1:
                print("[AGENT] turned right -> dir", self.dir)
        elif self.last_action == Action.GRAB:
            # If we grabbed while on glitter, assume we now have gold.
            self.has_gold = True
            if self.verbosity > 0:
                print("[AGENT] grabbed gold (internal)")


    def update_beliefs_from_percepts(self, percepts):
        """
        Update beliefs (safe, possible_risky) based on current percepts at self.pos.
        - If no BREEZE and no STENCH: all neighbors are safe
        - If BREEZE or STENCH: neighbors not yet visited/safe get marked as possible_risky
        """

        # Verbosity outputs
        if Percept.GLITTER in percepts:
            # We're on gold (and we haven't grabbed it yet)
            # Do not change adjacency info just for glitter
            if self.verbosity > 0:
                print("[AGENT] GLITTER perceived at", self.pos)
        if Percept.BREEZE in percepts:
            # We're close to a pit
            if self.verbosity > 0:
                print("[AGENT] BREEZE perceived at", self.pos)
        if Percept.STENCH in percepts:
            # We're close to a Wumpus
            if self.verbosity > 0:
                print("[AGENT] STENCH perceived at", self.pos)

        has_breeze = Percept.BREEZE in percepts
        has_stench = Percept.STENCH in percepts

        neighbors = list(self.neighbors(self.pos))
        if not has_breeze and not has_stench:
            # Neighbors are safe
            for nb in neighbors:
                if nb not in self.walls:
                    self.safe.add(nb)
        else:
            # Mark unvisited neighbors as possibly risky
            for nb in neighbors:
                if nb not in self.visited and nb not in self.safe:
                    self.possible_risky.add(nb)


    # Choose next action
    def next_action(self, percepts):
        # Process effect of the last action
        self.process_last_action(percepts)

        # Update beliefs
        self.update_beliefs_from_percepts(percepts)

        # If we perceive GLITTER and don't already have gold, grab it now and then plan to go home
        if Percept.GLITTER in percepts and not self.has_gold:
            if self.verbosity > 0:
                print("[AGENT] planning to GRAB gold at", self.pos)
            self.action_queue.append(Action.GRAB)
            # After grabbing, we'll plan path home on subsequent calls (we set has_gold in process_last_action)
            self.last_action = None
            next_act = self.action_queue.popleft()
            self.last_action = next_act
            return next_act

        # If we have gold and haven't planned return-and-climb
        if self.has_gold and Action.CLIMB not in self.action_queue:
            planned = self.plan_return_home_and_climb()
            if planned and self.verbosity > 0:
                print("[AGENT] planned return home and CLIMB")

        if self.action_queue:
            act = self.action_queue.popleft()
            self.last_action = act
            return act

        # No queued actions: plan exploration or fallback
        planned = self.plan_explore()
        if planned and self.action_queue:
            act = self.action_queue.popleft()
            self.last_action = act
            return act

        # If we are at start and have gold: climb
        if self.pos == (0, 0) and self.has_gold:
            self.last_action = Action.CLIMB
            return Action.CLIMB

        # Climb if nothing left to explore
        if self.pos == (0, 0):
            self.last_action = Action.CLIMB
            return Action.CLIMB

        # Try to go home using any allowed nodes
        path = self.bfs_shortest_path(self.pos, {(0, 0)}, allow_unknown=True)
        if path:
            self.enqueue_path_actions(path)
            if self.action_queue:
                act = self.action_queue.popleft()
                self.last_action = act
                return act

        # NO_OP as last action
        self.last_action = Action.NO_OP
        return Action.NO_OP


    def game_over(self, score):
        if self.verbosity > 0:
            print(f"[AGENT] game over. Score: {score}. Visited: {len(self.visited)} cells. Has gold: {self.has_gold}")

