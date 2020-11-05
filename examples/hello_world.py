import asyncore
import logging

from creepy.query import Remote

remote = Remote('http://localhost:8000')

scope = remote.scope

scope.print('Hello World!!!')
