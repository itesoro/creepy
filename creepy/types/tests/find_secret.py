import sys

secret = b'Paszword'

prev_buf = b''

while True:
    curr_buf = sys.stdin.buffer.read(256)
    if len(curr_buf) == 0:
        break
    i = (prev_buf + curr_buf).find(b'Paszword')
    if i != -1:
        sys.exit(-1)
    prev_buf = curr_buf
