from creepy.subprocess import App


app = App()


@app.route('foo')
def foo(a, b, c=1.5, *args, d=False, **kwargs):
    """Foo."""
    return a, b, c, args, d, kwargs


@app.route('bar')
def bar(a, b, c=1.5, *, d=False, **kwargs):
    """Bar."""
    return a, b, c, d, kwargs


app.run()
