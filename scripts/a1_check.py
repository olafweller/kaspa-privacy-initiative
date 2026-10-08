#!/usr/bin/env python3
"""Independent, offline A1 parameter inspection. No production-code imports.

This checker establishes byte/accounting consistency with separately supplied
owner intent and compiler/setup observations. Opaque keys cannot establish their
own circuit provenance. It never generates setup material or broadcasts.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import tempfile

MAX_SOMPI = 2_900_000_000_000_000_000
FR = 21888242871839275222246405745257275088548364400416034343698204186575808495617
GENESIS = bytes.fromhex('f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370')
LABEL = b'KPI-A1/TN10/finite/v1\0'
BRANCHES = ('s0_continue', 's0_terminal', 's1_terminal')
PUBLIC = ['txid_lo128', 'txid_hi128', 'index_u32', 'tag_lo128', 'tag_hi128']


class Invalid(ValueError):
    pass


# Fixture harness bundles (public key 1) and testnet-10 test-KAS instances.
SCOPES=('local-unfunded-fixture','testnet-10-test-kas')

def require(condition, message):
    if not condition:
        raise Invalid(message)


def keys(record, expected, label):
    require(isinstance(record, dict) and set(record) == set(expected.split()), f'{label}: exact keys required')


def decimal(value, bits=64, monetary=False):
    require(isinstance(value, str) and re.fullmatch(r'0|[1-9][0-9]*', value), 'noncanonical unsigned decimal')
    n = int(value)
    require(n < 1 << bits and (not monetary or n <= MAX_SOMPI), 'integer out of range')
    return n


def unhex(value, length=None):
    require(isinstance(value, str) and re.fullmatch(r'(?:[0-9a-f]{2})*', value), 'noncanonical hex')
    b = bytes.fromhex(value)
    require(length is None or len(b) == length, 'hex length')
    return b


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f'duplicate JSON key: {key}')
            result[key] = value
        return result
    def bad_float(_):
        raise Invalid('float/NaN JSON values forbidden')
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique,
                      parse_float=bad_float, parse_constant=bad_float)


@dataclass(frozen=True)
class Terms:
    L0: int
    B0: int
    W: int
    f0: int
    fc: int
    f1: int

    def checked(self):
        for value in (self.L0, self.B0, self.W, self.f0, self.fc, self.f1):
            require(type(value) is int and 0 <= value <= MAX_SOMPI, 'invalid sompi')
        require(0 < self.W < self.L0, 'partial payout outside principal')
        require(0 < self.f0 <= self.B0 and 0 < self.fc <= self.B0, 'S0 fee outside credit')
        require(0 < self.f1 <= self.B0-self.fc, 'S1 fee outside credit')
        result = {'R0': self.L0+self.B0, 'L0': self.L0, 'B0': self.B0,
                  'L1': self.L0-self.W, 'B1': self.B0-self.fc,
                  'R1': self.L0-self.W+self.B0-self.fc,
                  'P0': self.L0+self.B0-self.f0,
                  'P1': self.L0-self.W+self.B0-self.fc-self.f1}
        require(all(0 <= n <= MAX_SOMPI for n in result.values()), 'sum exceeds native amount range')
        require(result['R0'] == self.W+result['R1']+self.fc, 'continuation conservation')
        require(result['R0'] == result['P0']+self.f0, 'direct conservation')
        require(result['R1'] == result['P1']+self.f1, 'successor conservation')
        return result


def full_spk(value, kind=None):
    b = unhex(value) if isinstance(value, str) else value
    require(isinstance(b, bytes) and len(b) >= 2 and b[:2] == b'\0\0', 'SPK version must be zero')
    if kind == 'p2pk':
        require(len(b) == 36 and b[2] == 32 and b[-1] == 0xac, 'recipient must be Schnorr P2PK')
        prime=0xfffffffffffffffffffffffffffffffffffffffffffffffffffffffefffffc2f
        x=int.from_bytes(b[3:35],'big');rhs=(x*x*x+7)%prime
        require(x<prime and pow(rhs,(prime-1)//2,prime)==1,'recipient x-only key is not a curve point')
    elif kind == 'p2sh':
        require(len(b) == 37 and b[2:4] == bytes.fromhex('aa20') and b[-1] == 0x87, 'reserve must be P2SH')
    return b


def p2sh(redeem):
    return b'\0\0\xaa\x20'+hashlib.blake2b(redeem, digest_size=32).digest()+b'\x87'


def branch_values(stage, mode, terms, recipient_spk, successor_spk):
    q = terms.checked()
    full_spk(recipient_spk, 'p2pk')
    require((stage, mode) in ((0, 0), (0, 1), (1, 1)), 'unknown stage/mode')
    i = str(stage)
    if mode == 0:
        full_spk(successor_spk, 'p2sh')
        return (q['R0'], q['L0'], q['B0'], terms.fc, q['R1'], q['L1'], q['B1']), [(q['R1'], successor_spk), (terms.W, recipient_spk)]
    fee = terms.f0 if stage == 0 else terms.f1
    return (q['R'+i], q['L'+i], q['B'+i], fee, 0, 0, 0), [(q['P'+i], recipient_spk)]


def encode_context(stage, mode, genesis, instance, commitment, terms, recipient_spk, successor_spk=b''):
    require(genesis == GENESIS and len(instance) == len(commitment) == 32, 'wrong fixed context identity')
    amounts, outputs = branch_values(stage, mode, terms, recipient_spk, successor_spk)
    b = LABEL+genesis+instance+bytes((stage, mode))+commitment
    b += struct.pack('<7Q', *amounts)+bytes((len(outputs),))
    for value, spk in outputs:
        b += struct.pack('<QI', value, len(spk))+spk+b'\0'
    return b


def parse_context(data):
    require(len(data) >= 177 and data[:22] == LABEL and data[22:54] == GENESIS, 'context prefix')
    stage, mode = data[86:88]
    require((stage, mode) in ((0, 0), (0, 1), (1, 1)), 'context stage/mode')
    amounts = struct.unpack_from('<7Q', data, 120)
    require(all(n <= MAX_SOMPI for n in amounts), 'context amount overflow')
    require(mode == 0 or amounts[4:] == (0, 0, 0), 'terminal successor terms')
    count = data[176]
    require(count == (2 if mode == 0 else 1), 'context output count')
    outputs, pos = [], 177
    for _ in range(count):
        require(pos+12 <= len(data), 'truncated output')
        value, size = struct.unpack_from('<QI', data, pos)
        pos += 12
        require(value <= MAX_SOMPI and pos+size < len(data), 'truncated SPK or amount overflow')
        spk = full_spk(data[pos:pos+size])
        pos += size
        require(data[pos] == 0, 'covenant metadata present')
        pos += 1
        outputs.append((value, spk))
    require(pos == len(data), 'trailing context bytes')
    return {'stage': stage, 'mode': mode, 'instance': data[54:86], 'commitment': data[88:120], 'amounts': amounts, 'outputs': outputs}


def tag(context, secret, txid, index):
    require(len(secret) == len(txid) == 32 and type(index) is int and 0 <= index <= 0xffffffff, 'tag suffix widths')
    return hashlib.sha256(context+secret+txid+struct.pack('<I', index)).digest()


def public_inputs(txid, index, t):
    require(len(txid) == len(t) == 32 and type(index) is int and 0 <= index <= 0xffffffff, 'public widths')
    return [txid[:16]+bytes(16), txid[16:]+bytes(16), struct.pack('<I', index)+bytes(28), t[:16]+bytes(16), t[16:]+bytes(16)]


def parse_r1cs(data, evaluate=None):
    """Strict independent sparse R1CS parser/evaluator, without Arkworks imports."""
    magic = b'KPI-A1/R1CS/v1\0'
    require(data.startswith(magic) and len(data) >= len(magic)+20, 'R1CS magic/header')
    public, variables, constraints = struct.unpack_from('<IQQ', data, len(magic))
    require(public == 5 and variables >= 6 and constraints > 0, 'R1CS ABI/counts')
    require(constraints <= (len(data)-len(magic)-20)//24, 'R1CS impossible row count')
    if evaluate is not None:
        require(len(evaluate) == variables and evaluate[0] == 1 and all(type(x) is int and 0 <= x < FR for x in evaluate), 'R1CS assignment')
    pos = len(magic)+20
    for row in range(constraints):
        values = []
        for _ in range(3):
            require(pos+8 <= len(data), 'R1CS truncated count')
            count = struct.unpack_from('<Q', data, pos)[0]
            pos += 8
            require(count <= (len(data)-pos)//40, 'R1CS truncated terms')
            previous, acc = -1, 0
            for _ in range(count):
                index = struct.unpack_from('<Q', data, pos)[0]
                coef = int.from_bytes(data[pos+8:pos+40], 'little')
                pos += 40
                require(previous < index < variables and 0 < coef < FR, 'R1CS unsorted/duplicate/noncanonical term')
                previous = index
                if evaluate is not None:
                    acc = (acc+coef*evaluate[index]) % FR
            values.append(acc)
        if evaluate is not None:
            require(values[0]*values[1] % FR == values[2], f'R1CS unsatisfied row {row}')
    require(pos == len(data), 'R1CS trailing bytes')
    return {'public_count': public, 'variable_count': variables, 'constraint_count': constraints, 'sha256': sha(data)}


def script_push(b):
    if not b:
        return b'\0'
    if len(b) == 1 and 1 <= b[0] <= 16:
        return bytes((0x50+b[0],))
    if b == b'\x81':
        return b'\x4f'
    n = len(b)
    if n <= 75:
        return bytes((n,))+b
    if n <= 255:
        return b'\x4c'+bytes((n,))+b
    if n <= 65535:
        return b'\x4d'+struct.pack('<H', n)+b
    return b'\x4e'+struct.pack('<I', n)+b


def script_num(n):
    require(type(n) is int and -(1 << 63) <= n < 1 << 63, 'script integer range')
    if n == 0:
        return b'\0'
    negative = n < 0
    n = abs(n)
    data = bytearray()
    while n:
        data.append(n & 255)
        n >>= 8
    if data[-1] & 128:
        data.append(128 if negative else 0)
    elif negative:
        data[-1] |= 128
    return script_push(bytes(data))


def expected_body(reserve, outputs, vk):
    """Own raw opcode assembler: exact frozen template, never Rust import."""
    require(len(vk) == 424, 'VK size')
    def eq(op,n): return bytes((op,))+script_num(n)+b'\x9d'
    b = eq(0xb3,1)+eq(0xb9,0)+script_num(0)+eq(0xbe,reserve)+eq(0xb4,len(outputs))
    for index,(amount,spk) in enumerate(outputs):
        b += script_num(index)+eq(0xc2,amount)+script_num(index)+b'\xc3'+script_push(spk)+b'\x88'
        b += script_num(index)+eq(0xd6,-1)
    b += eq(0x82,128)+b'\x6b'+eq(0x82,32)+b'\x78'+eq(0x82,32)+b'\x75'
    b += script_num(0)+b'\xbb'+script_num(8)+b'\xcd'+script_push(bytes(24))+b'\x7e'
    for start,end in ((16,32),(0,16)):
        b += script_num(0)+b'\xba'+script_num(start)+script_num(end)+b'\x7f'+script_push(bytes(16))+b'\x7e'
    return b+script_num(5)+b'\x6c'+script_push(vk)+script_push(b'\x20')+b'\xa6'


def expected_scripts(terms, recipient, successor, vks):
    q = terms.checked()
    def eq(op,n):return bytes((op,))+script_num(n)+b'\x9d'
    envelope=eq(0xb2,1)+b'\xb6'+script_push(bytes(20))+b'\x88'+eq(0xb7,0)+eq(0xc4,0)+eq(0xb5,0)+eq(0x74,4)
    b1=expected_body(q['R1'],[(q['P1'],recipient)],vks['s1_terminal'])
    d1=envelope+script_push(b'\1')+b'\x88'+b1
    require(p2sh(d1)==successor,'successor SPK is not independently reconstructed D1')
    bc=expected_body(q['R0'],[(q['R1'],successor),(terms.W,recipient)],vks['s0_continue'])
    bt=expected_body(q['R0'],[(q['P0'],recipient)],vks['s0_terminal'])
    d0=envelope+b'\x76'+script_push(b'\0')+b'\x87\x63\x75'+bc+b'\x67'+script_push(b'\1')+b'\x88'+bt+b'\x68'
    return {'s0':d0,'s1':d1}


def disassemble(script):
    """Raw instruction boundaries for reviewer-readable exact literal inspection."""
    rows=[];pos=0
    while pos<len(script):
        start=pos;op=script[pos];pos+=1;data=None
        if 1<=op<=75:
            size=op
        elif op in (0x4c,0x4d,0x4e):
            width={0x4c:1,0x4d:2,0x4e:4}[op]
            require(pos+width<=len(script),'truncated script push length')
            size=int.from_bytes(script[pos:pos+width],'little');pos+=width
        else:
            size=None
        if size is not None:
            require(pos+size<=len(script),'truncated script literal')
            data=script[pos:pos+size].hex();pos+=size
        rows.append({'offset':str(start),'opcode_hex':f'{op:02x}','data_hex':data})
    return rows


def canonical_json(record):
    return json.dumps(record,sort_keys=True,separators=(',',':')).encode()


def expected_report(counts,scripts):
    return {'schema':'kpi-a1-independent-check/v1','scope':'local-unfunded-fixture','parameter_consistency':True,'r1cs':counts,'scripts_sha256':{n:sha(d) for n,d in scripts.items()},'setup_provenance':'external observation receipt checked for consistency; opaque keys cannot attest their relation; independent supervision/authenticity remains a reviewer obligation','shared_dependency':'pinned Arkworks SHA256 gadget/field libraries','funding_authorized':False}


def address_for_spk(spk):
    """Independent Kaspa cashaddr encoding of standard Schnorr P2PK."""
    full_spk(spk,'p2pk')
    alphabet='qpzry9x8gf2tvdw0s3jn54khce6mua7l'
    raw=b'\0'+spk[3:35]
    acc=0;bits=0;groups=[]
    for byte in raw:
        acc=(acc<<8)|byte;bits+=8
        while bits>=5:
            bits-=5;groups.append((acc>>bits)&31)
    if bits:groups.append((acc<<(5-bits))&31)
    values=[ord(x)&31 for x in 'kaspatest']+[0]+groups+[0]*8
    mod=1
    for value in values:
        top=mod>>35;mod=((mod&0x07ffffffff)<<5)^value
        for i,generator in enumerate((0x98f2bc8e61,0x79b76d99e2,0xf33e5fb3c4,0xae2eabe2a8,0x1e4f43e470)):
            if top>>i&1:mod^=generator
    mod^=1
    checks=[(mod>>(5*(7-i)))&31 for i in range(8)]
    return 'kaspatest:'+''.join(alphabet[n] for n in groups+checks)


def artifact(root, descriptor, r1cs=False):
    keys(descriptor,'path bytes sha256'+(' format' if r1cs else ''),'artifact')
    require(not r1cs or descriptor['format']=='KPI-A1/R1CS/v1','R1CS format')
    path=descriptor['path']
    require(isinstance(path,str) and path and not Path(path).is_absolute() and all(p not in ('','.','..') for p in path.split('/')),'unsafe artifact path')
    base=Path(root).resolve();target=(base/path).resolve()
    require(target.is_relative_to(base) and target.is_file(),'missing/escaping artifact')
    data=target.read_bytes()
    require(len(data)==decimal(descriptor['bytes']) and sha(data)==descriptor['sha256'],'artifact size/hash mismatch')
    unhex(descriptor['sha256'],32)
    return data


def check_bundle(root, owner_intent, reference_r1cs_dir, receipt, validate_keys):
    """Inspect immutable public bundle against independently retained intent.

    validate_keys(pk,vk) must use validated Arkworks parsing with no trailing
    bytes. reference_r1cs_dir is produced by independent a1_reference compilation
    of the independently reconstructed contexts, NOT copied from the bundle.
    receipt is supplied by the reviewer outside the original-host bundle.
    """
    bundle=load_json(Path(root)/'manifest.json')
    keys(bundle,'schema protocol network genesis_hex instance_hex claim_commitment_hex recipient states branches abi envelope pins inspection recovery','bundle')
    keys(owner_intent,'schema scope genesis_hex instance_hex claim_commitment_hex recipient_spk_hex terms pins','owner intent')
    require(owner_intent['schema']=='kpi-a1-intent/v1' and owner_intent['scope'] in SCOPES,'intent schema/scope')
    require(bundle['schema']=='kpi-a1-artifacts/v1' and bundle['protocol']==LABEL[:-1].decode() and bundle['network']=='testnet-10','bundle protocol identity')
    for field in ('genesis_hex','instance_hex','claim_commitment_hex'):
        require(bundle[field]==owner_intent[field],'owner-intent identity mismatch: '+field)
        unhex(bundle[field],32)
    require(unhex(bundle['genesis_hex'])==GENESIS,'wrong genesis')
    recipient=bundle['recipient'];keys(recipient,'address spk_version spk_hex','recipient')
    recipient_spk=full_spk(recipient['spk_hex'],'p2pk')
    require(recipient['spk_version']=='0' and recipient['spk_hex']==owner_intent['recipient_spk_hex'] and recipient['address']==address_for_spk(recipient_spk),'owner-intent recipient mismatch')
    keys(owner_intent['terms'],'l0 b0 w f0 fc f1','intent terms')
    t=Terms(*(decimal(owner_intent['terms'][name],monetary=True) for name in ('l0','b0','w','f0','fc','f1')));q=t.checked()
    states=bundle['states'];keys(states,'s0 s1','states')
    redeems={}
    for i in (0,1):
        name='s'+str(i);state=states[name];keys(state,'stage R L B redeem spk_hex','state')
        require(decimal(state['stage'],8)==i,'state stage')
        for quantity in ('R','L','B'):
            require(decimal(state[quantity],monetary=True)==q[quantity+str(i)],'state accounting mismatch')
        redeems[name]=artifact(root,state['redeem'])
        require(full_spk(state['spk_hex'],'p2sh')==p2sh(redeems[name]),'P2SH/redeem mismatch')
    keys(bundle['branches'],' '.join(BRANCHES),'branches')
    vks={};counts={};hash_records={}
    for name,(stage,mode) in zip(BRANCHES,((0,0),(0,1),(1,1))):
        branch=bundle['branches'][name]
        keys(branch,'stage mode selector_hex fee next_R next_L next_B outputs context_hex context_sha256 relation_id r1cs pk vk','branch')
        require(decimal(branch['stage'],8)==stage and decimal(branch['mode'],8)==mode and branch['selector_hex']==('00' if mode==0 else '01'),'branch stage/mode/selector')
        values,outs=branch_values(stage,mode,t,recipient_spk,unhex(states['s1']['spk_hex']))
        for field,n in zip(('fee','next_R','next_L','next_B'),values[3:]):
            require(decimal(branch[field],monetary=True)==n,'branch accounting mismatch')
        require(isinstance(branch['outputs'],list) and len(branch['outputs'])==len(outs),'branch output count')
        for index,(output,(amount,spk)) in enumerate(zip(branch['outputs'],outs)):
            keys(output,'index value spk_hex covenant','branch output')
            require(decimal(output['index'],32)==index and decimal(output['value'],monetary=True)==amount and output['spk_hex']==spk.hex() and output['covenant'] is None,'branch ordered outputs')
        context=encode_context(stage,mode,GENESIS,unhex(bundle['instance_hex']),unhex(bundle['claim_commitment_hex']),t,recipient_spk,unhex(states['s1']['spk_hex']))
        require(branch['context_hex']==context.hex() and branch['context_sha256']==sha(context),'independent context mismatch')
        require(branch['relation_id']=='sha256-preimage-and-outpoint-tag/v1','relation identity')
        matrices=artifact(root,branch['r1cs'],True);counts[name]=parse_r1cs(matrices)
        reference=(Path(reference_r1cs_dir)/(name+'.r1cs')).read_bytes()
        parse_r1cs(reference)
        require(matrices==reference,'independent compiled R1CS mismatch')
        pk=artifact(root,branch['pk']);vk=artifact(root,branch['vk']);vks[name]=vk
        require(len(vk)==424 and len(pk)>424 and pk[:424]==vk,'PK/VK compressed mapping')
        require(int.from_bytes(vk[224:232],'little')==6,'VK must have six gamma_abc elements')
        require(callable(validate_keys) and validate_keys(pk,vk) is True,'validated Arkworks PK/VK parsing required')
        hash_records[name]={'context_sha256':sha(context),'r1cs_sha256':sha(matrices),'pk_sha256':sha(pk),'vk_sha256':sha(vk)}
    scripts=expected_scripts(t,recipient_spk,unhex(states['s1']['spk_hex']),vks)
    require(scripts==redeems,'independent exact script template mismatch')
    abi=bundle['abi'];keys(abi,'verifier_tag_hex public_inputs scalar_bytes proof_bytes vk_bytes witness_order','abi')
    require(abi=={'verifier_tag_hex':'20','public_inputs':PUBLIC,'scalar_bytes':'32','proof_bytes':'128','vk_bytes':'424','witness_order':['tag_hi','tag_lo','proof','selector','redeem']},'verifier ABI mismatch')
    envelope=bundle['envelope'];keys(envelope,'tx_version subnetwork_hex gas payload_hex lock_time sequence_policy compute_budgets','envelope')
    require({k:v for k,v in envelope.items() if k!='compute_budgets'}=={'tx_version':'1','subnetwork_hex':'00'*20,'gas':'0','payload_hex':'','lock_time':'0','sequence_policy':'relative-lock-disabled'},'envelope mismatch')
    keys(envelope['compute_budgets'],' '.join(BRANCHES),'budgets')
    require(all(decimal(n,16)>0 for n in envelope['compute_budgets'].values()),'zero budget')
    pins=bundle['pins'];keys(pins,'kpi_source_commit rusty_kaspa_commit rust_toolchain target cargo_lock_sha256 dependency_versions sdk_archive_sha256 node_archive_sha256 build_commands checker_source_commit','pins')
    require(pins==owner_intent['pins'],'separately retained source/toolchain pins mismatch')
    for field in ('kpi_source_commit','rusty_kaspa_commit','checker_source_commit'):unhex(pins[field],20)
    require(pins['rusty_kaspa_commit']=='01b532e8b553523216471682649693af92f0fd16' and pins['rust_toolchain']=='1.91.0' and pins['target']=='x86_64-unknown-linux-gnu','baseline pin mismatch')
    for field in ('cargo_lock_sha256','sdk_archive_sha256','node_archive_sha256'):unhex(pins[field],32)
    require(pins['sdk_archive_sha256']=='ba674e109ff5dd8bedc4dc2ee8a5ecdf4b600b1178a541d77888ec58310b6124' and pins['node_archive_sha256']=='5ba61c05c013a4856491a8a17666fa73f7bd2aecbfed8affe8ffdc077361dad8','archive pins')
    require(isinstance(pins['dependency_versions'],dict) and pins['dependency_versions'] and isinstance(pins['build_commands'],list) and all(isinstance(x,str) and x for x in pins['build_commands']),'missing build/dependency pins')
    inspection=bundle['inspection'];keys(inspection,'normalized_r1cs_sha256 script_disassembly_sha256 checker_report_sha256 setup_observation_receipt_sha256','inspection')
    require(inspection['normalized_r1cs_sha256']=={n:counts[n]['sha256'] for n in BRANCHES},'normalized matrix hash map')
    for field in ('script_disassembly_sha256','checker_report_sha256','setup_observation_receipt_sha256'):unhex(inspection[field],32)
    disassembly=canonical_json({name:disassemble(data) for name,data in scripts.items()})
    require((Path(root)/'disassembly.json').read_bytes()==disassembly and inspection['script_disassembly_sha256']==sha(disassembly),'independent disassembly content/hash mismatch')
    # Receipt encoding is a supporting observation protocol, not an artifact-schema extension.
    keys(receipt,'schema scope observer build_pins branches setup_randomness_retained','setup receipt')
    require(receipt['schema']=='kpi-a1-setup-observation/v1' and receipt['scope']==owner_intent['scope'] and isinstance(receipt['observer'],str) and receipt['observer'] and receipt['setup_randomness_retained'] is False,'missing supervised setup observation')
    require(receipt['build_pins']==pins and receipt['branches']==hash_records,'setup receipt does not bind reviewed artifacts')
    receipt_bytes=canonical_json(receipt)
    require(inspection['setup_observation_receipt_sha256']==sha(receipt_bytes),'independently retained receipt hash mismatch')
    recovery=bundle['recovery'];keys(recovery,'source_id network_genesis_hex retention_start_hash retention_policy locator_schema private_backup_items public_artifact_items','recovery')
    require(recovery['network_genesis_hex']==GENESIS.hex() and recovery['locator_schema']=='kpi-a1-locator/v1','recovery identity')
    unhex(recovery['retention_start_hash'],32)
    for field in ('source_id','retention_policy'):require(isinstance(recovery[field],str) and recovery[field],'missing recovery source/retention')
    for field in ('private_backup_items','public_artifact_items'):require(isinstance(recovery[field],list) and recovery[field] and all(isinstance(x,str) and x for x in recovery[field]),'missing recovery inventory')
    report=expected_report(counts,scripts)
    report_bytes=canonical_json(report)
    require((Path(root)/'independent-checker-report.json').read_bytes()==report_bytes and inspection['checker_report_sha256']==sha(report_bytes),'completed independent report content/hash mismatch')
    return report


def key_validator(binary):
    binary=str(Path(binary).resolve())
    def validate(pk,vk):
        with tempfile.TemporaryDirectory(prefix='kpi-a1-keycheck-') as temp:
            p=Path(temp)/'pk.bin';v=Path(temp)/'vk.bin'
            p.write_bytes(pk);v.write_bytes(vk)
            command=subprocess.run([binary,'--keys',str(p),str(v)],capture_output=True,text=True,check=True)
            return json.loads(command.stdout).get('validated') is True
    return validate


def independent_references(binary, owner_intent, bundle, directory):
    """Run independently wired compiler on independently encoded context bytes."""
    binary=str(Path(binary).resolve());directory=Path(directory)
    keys(owner_intent['terms'],'l0 b0 w f0 fc f1','intent terms')
    t=Terms(*(decimal(owner_intent['terms'][name],monetary=True) for name in ('l0','b0','w','f0','fc','f1')))
    t.checked()
    for branch,(stage,mode) in zip(BRANCHES,((0,0),(0,1),(1,1))):
        context=encode_context(stage,mode,unhex(owner_intent['genesis_hex'],32),unhex(owner_intent['instance_hex'],32),unhex(owner_intent['claim_commitment_hex'],32),t,full_spk(owner_intent['recipient_spk_hex'],'p2pk'),full_spk(bundle['states']['s1']['spk_hex'],'p2sh'))
        context_file=directory/(branch+'.hex');context_file.write_text(context.hex())
        command=subprocess.run([binary,str(context_file),owner_intent['claim_commitment_hex'],str(directory/(branch+'.r1cs'))],capture_output=True,text=True,check=True)
        result=json.loads(command.stdout)
        require(result.get('public_count')==5 and result.get('sha256')==sha((directory/(branch+'.r1cs')).read_bytes()),'reference compiler output disagreement')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('bundle',type=Path)
    parser.add_argument('--intent',type=Path,required=True,help='independently retained owner intent')
    parser.add_argument('--receipt',type=Path,required=True,help='independently retained setup observation')
    parser.add_argument('--reference-binary',type=Path,required=True,help='pinned independently wired a1_reference executable')
    args=parser.parse_args()
    intent=load_json(args.intent);receipt=load_json(args.receipt)
    with tempfile.TemporaryDirectory(prefix='kpi-a1-reference-') as directory:
        independent_references(args.reference_binary,intent,load_json(args.bundle/'manifest.json'),directory)
        report=check_bundle(args.bundle,intent,directory,receipt,key_validator(args.reference_binary))
    print(json.dumps(report,sort_keys=True,indent=2))


if __name__=='__main__':
    main()
