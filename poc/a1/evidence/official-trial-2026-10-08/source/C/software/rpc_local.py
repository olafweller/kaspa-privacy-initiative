def require(condition, message):
    if not condition:
        raise ValueError(message)
import socket, struct, json, os, base64, hashlib

class RPC:
    METHODS = {'getServerInfo', 'getSyncStatus', 'getBlockDagInfo', 'getBlock', 'getVirtualChainFromBlockV2', 'getUtxosByAddresses'}

    def __init__(self):
        self.s = socket.create_connection(('127.0.0.1', 18210), 5)
        self.s.settimeout(45)
        self.buf = b''
        self.n = 0
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall(('GET / HTTP/1.1\r\nHost: 127.0.0.1:18210\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: ' + key + '\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        while b'\r\n\r\n' not in self.buf:
            p = self.s.recv(4096)
            if not p:
                raise EOFError()
            self.buf += p
        h, self.buf = self.buf.split(b'\r\n\r\n', 1)
        expected = base64.b64encode(hashlib.sha1((key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        require(b' 101 ' in h and expected in h, 'invalid websocket handshake')

    def read(self, n):
        while len(self.buf) < n:
            p = self.s.recv(min(65536, max(4096, n - len(self.buf))))
            if not p:
                raise EOFError()
            self.buf += p
        p, self.buf = (self.buf[:n], self.buf[n:])
        return p

    def send(self, data, op=1):
        p = data if isinstance(data, bytes) else json.dumps(data, separators=(',', ':')).encode()
        n = len(p)
        m = os.urandom(4)
        h = bytes([128 | op, 128 | (n if n < 126 else 126 if n < 65536 else 127)])
        if n >= 126:
            h += struct.pack('!H' if n < 65536 else '!Q', n)
        self.s.sendall(h + m + bytes((x ^ m[i % 4] for i, x in enumerate(p))))

    def receive(self):
        data = bytearray()
        while True:
            a, b = self.read(2)
            n = b & 127
            if n == 126:
                n = struct.unpack('!H', self.read(2))[0]
            elif n == 127:
                n = struct.unpack('!Q', self.read(8))[0]
            if n + len(data) > 64 * 1024 * 1024:
                raise ValueError('RPC size limit; capture stopped safely')
            m = self.read(4) if b & 128 else None
            p = self.read(n)
            if m:
                p = bytes((x ^ m[i % 4] for i, x in enumerate(p)))
            if a & 15 == 9:
                self.send(p, 10)
                continue
            if a & 15 == 8:
                raise EOFError('RPC closed')
            if a & 15 not in (0, 1):
                raise ValueError('unexpected RPC frame')
            data.extend(p)
            if a & 128:
                return json.loads(data)

    def call(self, method, params):
        if method not in self.METHODS:
            raise ValueError('RPC method not allowed')
        self.n += 1
        self.send({'id': self.n, 'method': method, 'params': params})
        r = self.receive()
        require(r.get('id') == self.n and r.get('method') == method, 'RPC response identity mismatch')
        if 'error' in r:
            raise ValueError(r['error'].get('message', 'RPC failure'))
        return r['params']

    def close(self):
        self.s.close()
