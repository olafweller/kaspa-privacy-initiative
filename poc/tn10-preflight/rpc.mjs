// Concrete native preflight: reuse the reviewed allowlist, with native u64 IDs.
import {validate} from '../private-native-tn10/read-only.mjs';
export async function request(method,params={},url='ws://127.0.0.1:18210') {
  validate(method,params,url);
  return await new Promise((resolve,reject)=>{
    const socket=new WebSocket(url);
    const timer=setTimeout(()=>finish(Error('read-only RPC timeout')),30000);
    function finish(error,raw){clearTimeout(timer);socket.close();error?reject(error):resolve(raw);}
    socket.addEventListener('open',()=>socket.send(JSON.stringify({id:1,method,params})));
    socket.addEventListener('error',()=>finish(Error('read-only RPC connection failed')));
    socket.addEventListener('message',e=>{
      const raw=String(e.data);
      try {
        // Read the envelope ID only. Never reserialize parsed native u64 data.
        if(JSON.parse(raw).id===1)finish(null,raw);
      } catch {finish(Error('malformed read-only RPC response'));}
    });
  });
}
