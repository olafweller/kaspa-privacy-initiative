// Stream public build artifacts through the existing authenticated root terminal.
// No new endpoint/listener; avoids putting a large binary in a shell argument.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
import {createRequire} from 'node:module';
const require = createRequire(path.resolve('.local/codex-cloud-tn10/http-client/package.json'));
const WebSocket = require('ws');
const {HttpsProxyAgent} = require('https-proxy-agent');
const [source, name] = process.argv.slice(2);
if (!source || !/^[a-zA-Z0-9._/-]+$/.test(name) || name.startsWith('/') || name.split('/').includes('..') || /key|private/i.test(name)) throw Error('public experiment artifact paths only');
const token = process.env.TN10_RPC_TOKEN;
if (!token) throw Error('TN10_RPC_TOKEN is required');
const content = fs.readFileSync(source);
const payload = zlib.gzipSync(content).toString('base64');
const expected = crypto.createHash('sha256').update(content).digest('hex');
const marker = 'KPI_TRANSFER_' + crypto.randomBytes(16).toString('hex');
const proxy = process.env.HTTPS_PROXY ?? process.env.https_proxy;
const agent = proxy ? new HttpsProxyAgent(proxy) : undefined;
const ws = new WebSocket('wss://vmi3633138.contaboserver.net/admin/ws', 'tty', {
  agent, headers: {Authorization: `Bearer ${token}`}, handshakeTimeout: 20000, perMessageDeflate: false,
});
let phase = 'init', output = '', finished = false;
const deadline = setTimeout(() => fail('transfer timeout; inspect remote outcome before retry'), 600000);
function fail(message) {if (finished) return; finished = true;clearTimeout(deadline);console.error(message);process.exitCode = 1;ws.terminate();agent?.destroy();}
function send(text) {ws.send(Buffer.concat([Buffer.from('0'), Buffer.from(text)]));}
ws.on('open', () => {
  ws.send(JSON.stringify({AuthToken: '', columns: 240, rows: 40}));
  const ready = Buffer.from(marker + '_READY\n').toString('base64');
  send(`stty -echo -icanon; export PS1=; printf %s '${ready}' | base64 -d\n`);
});
ws.on('error', () => fail('terminal transport error; inspect remote outcome before retry'));
ws.on('unexpected-response', (request, response) => {response.resume();request.destroy();fail(`terminal rejected HTTP ${response.statusCode}`);});
ws.on('message', async frame => {
  const bytes = Buffer.from(frame);
  if (finished || bytes[0] !== 48) return;
  output += bytes.subarray(1).toString().replaceAll('\r\n', '\n');
  if (phase === 'init' && output.includes(marker + '_READY\n')) {
    phase = 'receive'; output = '';
    const program = `import base64,gzip,sys,hashlib,os\np='/opt/kpi-pr31-cloud-20261017/${name}'\nif os.path.exists(p): raise RuntimeError('artifact already exists')\nprint('${marker}_SEND',flush=True)\ndata=gzip.decompress(base64.b64decode(sys.stdin.buffer.read(${payload.length}),validate=True))\nassert hashlib.sha256(data).hexdigest()=='${expected}'\nwith open(p,'xb') as f: f.write(data)\nos.chmod(p,0o700)\nprint('${marker}_DONE:${expected}',flush=True)\n`;
    send(`python3 -c "import base64;exec(base64.b64decode('${Buffer.from(program).toString('base64')}'))"\n`);
  }
  if (phase === 'receive' && output.includes(marker + '_SEND')) {
    phase = 'stream';
    for (let offset = 0; offset < payload.length; offset += 4096) {
      if (finished) return;
      while (ws.bufferedAmount > 65536) await new Promise(resolve => setTimeout(resolve, 10));
      send(payload.slice(offset, offset + 4096));
    }
  }
  if (phase === 'stream' && output.includes(marker + '_DONE:' + expected)) {
    finished = true; clearTimeout(deadline); ws.close(); agent?.destroy();
    console.log(JSON.stringify({remote: '/opt/kpi-pr31-cloud-20261017/' + name, bytes: content.length, sha256: expected}));
  }
});
