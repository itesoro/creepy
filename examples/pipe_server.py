import creepy.pipe


app = creepy.pipe.App()

@app.route('plus')
def plus(x, y):
    return x + y


app.run()
