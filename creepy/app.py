import os
import sys
import pickle
import base64
import types

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from .query import Context, PICKLE_PROTOCOL


def make_module():
    module = types.ModuleType('')
    module.open = open
    module.print = print
    module.os = os
    return module


context = Context()
context.put(make_module())


async def homepage(request):
    body = b''
    async for chunk in request.stream():
        body += chunk
    try:
        query = pickle.loads(body)
        result = query(context)
    except Exception as ex:
        result = ex
    data = pickle.dumps(result, PICKLE_PROTOCOL)
    response = Response(data, media_type='application/octet-stream')
    return response


app = Starlette(debug=True, routes=[
    Route('/', homepage, methods=['GET', 'POST']),
])
