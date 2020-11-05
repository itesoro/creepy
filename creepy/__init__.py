import sys
import pickle
import base64

import cryptography
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes as crypto_hashes

from .query import Context, PICKLE_PROTOCOL


crypto_backend = cryptography.hazmat.backends.default_backend()


context = Context()
context.put(sys.modules[__name__])


async def homepage(request):
    body = b''
    async for chunk in request.stream():
        body += chunk
    try:
        query = pickle.loads(body)
        result = query(context)
    except Exception as ex:
        print(ex)
        result = ex
    data = pickle.dumps(result, PICKLE_PROTOCOL)
    response = Response(data, media_type='application/octet-stream')
    return response


app = Starlette(debug=True, routes=[
    Route('/', homepage, methods=['GET', 'POST']),
])
