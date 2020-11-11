import creepy

remote = creepy.connect('localhost:8000')

scope = remote.globals

scope.print('Hello World!!!')
