#!/usr/bin/env node
// Read-only transport diagnostics. No wallet, secrets, signing or submission.
// An advertised schema is evidence about the interface, not a wire round trip.
import { pathToFileURL } from 'node:url';

const API = 'https://api-tn10.kaspa.org';
export const GENESIS = 'f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370';

export function assess(observations) {
  const blockers = [];
  const ok = name => observations[name]?.status === 200;
  const network = observations.network?.body;
  const node = observations.node?.body;
  if (!ok('network') || network?.networkName !== 'kaspa-testnet-10')
    blockers.push('network identity is missing or is not TN10');
  if (!ok('node') || node?.isSynced !== true || node?.isUtxoIndexed !== true)
    blockers.push('synchronized UTXO-indexed node not established');
  if (node?.serverVersion !== '2.1.0') blockers.push('pinned node version 2.1.0 not reported');
  // Even successful retrieval still needs pinned-header/hash verification in the adapter.
  if (!ok('genesis')) blockers.push('TN10 genesis block could not be retrieved');
  const schemas = observations.openapi?.body?.components?.schemas ?? {};
  const required = {
    SubmitTxInput: ['computeBudget'],
    SubmitTxOutput: ['covenant'],
    SubmitTxModel: ['mass', 'gas', 'payload'],
    UtxoModel: ['covenantId'],
  };
  const missing = Object.entries(required).flatMap(([model, fields]) =>
    fields.filter(field => !Object.hasOwn(schemas[model]?.properties ?? {}, field))
      .map(field => `${model}.${field}`));
  if (!ok('openapi') || missing.length)
    blockers.push(`REST schema does not advertise the lossless A0 interface: ${missing.join(', ')}`);
  return {
    status: blockers.length ? 'blocked_before_wallet_or_funding' : 'requires_adapter_wire_and_genesis_validation',
    funding_allowed: false,
    blockers,
    missing_schema_fields: missing,
  };
}

async function observe(path) {
  try {
    const response = await fetch(`${API}${path}`, {
      signal: AbortSignal.timeout(20000), redirect: 'error',
    });
    const type = response.headers.get('content-type') ?? '';
    const text = await response.text();
    // Never archive HTML error pages: they may contain client IPs or proxy identifiers.
    if (!type.includes('application/json')) return {
      status: response.status,
      content_type: type,
      body_retained: false,
      cloudflare_error_page: /Attention Required!.*Cloudflare/s.test(text),
    };
    return { status: response.status, body: JSON.parse(text) };
  } catch {
    // Avoid exposing credential-bearing URLs or implementation-specific network diagnostics.
    return { status: null, error: 'request failed, redirected, timed out, or returned malformed JSON' };
  }
}

export async function preflight() {
  const paths = {
    network: '/info/network', node: '/info/kaspad', fee: '/info/fee-estimate',
    openapi: '/openapi.json', genesis: `/blocks/${GENESIS}`,
  };
  const entries = await Promise.all(Object.entries(paths).map(async ([name, path]) =>
    [name, await observe(path)]));
  const observations = Object.fromEntries(entries);
  const assessment = assess(observations);
  // Keep a compact schema excerpt and its advertised API version, not unrelated API data.
  if (observations.openapi.body) {
    const { info = {}, components = {} } = observations.openapi.body;
    observations.openapi.body = {
      info: { title: info.title, version: info.version },
      model_properties: Object.fromEntries(['SubmitTxInput', 'SubmitTxOutput', 'SubmitTxModel', 'UtxoModel']
        .map(name => [name, Object.keys(components.schemas?.[name]?.properties ?? {})])),
    };
  }
  return {
    observed_at: new Date().toISOString(), endpoint: API, expected_genesis: GENESIS,
    scope: 'read-only REST preflight; no wallet, UTXO funding, transaction construction or broadcast',
    assessment, observations,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = await preflight();
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  process.exitCode = result.assessment.blockers.length ? 2 : 0;
}
