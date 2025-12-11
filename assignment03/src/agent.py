# CS 452/552 - Assignment 3
# Name: Benjamin Zignego

from abc import ABC, abstractmethod


class Agent(ABC):
    """
    Base class for Wumpus World agents.
    """

    @abstractmethod
    def initialize(self, grid_size, num_arrows, **kwargs):
        """
        Called once at the beginning of each new world / trial.

        :param grid_size: Size N of the N x N grid.
        :param num_arrows: Initial number of arrows available.
        :param kwargs: Optional parameters (max_actions, verbosity, etc.)
        """
        pass

    @abstractmethod
    def next_action(self, percepts):
        """
        Called every time step.

        :param percepts: A set (or list) of Percept enums
        :return: an Action enum
        """
        pass

    def game_over(self, score):
        """
        Called once at the end of the trial with the final score.
        Can be used for learning/statistics. Default: do nothing.
        """
        pass
