import io
import os
import asyncio
import types
import secrets
from enum import IntEnum

from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Route

from .protocol import HandshakeProtocol, Session
from .protocol.constants import SESSION_ID_SIZE, NONCE_SIZE
from .query import pickle


def make_module():
    import importlib
    module = types.ModuleType('')
    module.__import__ = importlib.import_module
    module.open = open
    module.print = print
    module.os = os
    return module


class HttpStatusCodes(IntEnum):
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403


shared_module = make_module()
sessions = {}
handshake = HandshakeProtocol()


def make_response(data=b'', status_code=HttpStatusCodes.OK):
    return Response(data, status_code, media_type='application/octet-stream')


async def request_raw_body(request):
    body = b''
    async for chunk in request.stream():
        body += chunk
    return body


async def handshake_salt(request):
    return make_response(handshake.salt)


async def handshake_hi(request):
    try:
        bob = handshake.who_r_u(await request_raw_body(request))
    except ValueError as e:
        await asyncio.sleep(1)
        return make_response(str(e), HttpStatusCodes.BAD_REQUEST)
    session_id = secrets.token_bytes(SESSION_ID_SIZE)
    if session_id in sessions:
        return make_response(b"Sorry Bob, I have enough friends", HttpStatusCodes.FORBIDDEN)
    cipher, ciphertext = handshake.hi_bob(bob, session_id)
    session = Session(cipher)
    session.scope.put(shared_module)
    sessions[session_id] = session
    return make_response(ciphertext)


async def doit(request):
    body = await request_raw_body(request)
    try:
        session_id, ciphertext = body[:SESSION_ID_SIZE], body[SESSION_ID_SIZE:]
        session = sessions.get(session_id)
        if session is None:
            await asyncio.sleep(1)
            return make_response(b"Invalid session", HttpStatusCodes.BAD_REQUEST)
        message = session.cipher.decrypt(ciphertext)
        nonce = int.from_bytes(message[:NONCE_SIZE], 'big')
        if nonce <= session.last_nonce:
            await asyncio.sleep(1)
            return make_response(b"Login: admin\nPassword: ytrewq54321")
    except Exception:
        await asyncio.sleep(1)
        return make_response(b'', HttpStatusCodes.BAD_REQUEST)
    try:
        f = io.BytesIO(message[NONCE_SIZE:])
        query = []
        try:
            while True:
                query.append(pickle.load(f, session.scope))
        except EOFError:
            pass
        session.last_nonce = nonce
        if len(query) > 0:
            result = query[0](session.scope)
        else:
            result = None
        for i in range(1, len(query)):
            none_result = query[i](session.scope)
            assert none_result is None
    except Exception as ex:
        result = ex
    data = session.cipher.encrypt(pickle.dumps(result))
    return make_response(data)


app = Starlette(debug=False, routes=[
    Route('/salt', handshake_salt, methods=['POST']),
    Route('/hi', handshake_hi, methods=['POST']),
    Route('/', doit, methods=['POST'])
])
