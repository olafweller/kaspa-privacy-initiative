import assert from 'node:assert/strict';
import { METHODS, validate } from './read-only.mjs';
for (const method of METHODS) validate(method, {}, 'ws://127.0.0.1:18210');
for (const method of ['submitTransaction', 'submitBlock', 'stop', 'unknown']) {
  assert.throws(() => validate(method, {}, 'ws://127.0.0.1:18210'), /read-only/);
}
assert.throws(() => validate('getServerInfo', {}, 'wss://untrusted.example'), /existing local/);
console.log('Read-only RPC allowlist: 8 permitted methods; mutating methods/foreign endpoints rejected. No RPC executed.');
