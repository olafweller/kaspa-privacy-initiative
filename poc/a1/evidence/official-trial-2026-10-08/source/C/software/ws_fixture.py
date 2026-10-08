"""Loopback-only wRPC JSON fixture server. Never forwards submission to TN10."""
import base64,hashlib,struct,json,socketserver,time
class Server(socketserver.ThreadingTCPServer):allow_reuse_address=True;daemon_threads=True
class Handler(socketserver.StreamRequestHandler):
 def handle(self):
  self.connection.settimeout(60);headers={};total=0;line=self.rfile.readline(8193)
  if not line.startswith(b'GET ') or len(line)>8192:return
  while True:
   line=self.rfile.readline(8193);total+=len(line)
   if len(line)>8192 or total>16384 or len(headers)>20:return
   if line in (b'\r\n',b''):break
   if b':' not in line:return
   k,v=line.decode().split(':',1);headers[k.lower()]=v.strip()
  if 'sec-websocket-key' not in headers:return
  accept=base64.b64encode(hashlib.sha1((headers['sec-websocket-key']+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest()).decode();self.wfile.write(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: '+accept+'\r\n\r\n').encode());self.wfile.flush()
  while True:
   h=self.rfile.read(2)
   if not h:return
   a,b=h;length=b&127
   if length==126:length=struct.unpack('!H',self.rfile.read(2))[0]
   elif length==127:length=struct.unpack('!Q',self.rfile.read(8))[0]
   if length>65536:return
   mask=self.rfile.read(4) if b&128 else None;data=self.rfile.read(length)
   if len(data)!=length:return
   if mask:data=bytes(x^mask[i%4] for i,x in enumerate(data))
   if a&15==8:return
   if a&15==9:self.send(data,10);continue
   request=json.loads(data);self.server.requests.append(request)
   try:response=self.server.callback(request)
   except Exception as exception:
    # Source-owned hook receives no request/body/locals; public error stays generic.
    try:
     callback=getattr(self.server,'failure_callback',None)
     if callback is not None:callback(exception)
    except Exception:pass
    response={'id':request['id'],'method':request['method'],'error':{'code':1,'message':'fixture rejected'}}
   if response is None:return
   self.send(json.dumps(response,separators=(',',':')).encode())
 def send(self,data,op=1):
  n=len(data);h=bytes([128|op,n if n<126 else 126 if n<65536 else 127]);h+=struct.pack('!H',n) if n>=126 and n<65536 else struct.pack('!Q',n) if n>=65536 else b'';self.wfile.write(h+data);self.wfile.flush()
