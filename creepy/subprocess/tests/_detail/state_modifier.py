from creepy.subprocess import App


app = App()


@app.route('modify_and_get_state')
def modify_and_get_state(process):
    curr_state = process.get_state()
    if curr_state != "initial state":
        return curr_state
    new_state = "modified state"
    process.set_state(new_state)
    return new_state


app.run()
