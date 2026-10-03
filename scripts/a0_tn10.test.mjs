import { test } from 'node:test';
import assert from 'node:assert/strict';
import { transaction, canonical } from './a0_tn10.mjs';

// Public, unfunded serialization vector. No private key or spending proof.
function sample() {
  return {version:1,id:'853aa4897fcb0c2c7dd75684a40cac0b8df50fc5612d9987c940c47af538e070',
    inputs:[{previousOutpoint:{transactionId:'42'.repeat(32),index:7},signatureScript:'',
      sequence:'18446744073709551615',sigOpCount:0,computeBudget:1700}],
    outputs:[{value:'1000000000',scriptPublicKey:'000020'+'01'.repeat(32)+'ac',covenant:null}],
    lockTime:'0',subnetworkId:'00'.repeat(20),gas:'0',payload:'',storageMass:'20'};
}

test('native SDK keeps u64::MAX, compute budget, storage mass and explicit no-covenant meaning',()=>{
  const raw=sample(),tx=transaction(raw);
  assert.equal(tx.inputs[0].sequence,18446744073709551615n);
  assert.equal(tx.inputs[0].computeBudget,1700);
  assert.equal(tx.storageMass,20n);
  assert.deepEqual(canonical(tx),raw);
});
test('missing metadata or a covenant substitution cannot silently become None',()=>{
  const missing=sample();delete missing.outputs[0].covenant;
  assert.throws(()=>transaction(missing));
  const changed=sample();changed.outputs[0].covenant={authorizingInput:0,covenantId:'07'.repeat(32)};
  assert.throws(()=>transaction(changed));
});
test('overflow and noninteger budgets do not survive roundtrip',()=>{
  for(const bad of [65536,1700.5]) {const raw=sample();raw.inputs[0].computeBudget=bad;assert.throws(()=>transaction(raw));}
  const raw=sample();raw.inputs[0].sequence='18446744073709551616';assert.throws(()=>transaction(raw));
});
