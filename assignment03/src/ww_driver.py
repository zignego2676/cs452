# CS 452/552 - Assignment 3
# Name: Benjamin Zignego

import argparse

from environment import Environment
from my_agent import MyAgent


def run_trial(args, seed_offset=0):
    env = Environment(
        grid_size=args.grid_size,
        pit_prob=args.pit_prob,
        max_actions=args.max_actions,
        num_arrows=1,
        seed=args.seed + seed_offset,
        verbosity=args.verbosity,
    )

    agent = MyAgent()
    agent.initialize(
        grid_size=args.grid_size,
        num_arrows=1,
        max_actions=args.max_actions,
        verbosity=args.verbosity,
    )

    done = False
    percepts = env.get_percepts()
    total_steps = 0

    while not done:
        action = agent.next_action(percepts)
        percepts, done = env.step(action)
        total_steps += 1

    # Final percepts not needed; environment score is final
    score = env.score
    agent.game_over(score)
    return score, total_steps


def main():
    parser = argparse.ArgumentParser(description="Wumpus World Agent Driver")
    parser.add_argument("-v", "--verbosity", type=int, default=0,
                        help="Verbosity level")
    parser.add_argument("-g", "--grid_size", type=int, default=2,
                        help="Grid size N (N x N world)")
    parser.add_argument("-p", "--pit_prob", type=float, default=0.2,
                        help="Pit probability")
    parser.add_argument("-m", "--max_actions", type=int, default=10,
                        help="Maximum number of actions per trial")
    parser.add_argument("-t", "--time_limit", type=int, default=3000,
                        help="Time limit in ms (not enforced in this reference)")
    parser.add_argument("-n", "--num_trials", type=int, default=1,
                        help="Number of trials to run")
    parser.add_argument("-s", "--seed", type=int, default=12345,
                        help="Random seed")

    args = parser.parse_args()

    scores = []
    steps = []

    for i in range(args.num_trials):
        score, num_steps = run_trial(args, seed_offset=i)
        scores.append(score)
        steps.append(num_steps)
        if args.verbosity > 0:
            print(f"Trial {i+1}: score={score}, steps={num_steps}")

    avg_score = sum(scores) / len(scores)
    avg_steps = sum(steps) / len(steps)

    print("===================================")
    print(f"Trials run: {args.num_trials}")
    print(f"Average score: {avg_score:.2f}")
    print(f"Average steps: {avg_steps:.2f}")


if __name__ == "__main__":
    main()
