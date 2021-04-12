import creepy.pipe


with creepy.pipe.connect('pipe_server',
                         hash='425f2b0c5bffd4946c3c4bf5732a61ca4d16a027c424ca69962569c0dd1ff1ef') as session:
    print(session.request('plus', 'Hello ', 'World!!!'))
