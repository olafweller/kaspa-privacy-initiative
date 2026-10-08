// Trusted local checklist binds exact manifest-derived terms. No network/API.
import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
export function uint(v){assert.equal(typeof v,'string');assert.match(v,/^(0|[1-9][0-9]*)$/);const n=BigInt(v);assert.ok(n<=(1n<<64n)-1n);return n;}
export function loadTerms(dir,manifestPath){
 const check=JSON.parse(fs.readFileSync(dir+'/frozen-live-checklist.json'));const file=dir+'/fixed-terms.json';assert.equal(check.fixed_terms_sha256,sha(file));assert.equal(check.manifest_sha256,sha(manifestPath));
 const t=JSON.parse(fs.readFileSync(file)),m=JSON.parse(fs.readFileSync(manifestPath));assert.equal(t.schema,'kpi-native-fixed-term-extraction/v1');assert.equal(t.manifest_sha256,check.manifest_sha256);assert.equal(t.network,'testnet-10');assert.equal(m.network,'testnet-10');assert.equal(t.reserve_sompi,m.states.s0.R);assert.equal(t.credit_sompi,m.states.s0.B);
 for(const n of ['s0_continue','s0_terminal','s1_terminal'])assert.equal(t.branch_fees_sompi[n],m.branches[n].fee);
 const reserve=uint(t.reserve_sompi),feeCap=uint(t.funding_fee_cap_sompi),maximumDebit=uint(t.maximum_wallet_debit_sompi);assert.ok(reserve>0n&&feeCap>0n);assert.equal(reserve+feeCap,maximumDebit);
 return {reserve,feeCap,maximumDebit,manifest:m,terms:t};
}
