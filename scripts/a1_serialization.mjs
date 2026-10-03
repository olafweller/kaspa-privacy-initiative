#!/usr/bin/env node
// Offline SDK serialization only. No RPC client, wallet, signing or submission.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';

const archivePin = 'ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124';
const filePins = {
  'kaspa.js': '6d92cb305d0cc2eb26de9e305b7f7a8c17daa130ad478f0b340b50490557dbcf',
  'kaspa_bg.wasm': 'c9657568610ae1d305bc2e1cf85208ceba0d1a7893c4057b38caa8add2ffb0f5',
  'package.json': '8b61fefaba842c41b805291d95b2f9e81778ec590813a6c34eddcd316659b8d0',
};
const options = Object.fromEntries(['--bundle', '--sdk-dir', '--sdk-archive', '--validator', '--reference'].map(key => [key, null]));
for (let i = 2; i < process.argv.length; i += 2) {
  assert.ok(Object.hasOwn(options, process.argv[i]) && process.argv[i + 1], 'expected --bundle DIR --sdk-dir DIR --sdk-archive ZIP --validator BINARY --reference BINARY');
  options[process.argv[i]] = path.resolve(process.argv[i + 1]);
}
assert.ok(Object.values(options).every(Boolean), 'all five explicit paths required');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
assert.equal(sha(fs.readFileSync(options['--sdk-archive'])), archivePin);
for (const [name, pin] of Object.entries(filePins)) assert.equal(sha(fs.readFileSync(path.join(options['--sdk-dir'], name))), pin, name);
const sdk = createRequire(import.meta.url)(path.join(options['--sdk-dir'], 'kaspa.js'));
const read = name => JSON.parse(fs.readFileSync(path.join(options['--bundle'], name), 'utf8'));
const fullSpk = spk => spk.version.toString(16).padStart(4, '0') + spk.script;
function canonical(tx) {
  tx.finalize(); // Never trust a supplied cached transaction ID.
  return {
    version: tx.version, id: tx.id,
    inputs: tx.inputs.map(input => ({ previousOutpoint: {transactionId: input.previousOutpoint.transactionId, index: input.previousOutpoint.index},
      signatureScript: input.signatureScript ?? '', sequence: input.sequence.toString(), sigOpCount: input.sigOpCount, computeBudget: input.computeBudget })),
    outputs: tx.outputs.map(output => ({value: output.value.toString(), scriptPublicKey: fullSpk(output.scriptPublicKey),
      covenant: output.covenant ? {authorizingInput: output.covenant.authorizingInput, covenantId: output.covenant.covenantId.toString()} : null})),
    lockTime: tx.lockTime.toString(), subnetworkId: tx.subnetworkId, gas: tx.gas.toString(), payload: tx.payload, storageMass: tx.storageMass.toString(),
  };
}
function safeSchema(raw, entry) {
  return {...raw, inputs: raw.inputs.map(input => ({transactionId: input.previousOutpoint.transactionId,
    index: input.previousOutpoint.index, signatureScript: input.signatureScript, sequence: input.sequence,
    sigOpCount: input.sigOpCount, computeBudget: input.computeBudget,
    utxo: {...entry, address: null, amount: String(entry.amount), blockDaaScore: String(entry.blockDaaScore)}}))};
}
const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'kpi-a1-sdk-roundtrip.'));
const branches = [];
for (const name of ['s0_continue', 's0_terminal', 's1_terminal']) {
  const request = read(`${name}.validate.json`);
  const expected = read(`${name}.transaction.json`);
  assert.deepEqual(request.transaction, expected);
  const source = sdk.Transaction.deserializeFromSafeJSON(JSON.stringify(safeSchema(expected, request.entry)));
  assert.deepEqual(canonical(source), expected, `${name}: SDK import`);
  // Safe JSON is itself a byte string; this exercises the real SDK serializers,
  // rather than merely JSON.stringify/parse of our own transport representation.
  const wire = source.serializeToSafeJSON();
  const decoded = sdk.Transaction.deserializeFromSafeJSON(wire);
  const decodedBody = canonical(decoded);
  assert.deepEqual(decodedBody, expected, `${name}: SDK byte roundtrip`);
  const numericWire = source.serializeToJSON();
  const numericDecoded = sdk.Transaction.deserializeFromJSON(numericWire);
  assert.deepEqual(canonical(numericDecoded), expected, `${name}: SDK native numeric JSON parser`);
  const safeDecoded = JSON.parse(wire);
  assert.equal(safeDecoded.inputs[0].sequence, expected.inputs[0].sequence, 'u64::MAX string must not lose precision');
  const outputPath = path.join(directory, `${name}.validate.json`);
  fs.writeFileSync(outputPath, JSON.stringify({transaction: decodedBody, entry: request.entry}), {flag: 'wx'});
  const bodyPath = path.join(directory, `${name}.transaction.json`);
  fs.writeFileSync(bodyPath, JSON.stringify(decodedBody), {flag: 'wx'});
  const native = JSON.parse(execFileSync(options['--validator'], ['validate-body', outputPath], {encoding: 'utf8'}));
  const reference = JSON.parse(execFileSync(options['--reference'], ['--body', bodyPath], {encoding: 'utf8'}));
  const measured = read(`${name}.measurement.json`);
  assert.equal(native.full_valid, true);
  assert.equal(native.txid, expected.id);
  assert.equal(native.full_hash, measured.full_hash);
  assert.equal(reference.txid, native.txid);
  assert.equal(reference.full_hash, native.full_hash);
  assert.equal(native.fee, String(measured.fee_sompi));
  const masses = {compute: measured.meter.compute_mass, storage: measured.meter.storage_mass, transient: measured.meter.transient_mass};
  assert.deepEqual(native.native_masses, masses, 'fresh native masses after SDK decode');
  assert.equal(native.consensus_full_hash_preimage_bytes, measured.consensus_full_hash_preimage_bytes);
  // Negative guard: corrupt cached IDs cannot pass exact canonical readback.
  const wrongId = structuredClone(expected); wrongId.id = '00'.repeat(32);
  assert.notDeepEqual(canonical(source), wrongId);
  // Negative guard: replacing a high u64 by an IEEE-754 Number changes its value.
  assert.notEqual(BigInt(Number(expected.inputs[0].sequence)).toString(), expected.inputs[0].sequence);
  const mutationResults = [];
  for (const kind of ['wrong-proof-byte', 'insufficient-budget', 'covenant-some-zero']) {
    const mutatedSchema = safeSchema(expected, request.entry);
    if (kind === 'wrong-proof-byte') {
      const signature = Buffer.from(mutatedSchema.inputs[0].signatureScript, 'hex');
      // Frozen high32/low32 shortest pushes occupy 66 bytes; PUSHDATA1(128)
      // occupies two bytes. Change proof material only, not its push envelope.
      assert.equal(signature[66], 0x4c); assert.equal(signature[67], 128);
      signature[68] ^= 1; mutatedSchema.inputs[0].signatureScript = signature.toString('hex');
    } else if (kind === 'insufficient-budget') mutatedSchema.inputs[0].computeBudget = 1;
    else mutatedSchema.outputs = mutatedSchema.outputs.map((output, index) => index ? output :
      {...output, covenant: {authorizingInput: 0, covenantId: '00'.repeat(32)}});
    const mutant = sdk.Transaction.deserializeFromSafeJSON(JSON.stringify(mutatedSchema));
    const mutation = canonical(mutant);
    assert.notDeepEqual(mutation, expected, `${kind}: exact readback detects mutation`);
    const mutationPath = path.join(directory, `${name}.${kind}.validate.json`);
    fs.writeFileSync(mutationPath, JSON.stringify({transaction: mutation, entry: request.entry}), {flag: 'wx'});
    assert.throws(() => execFileSync(options['--validator'], ['validate-body', mutationPath], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe']}), `${kind}: native Full must reject`);
    mutant.free(); mutationResults.push({mutation: kind, exact_readback_detected: true, native_full_rejected: true});
  }
  branches.push({branch: name, safe_json_bytes: Buffer.byteLength(wire), safe_json_sha256: sha(wire),
    numeric_json_bytes: Buffer.byteLength(numericWire), decoded_transport_sha256: sha(JSON.stringify(decodedBody)),
    txid: native.txid, full_hash: native.full_hash, native_full_after_decode: true,
    independent_hash_encoder_agrees: true, fee_sompi: native.fee,
    literal_witness_and_proof_preserved: true, compute_budget: decodedBody.inputs[0].computeBudget,
    committed_storage_mass: decodedBody.storageMass, output_covenant_none_preserved: decodedBody.outputs.every(output => output.covenant === null),
    decoded_negative_cases: mutationResults,
    native_masses: native.native_masses,
    mass_evidence: 'Fresh native computation from exact SDK-decoded transaction and UTXO; equals original native fixture measurements, not legacy SDK helper estimates.'});
  decoded.free(); numericDecoded.free(); source.free();
}
console.log(JSON.stringify({schema: 'kpi-a1-sdk-roundtrip/v1', observed_at_utc: new Date().toISOString(),
  scope: 'Offline unfunded three-branch final transaction serialization; no RPC, public-chain acceptance or wallet.',
  sdk_version: '2.1.0', sdk_archive_sha256: archivePin, extracted_files_sha256: filePins,
  native_validator_binary_sha256: sha(fs.readFileSync(options['--validator'])), independent_reference_binary_sha256: sha(fs.readFileSync(options['--reference'])),
  retained_decoded_public_requests: directory, branches,
  negative_guards: ['cached wrong ID fails canonical equality', 'IEEE-754 sequence precision loss detected']}, null, 2));
