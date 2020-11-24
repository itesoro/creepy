import creepy

with creepy.connect('localhost:8000') as remote:
    scope = remote.globals
    scope.world = 'World!!!'
    scope.print('Hello', scope.world)
