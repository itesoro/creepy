from creepy.subprocess import App


app = App()


@app.route('set_state')
def set_state(state):
    global _state
    _state = state


@app.route('get_state')
def get_state():
    return _state


_state = "initial state"
app.run()
