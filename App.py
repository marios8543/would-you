from quart import Quart, render_template, request, make_response, redirect, jsonify, websocket, send_from_directory
from constants import options, INTERVAL, GAME_LENGTH, MAX_INTERVAL, MAX_LENGTH
from Game import Game, games, Player, ig_client
from Instagram import InstagramException
from langs import index_page, in_game_page
from json import loads
from asyncio import get_event_loop, CancelledError
from os import getenv
from json import dumps
from random import choice

loop = get_event_loop()
loop.create_task(ig_client.init())
app = Quart(__name__)

def get_lang(req):
    lang = "en"
    l = req.args.get("l")
    if l and l in index_page:
        lang = l
    else:
        l = req.cookies.get("lang")
        if l and l in index_page:
            lang = l
        else:
            coun = req.headers.get("Cf-Ipcountry")
            if coun in ("GR", "CY"):
                lang = "el"
    return lang

@app.route("/")
async def index(status=200, error=None):
    lang = get_lang(request)
    res = await make_response(await render_template("index.html",
        options=[i.name for i in options],
        error=error,
        lang=index_page[lang],
        interval=INTERVAL,
        scenarios=GAME_LENGTH,
        max_length=MAX_LENGTH,
        max_interval=MAX_INTERVAL
    ), status)
    res.set_cookie("lang", lang)
    return res

@app.route("/randomGame")
async def random_game():
    try:    
        game = choice([i for i in games.values() if not i.private])
        return redirect(str(game.game_id))
    except IndexError:
        return await index(status=404, error="game_not_exists")

@app.route("/<game_id>")
async def in_game(game_id):
    if game_id in games:
        ip = request.headers.get('X-Real-Ip')
        if games[game_id].has_player(None, ip):
            return await index(status=404, error="already_joined")
        return await send_from_directory("templates", "in-game.html")
    return await index(status=404, error="game_not_exists")

@app.route("/lang-pack")
async def lang_pack():
    lang = get_lang(request)
    return "lang_pack = {}".format(dumps(in_game_page[lang]))

@app.route("/createGame", methods=["POST"])
async def createGame():
    form = await request.form
    ig_username = form.get("ig_profile")
    if not ig_username:
        return await index(status=400, error="no_ig_name")
    game_opts = [True for _ in range(len(options))]
    for i,v in enumerate(options):
        game_opts[i] = form.get(v.name) == "on"
    no_action1 = False
    if form.get("action1") != "on":
        no_action1 = True
    difficulty = int(form.get("difficulty"))
    if difficulty <= 0 or difficulty > 100:
        raise ValueError("bad_difficulty")
    interval = int(form.get("interval"))
    if interval <= 0 or interval > MAX_INTERVAL:
        raise ValueError("bad_interval")
    length = int(form.get("scenarios"))
    if length <= 0 or length > MAX_LENGTH:
        raise("bad_scenarios")
    private = form.get("private") == "on"
    try:
        game = await Game(game_opts, ig_username, no_action1, interval, length, difficulty, private)
    except (InstagramException, ValueError) as e:
        return await index(status=400, error=str(e))
    game.add_to_games()
    return redirect(str(game.game_id)+"?fp")

@app.route("/joinGame", methods=["GET"])
async def joinGame():
    ip = request.headers.get('X-Real-Ip')
    game_id = request.args.get("game_id")
    if game_id and game_id in games:
        player_name = request.args.get("player_name")
        if not games[game_id].has_player(player_name, ip):
            if len(player_name.strip()) == 0:
                return await make_response("empty_name", 400)
            player = games[game_id].add_player(player_name.strip(), ip)
            return jsonify({"game_id": game_id, "player_id": player.player_id})
        return await make_response("name_in_use_or_already_joined", 400)
    return await make_response("game_not_exists", 400)

@app.route("/startGame", methods=["GET"])
async def startGame():
    game_id = request.args.get("game_id")
    if game_id and game_id in games:
        player_id = request.args.get("player_id")
        if len(games[game_id].players) > 0 and games[game_id].players[0].player_id == player_id:
            games[game_id].start()
            return await make_response("OK", 200)
        return await make_response("not_authorised", 403)
    return await make_response("game_not_exists", 400)

@app.route("/continue", methods=["GET"])
async def continueGame():
    game_id = request.args.get("game_id")
    if game_id and game_id in games:
        player_id = request.args.get("player_id")
        if len(games[game_id].players) > 0 and games[game_id].players[0].player_id == player_id:
            games[game_id].event.set()
            return await make_response("OK", 200)
        return await make_response("not_authorised", 403)
    return await make_response("game_not_exists", 400)

@app.route("/answer", methods=["GET"])
async def answer():
    game_id = request.args.get("game_id")
    if game_id and game_id in games:
        player_id = request.args.get("player_id")
        scenario_id = request.args.get("scenario_id")
        answer = request.args.get("answer").lower() == "true"
        try:
            games[game_id].player_answer(player_id, scenario_id, answer)
            return await make_response("OK", 200)
        except (KeyError, ValueError) as e:
            return await make_response(str(e), 400)

@app.route("/message", methods=["POST"])
async def message():
    form = await request.form
    game_id = form.get("game_id")
    content = form.get("content")[0:200]
    for i in games[game_id].players:
        if i.player_id == form.get("player_id"):
            player_name = i.name
            break
    else:
        return await make_response("player_not_found", 404)
    games[game_id].broadcast(dumps({"event":"new_message", "data":{"name": player_name, "content": content}}))
    return await make_response("OK", 200)

@app.route("/_games", methods=["GET"])
async def list_games():
    return jsonify(list(games.keys()))

@app.websocket("/socket")
async def ws_route():
    auth = loads(await websocket.receive())
    try:
        player_id = auth["player_id"]
        game_id = auth["game_id"]
        queue = games[game_id].get_player_queue(player_id)
    except (KeyError, ValueError):
        return
    try:
        while True:
            await websocket.send(await queue.get())
    except CancelledError:
        games[game_id].remove_player(player_id)
        raise

if getenv("PRODUCTION", "FALSE")=="TRUE":
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    cfg = Config()
    cfg.bind = [getenv("BIND")]
    get_event_loop().run_until_complete(serve(app, cfg))
else:
    app.run("0.0.0.0", port=5010, debug=True, loop=loop)