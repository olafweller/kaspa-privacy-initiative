import { test } from 'node:test';
import assert from 'node:assert/strict';
import { assess } from './a0_tn10_preflight.mjs';

function complete() {
  return {
    network: { status: 200, body: { networkName: 'kaspa-testnet-10' } },
    node: { status: 200, body: { isSynced: true, isUtxoIndexed: true, serverVersion: '2.1.0' } },
    genesis: { status: 200 },
    openapi: { status: 200, body: { components: { schemas: {
      SubmitTxInput: { properties: { computeBudget: {} } },
      SubmitTxOutput: { properties: { covenant: {} } },
      SubmitTxModel: { properties: { mass: {}, gas: {}, payload: {} } },
      UtxoModel: { properties: { covenantId: {} } },
    } } } },
  };
}

test('an advertised complete schema never authorizes funding', () => {
  const result = assess(complete());
  assert.equal(result.blockers.length, 0);
  assert.equal(result.funding_allowed, false);
  assert.equal(result.status, 'requires_adapter_wire_and_genesis_validation');
});
test('mainnet, an unsynced node and absent UTXO indexing fail closed', () => {
  for (const mutate of [x => { x.network.body.networkName = 'kaspa-mainnet'; },
    x => { x.node.body.isSynced = false; }, x => { delete x.node.body.isUtxoIndexed; }]) {
    const input = complete(); mutate(input);
    assert.ok(assess(input).blockers.length > 0);
  }
});
test('missing compute budget, mass or covenant metadata blocks the REST route', () => {
  for (const [model, field] of [['SubmitTxInput', 'computeBudget'], ['SubmitTxModel', 'mass'],
    ['SubmitTxOutput', 'covenant'], ['UtxoModel', 'covenantId']]) {
    const input = complete(); delete input.openapi.body.components.schemas[model].properties[field];
    assert.ok(assess(input).missing_schema_fields.includes(`${model}.${field}`));
  }
});
test('HTTP errors and unavailable observations cannot establish compatibility', () => {
  for (const name of ['genesis', 'openapi', 'network', 'node']) {
    const input = complete(); input[name] = { status: 403 };
    assert.ok(assess(input).blockers.length > 0);
  }
  assert.ok(assess({}).blockers.length > 0);
});
