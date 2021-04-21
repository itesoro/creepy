import creepy.subprocess


app = creepy.subprocess.App()


@app.route('plus')
def plus(x, y):
    return x + y


app.run()
