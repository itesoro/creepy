from creepy.subprocess import Pypen


with Pypen('pypen_child', hash='7be55349d6344e0ecfbf0d109ef92264fb1a4e060b045df7a65e6bcaa247eaab') as process:
    print(process.plus('Hello ', 'World!!!'))
