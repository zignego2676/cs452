# CS 452/552 - Assignment 3
# Name: Benjamin Zignego

import random
from action import Action
from percept import Percept

# Directions: 0 = EAST, 1 = NORTH, 2 = WEST, 3 = SOUTH
DIRECTIONS = [(1, 0), (0, 1), (-1, 0), (0, -1)]


class Environment:
    """
    Wumpus World environment.
    """

    def __init__(self, grid_size=4, pit_prob=0.2, max_actions=100,
                 num_arrows=1, seed=12345, verbosity=0):
        self.grid_size = grid_size
        self.pit_prob = pit_prob
        self.max_actions = max_actions
        self.num_arrows = num_arrows
        self.verbosity = verbosity

        self.rng = random.Random(seed)

        # World layout
        self.pits = set()
        self.wumpus_alive = True
        self.wumpus_pos = None
        self.gold_pos = None

        # Agent state
        self.agent_pos = (0, 0)
        self.agent_dir = 0  # EAST
        self.agent_alive = True
        self.agent_has_gold = False
        self.agent_arrows = num_arrows

        # Game state
        self.score = 0
        self.action_count = 0
        self.bump = False
        self.scream = False
        self.terminated = False

        self._generate_world()

    def _log(self, *args):
        if self.verbosity > 0:
            print("[ENV]", *args)

    def _generate_world(self):
        N = self.grid_size

        # Place pits (except start)
        for x in range(N):
            for y in range(N):
                if (x, y) == (0, 0):
                    continue
                if self.rng.random() < self.pit_prob:
                    self.pits.add((x, y))

        # Place Wumpus at random cell != (0,0) and not a pit
        candidates = [
            (x, y)
            for x in range(N)
            for y in range(N)
            if (x, y) != (0, 0) and (x, y) not in self.pits
        ]
        self.wumpus_pos = self.rng.choice(candidates)

        # Place gold at random safe cell != (0,0)
        gold_candidates = [
            (x, y)
            for (x, y) in candidates
            if (x, y) != self.wumpus_pos
        ]
        self.gold_pos = self.rng.choice(gold_candidates)

        self._log("Pits:", self.pits)
        self._log("Wumpus:", self.wumpus_pos)
        self._log("Gold:", self.gold_pos)

    def _adjacent_cells(self, x, y):
        N = self.grid_size
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < N and 0 <= ny < N:
                yield (nx, ny)

    def _compute_percepts(self):
        percepts = set()

        x, y = self.agent_pos

        # Breeze if adjacent to pit
        if any((nx, ny) in self.pits for (nx, ny) in self._adjacent_cells(x, y)):
            percepts.add(Percept.BREEZE)

        # Stench if adjacent to live Wumpus
        if self.wumpus_alive and any(
            (nx, ny) == self.wumpus_pos for (nx, ny) in self._adjacent_cells(x, y)
        ):
            percepts.add(Percept.STENCH)

        # Glitter if on gold
        if (x, y) == self.gold_pos and not self.agent_has_gold:
            percepts.add(Percept.GLITTER)

        # Bump and scream come from last action
        if self.bump:
            percepts.add(Percept.BUMP)
        if self.scream:
            percepts.add(Percept.SCREAM)

        return percepts

    def _move_forward(self):
        x, y = self.agent_pos
        dx, dy = DIRECTIONS[self.agent_dir]
        nx, ny = x + dx, y + dy
        N = self.grid_size

        if 0 <= nx < N and 0 <= ny < N:
            self.agent_pos = (nx, ny)
            self.bump = False
        else:
            # Bump into wall
            self.bump = True

    def _turn_left(self):
        self.agent_dir = (self.agent_dir + 1) % 4

    def _turn_right(self):
        self.agent_dir = (self.agent_dir - 1) % 4

    def _shoot(self):
        if self.agent_arrows <= 0:
            return

        self.agent_arrows -= 1
        # Arrow travels in a straight line; if Wumpus is in that line, it dies
        x, y = self.agent_pos
        dx, dy = DIRECTIONS[self.agent_dir]
        N = self.grid_size
        while 0 <= x < N and 0 <= y < N:
            if (x, y) == self.wumpus_pos and self.wumpus_alive:
                self.wumpus_alive = False
                self.scream = True
                self._log("Wumpus killed!")
                return
            x += dx
            y += dy
        # Missed
        self.scream = False

    def _check_death(self):
        if self.agent_pos in self.pits:
            self.agent_alive = False
            self._log("Agent fell into a pit.")
        elif self.agent_pos == self.wumpus_pos and self.wumpus_alive:
            self.agent_alive = False
            self._log("Agent eaten by the Wumpus.")

    def get_percepts(self):
        """Return current percepts, then clear bump/scream flags for next step."""
        percepts = self._compute_percepts()
        # Note: we clear bump & scream AFTER they are perceived.
        self.bump = False
        self.scream = False
        return percepts

    def step(self, action):
        """
        Apply an action and update the world.
        Returns: (percepts, done)
        """
        if self.terminated:
            return set(), True

        self.action_count += 1
        self.score -= 1  # cost for each action

        self._log("Action:", action.name, "Pos:", self.agent_pos, "Dir:", self.agent_dir)

        # Reset bump/scream for this action
        self.bump = False
        self.scream = False

        if action == Action.MOVE_FORWARD:
            self._move_forward()
            self._check_death()

        elif action == Action.TURN_LEFT:
            self._turn_left()

        elif action == Action.TURN_RIGHT:
            self._turn_right()

        elif action == Action.GRAB:
            if self.agent_pos == self.gold_pos and not self.agent_has_gold:
                self.agent_has_gold = True
                self._log("Gold grabbed!")

        elif action == Action.SHOOT:
            self.score -= 10  # cost of arrow
            self._shoot()

        elif action == Action.CLIMB:
            if self.agent_pos == (0, 0):
                # Exit; if has gold, big reward
                if self.agent_has_gold:
                    self.score += 1000
                self.terminated = True
                self._log("Agent climbed out. Score:", self.score)

        elif action == Action.NO_OP:
            # Do nothing; could be used to signal done
            pass

        # Check death if moved
        if not self.agent_alive:
            self.score -= 1000
            self.terminated = True
            self._log("Agent died. Score:", self.score)

        # Check max actions
        if self.action_count >= self.max_actions and not self.terminated:
            self._log("Max actions reached.")
            self.terminated = True

        percepts = self._compute_percepts()
        done = self.terminated
        return percepts, done
