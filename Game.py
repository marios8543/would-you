from Instagram import Instagram
from random import randint, choice
from constants import actions, options, Option, GAME_LENGTH, INTERVAL
from asyncio import get_event_loop, Queue, Event, wait_for, TimeoutError
from json import loads, dumps
from datetime import datetime
from math import floor

games = {}
ig_client = Instagram()

class Player:
    def __init__(self, name, ip):
        self.player_id = str(abs(hash(name+str(datetime.now()))))
        self.name = name
        self.answers = {} # 0:No, 1: Yes, 2:N/A
        self.queue = Queue()
        self.balance = 0
        self.answered = False
        self.ip = ip

    def send(self, message):
        self.queue.put_nowait(message)

    def to_dict(self):
        return {
            "name": self.name,
            "balance": self.balance
        }

class Scenario:
    def __init__(self, person, action, chances, difficulty):
        self.money = floor(sum([i.multiplier(chances[i], difficulty) for i in chances]))
        self.person = person
        self.action = action
        self.chances = {i.name : chances[i] for i in chances}
        self.scenario_id = str(abs(hash(
            str(person.user_id)+
            action+
            "".join([str(i)+str(self.chances[i]) for i in self.chances])+
            str(self.money)
        )))

    def to_dict(self):
        return {
            "id": self.scenario_id,
            "money": self.money,
            "user": self.person.to_dict(),
            "action" : self.action,
            "chances": self.chances
        }

async def Game(opts, ig_username, no_action1, *args):
    following = await ig_client.get_following(ig_username)
    return _Game(opts, following, no_action1, *args)

class _Game:
    def __init__(self, opts, following, no_action1, interval, length, difficulty, private):
        self.game_id = str(randint(100000,999999))
        self.options = [i for i,v in enumerate(opts) if v]
        self.players = []
        self.scenarios = {}
        self.following = following
        self.event = Event()
        self.no_action1 = no_action1
        self.task = None
        self.interval = interval
        self.length = length
        self.difficulty = 100 - difficulty
        self.private = private
        if not self.following:
            raise ValueError("no_following")

    def add_to_games(self):
        games[self.game_id] = self

    def remove_from_games(self):
        games.pop(self.game_id, None)

    def add_player(self, player_name, ip):
        player = Player(player_name, ip)
        for i in self.players:
            player.send(dumps({"event":"player_add", "data":i.to_dict()}))
        self.players.append(player)
        self.broadcast(dumps({"event":"player_add", "data":player.to_dict()}))
        self.announce("{} joined the game!".format(player_name))
        return player

    def remove_player(self, player_id):
        for i in self.players:
            if i.player_id == player_id:
                self.players.remove(i)
                self.broadcast(dumps({"event":"player_remove", "data":i.to_dict()}))
                self.announce("{} left the game.".format(i.name))
                break
        if len(self.players) == 0:
            if self.task:
                self.task.cancel()
            self.remove_from_games()

    def has_player(self, name, ip):
        return name in [i.name for i in self.players] or ip in [i.ip for i in self.players]

    def get_player_queue(self, player_id):
        for i in self.players:
            if i.player_id == player_id:
                i.connected = True
                return i.queue
        raise ValueError("player_not_exist")

    def player_answer(self, player_id, scenario_id, answer):
        for i in self.players:
            if i.player_id == player_id:
                if i.answered:
                    return
                if scenario_id in self.scenarios:
                    i.answers[scenario_id] = answer
                    i.answered = True
                    if answer:
                        i.balance += self.scenarios[scenario_id].money
                    self.broadcast(dumps({"event":"player_answer", "data": {"player":i.to_dict(), "details": {"answer":int(answer), "balance":i.balance}}}))
                    break
                else:
                    raise ValueError("scenario_not_exist")
        else:
            raise ValueError("player_not_exist")

    def broadcast(self, message):
        for i in self.players:
            i.send(message)

    def announce(self, message):
        self.broadcast(dumps({"event":"new_message", "data":{"name":"System", "content": message}}))
        
    def create_scenario(self):
        person = choice(self.following)
        action = choice(actions[:-1]) if self.no_action1 else choice(actions)
        chances = {options[i] : choice(options[i].values) for i in self.options}
        if action == "action4":
            for i in chances:
                if i.name == "option3" or i.name == "option2" or i.name == "option4":
                    chances[i] = 0

        scenario = Scenario(person, action, chances, self.difficulty)
        self.scenarios[scenario.scenario_id] = scenario

        return scenario

    async def _start(self):
        self.broadcast(dumps({"event":"game_start"}))
        for _ in range(self.length):
            self.event.clear()
            scen = self.create_scenario()
            for i in self.players:
                i.answers[scen.scenario_id] = 2
                i.answered = False
            self.broadcast(dumps({"event":"new_scenario", "data":scen.to_dict()}))
            try:
                await wait_for(self.event.wait(), self.interval)
            except TimeoutError:
                pass
        winner = max(self.players, key=lambda p: p.balance)
        self.announce("{} won with ${} !".format(winner.name, winner.balance))
        self.broadcast(dumps({"event":"game_end"}))

    def start(self):
        self.task = get_event_loop().create_task(self._start())
        
