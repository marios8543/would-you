Vue.config.devtools = true
const app = new Vue({
    el: "#mainWrap",
    data: {
        ws: new WebSocket(`${location.protocol == "https:" ? "wss" : "ws"}://${window.location.hostname}/socket`),
        //ws: new WebSocket("ws://localhost:5010/socket"),
        player_name: "",
        player_id: "",
        game_id: "",
        interval: 10,
        join_error: "",
        game: {
            action: "",
            money: 0,
            user: {
                name: "",
                username: "",
                profile_pic: ""
            },
            chances: {
                option4: 0,
                option2: 0,
                option3: 0,
                option5: 0,
                option1: false
            }
        },
        players: {},
        game_in_progress: false,
        first_player: false,
        countdown: 0,
        timer: null,
        lang: lang_pack,
        messages: [{name:"System", content: "Welcome to Would You ?!"}],
        message_input: ""
    },
    methods: {
        joinGame: function () {
            let _this = this;
            $.getJSON("/joinGame", {
                game_id: app.game_id,
                player_name: app.player_name
            }, function (data) {
                _this.player_id = data.player_id;
                _this.ws.send(JSON.stringify(data));
                $("#close_modal").click();
            }).fail(function(j, text, des) {
                _this.join_error = text;
            });
        },
        startGame: function () {
            $.get("/startGame", {
                game_id: this.game_id,
                player_id: this.player_id
            });
        },
        answer: function (a) {
            $.get("/answer", {
                game_id: this.game_id,
                player_id: this.player_id,
                scenario_id: this.game.id,
                answer: a
            });
        },
        continueGame: function() {
            $.get("/continue", {
                game_id: this.game_id,
                player_id: this.player_id
            });                    
        },
        addPlayer: function(name) {
            this.players[name] = {answer:2, balance:0};
            this.$forceUpdate();
        },
        removePlayer: function(name) {
            delete this.players[name];
            this.$forceUpdate();
        },
        updatePlayer: function(name, details) {
            app.players[name] = details;
            this.$forceUpdate();
        },
        sendMessage: function() {
            if (this.message_input.length > 0) {
                let _this = this;
                $.post("/message", {
                    game_id: this.game_id,
                    player_id: this.player_id,
                    content: this.message_input
                }, function() {
                    _this.message_input = "";
                });
            }
        }
    },
    mounted: function () {
        $("#display_modal").click();
    }
});

function handleWebsocket(message) {
    let data = JSON.parse(message.data)
    switch (data["event"]) {
        case "player_add":
            app.addPlayer(data.data.name);
            break;
        case "player_remove":
            app.removePlayer(data.data.name);
            break;
        case "player_answer":
            app.updatePlayer(data.data.player.name, data.data.details);
            break;
        case "game_start":
            app.game_in_progress = true;
            break;
        case "game_end":
            app.game_in_progress = false;
            break;
        case "new_scenario":
            for(const key of Object.keys(app.players)) {
                app.players[key].answer = 2;
            }
            app.game = data.data;
            break;
        case "new_message":
            app.messages.push(data.data);
            break;
    }
}
app.ws.onmessage = handleWebsocket;

const urlParams = new URLSearchParams(window.location.search);
if(urlParams.has("fp")) app.first_player = true;

app.game_id = window.location.href.split("/").pop();
if(app.game_id.includes("?")) {
    app.game_id = app.game_id.split("?")[0];
}
history.replaceState({id: 'in_game'}, 'Would you ?!', `/${app.game_id}`);
delete lang_pack;