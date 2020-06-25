from os import getenv

GAME_LENGTH = int(getenv("GAME_LENGTH", "15"))
INTERVAL = int(getenv("INTERVAL", "10"))

MAX_LENGTH = int(getenv("MAX_GAME_LENGTH", "50"))
MAX_INTERVAL = int(getenv("MAX_INTERVAL", "60"))

class Option:
    def __init__(self, name, values, multiplier):
        self.name = name
        self.values = range(0,values)
        self.multiplier = multiplier

actions = [
    "action2",
    "action4",
    "action3",
    "action1"
]

options = [
    Option("option1", 2, lambda x, d: (x*5000)*(d/100)),
    Option("option2", 65, lambda x, d: pow(x, 2.1772)*(d/100)),
    Option("option3", 50, lambda x, d: pow(x, 3.0745)*(d/100)),
    Option("option4", 100, lambda x, d: (x*10)*(d/100)),
    Option("option5", 5, lambda x, d: pow(x, 6.65)*(d/100))
]