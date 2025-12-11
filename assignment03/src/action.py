# CS 452/552 - Assignment 3
# Name: Benjamin Zignego

from enum import Enum, auto


class Action(Enum):
    MOVE_FORWARD = auto()
    TURN_LEFT = auto()
    TURN_RIGHT = auto()
    GRAB = auto()
    SHOOT = auto()
    CLIMB = auto()
    NO_OP = auto()
