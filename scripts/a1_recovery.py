#!/usr/bin/env python3
"""Offline accepted-history recovery; never submits or contacts an original host.

Native v2 Full RPC pages are retained with their request startHash. Acceptance
is an assertion by the independent validated archive/node, not a light-client
proof. A required native callback recomputes txid and validates relevant spends.
Local synthetic tests do not demonstrate live TN10 or machine-loss recovery.
"""
import copy
import hashlib
import struct
from a1_check import Invalid, require, keys, decimal, unhex, full_spk, sha, p2sh, FR


def rpc_uint(value, bits=64):
    if isinstance(value, str):
        return decimal(value, bits)
    require(type(value) is int and 0 <= value < 1 << bits, 'missing/malformed RPC integer')
    return value


def rpc_spk(spk):
    if isinstance(spk,str):
        b=unhex(spk)
        require(len(b)>=2,'missing Full SPK version')
        return b
    require(isinstance(spk, dict) and 'version' in spk and 'script' in spk, 'missing Full SPK')
    version = rpc_uint(spk['version'], 16)
    return struct.pack('>H', version)+unhex(spk['script'])


def canonical_body(tx, full=True):
    """Independent pinned consensus hashing preimage (v1); no defaulted fields."""
    require(isinstance(tx, dict), 'missing accepted body')
    required = ('version','inputs','outputs','lockTime','subnetworkId','gas','payload')
    require(all(k in tx and tx[k] is not None for k in required), 'incomplete Full accepted body')
    require('storageMass' in tx or 'mass' in tx,'missing Full storage mass')
    mass=rpc_uint(tx['storageMass'] if 'storageMass' in tx else tx['mass'])
    require('storageMass' not in tx or 'mass' not in tx or rpc_uint(tx['mass'])==mass,'conflicting storage mass aliases')
    version = rpc_uint(tx['version'],16)
    require(version in (0,1), 'unsupported pinned transaction version')
    b = struct.pack('<HQ',version,len(tx['inputs']))
    for item in tx['inputs']:
        compute_field='computeBudget' if version else 'sigOpCount'
        require(all(k in item and item[k] is not None for k in ('previousOutpoint','signatureScript','sequence',compute_field)), 'incomplete Full input')
        previous = item['previousOutpoint']
        b += unhex(previous['transactionId'],32)+struct.pack('<I',rpc_uint(previous['index'],32))
        sig = unhex(item['signatureScript']) if full else b''
        b += struct.pack('<Q',len(sig))+sig
        if full and version==0:
            b += bytes((rpc_uint(item['sigOpCount'],8),))
        b += struct.pack('<Q',rpc_uint(item['sequence']))
        if full and version>=1:
            b += struct.pack('<H',rpc_uint(item['computeBudget'],16))
    b += struct.pack('<Q',len(tx['outputs']))
    for output in tx['outputs']:
        require(all(k in output for k in ('value','scriptPublicKey')) and (version==0 or 'covenant' in output), 'incomplete Full output')
        spk = rpc_spk(output['scriptPublicKey'])
        b += struct.pack('<QH',rpc_uint(output['value']),int.from_bytes(spk[:2],'big'))
        b += struct.pack('<Q',len(spk)-2)+spk[2:]
        covenant = output.get('covenant')
        if version>=1:b += bytes((covenant is not None,))
        require(version>=1 or covenant is None,'v0 cannot encode covenant')
        if version>=1 and covenant is not None:
            require(isinstance(covenant,dict), 'malformed covenant')
            b += struct.pack('<H',rpc_uint(covenant['authorizingInput'],16))+unhex(covenant['covenantId'],32)
    b += struct.pack('<Q',rpc_uint(tx['lockTime']))+unhex(tx['subnetworkId'],20)+struct.pack('<Q',rpc_uint(tx['gas']))
    payload = unhex(tx['payload']) if full or version==0 else b''
    b += struct.pack('<Q',len(payload))+payload
    if full and (version>=1 or mass>0):
        b += struct.pack('<Q',mass)
    return b


def full_hash(tx):
    return hashlib.blake2b(canonical_body(tx),digest_size=32,key=b'TransactionHash').hexdigest()


def pushes(script):
    """Decode push-only witness, allowing equivalent push opcode encodings."""
    result, pos = [],0
    while pos<len(script):
        op=script[pos];pos+=1
        if op==0:
            result.append(b'');continue
        if op==0x4f:
            result.append(b'\x81');continue
        if 0x51<=op<=0x60:
            result.append(bytes((op-0x50,)));continue
        if 1<=op<=75:
            size=op
        elif op in (0x4c,0x4d,0x4e):
            width={0x4c:1,0x4d:2,0x4e:4}[op]
            require(pos+width<=len(script),'truncated push length')
            size=int.from_bytes(script[pos:pos+width],'little');pos+=width
        else:
            raise Invalid('signature script is not push-only')
        require(pos+size<=len(script),'truncated push data')
        result.append(script[pos:pos+size]);pos+=size
    return result


class Scanner:
    def __init__(self, locator, bundle, native_validate, artifact_index_sha256):
        keys(locator,'network genesis_hex instance_hex s0_txid_hex s0_index s0_amount s0_spk_hex s0_covenant scan_start_hash scan_start_blue_score scan_start_daa_score artifact_index_sha256','locator')
        require(locator['network']==bundle['network']=='testnet-10','network mismatch')
        require(locator['genesis_hex']==bundle['genesis_hex'] and locator['instance_hex']==bundle['instance_hex'],'locator identity mismatch')
        require(locator['artifact_index_sha256']==artifact_index_sha256,'locator artifact index mismatch')
        require(locator['s0_covenant'] is None,'locator covenant present')
        unhex(locator['scan_start_hash'],32)
        decimal(locator['scan_start_blue_score']);decimal(locator['scan_start_daa_score'])
        s0=bundle['states']['s0']
        require(locator['s0_amount']==s0['R'] and locator['s0_spk_hex']==s0['spk_hex'],'stale/wrong S0 terms')
        self.s0=(locator['s0_txid_hex'],decimal(locator['s0_index'],32))
        unhex(self.s0[0],32)
        require(callable(native_validate),'native validation callback is required')
        self.locator=copy.deepcopy(locator);self.bundle=bundle;self.native_validate=native_validate
        self.checkpoint=locator['scan_start_hash'];self.cursor=self.checkpoint
        self.chain=[];self.groups={};self.observations=[]
        self.funding_authenticated=False
        self.state='s0';self.current=self.s0;self.paid=0;self.fees=0

    def _apply_body(self,tx,accepted_seen):
        preimage=canonical_body(tx)
        verbose=tx.get('verboseData')
        require(isinstance(verbose,dict),'missing Full verbose IDs')
        asserted=verbose.get('transactionId');unhex(asserted,32)
        if tx['version']==0:
            require(asserted==hashlib.blake2b(canonical_body(tx,False),digest_size=32,key=b'TransactionID').hexdigest(),'poisoned v0 ID')
        require(verbose.get('hash')==full_hash(tx),'poisoned full transaction hash')
        digest=sha(preimage)
        if asserted in accepted_seen:
            require(accepted_seen[asserted]==digest,'conflicting duplicate accepted body')
            return
        accepted_seen[asserted]=digest
        matches=[i for i,item in enumerate(tx['inputs']) if (item['previousOutpoint']['transactionId'],rpc_uint(item['previousOutpoint']['index'],32))==self.current]
        # All body IDs are recomputed, even bodies unrelated to this instance.
        result=self.native_validate(tx,None if not matches else {'state':self.state,'outpoint':self.current,'bundle':self.bundle})
        require(isinstance(result,dict) and result.get('txid')==asserted and result.get('full_hash')==verbose['hash'],'native body/hash verification failed')
        if asserted==self.s0[0]:
            require(self.s0[1]<len(tx['outputs']),'funding output index absent')
            output=tx['outputs'][self.s0[1]];expected=self.bundle['states']['s0']
            require(rpc_uint(output['value'])==decimal(expected['R']) and rpc_spk(output['scriptPublicKey']).hex()==expected['spk_hex'] and output.get('covenant') is None,'funding body does not authenticate S0 locator')
            self.funding_authenticated=True
        if not matches:
            # A spent former reserve in two distinct currently accepted bodies is contradictory.
            for item in tx['inputs']:
                point=(item['previousOutpoint']['transactionId'],rpc_uint(item['previousOutpoint']['index'],32))
                require(not any(point==x['spent'] for x in self.transitions),'conflicting accepted reserve spend')
            return
        require(self.state in ('s0','s1') and matches==[0] and len(tx['inputs'])==1,'reserve input structure')
        require(result.get('full_valid') is True,'relevant spend lacks native Full proof validation')
        require(tx['version']==1 and rpc_uint(tx['lockTime'])==rpc_uint(tx['gas'])==0 and tx['payload']=='' and tx['subnetworkId']=='00'*20,'wrong transaction envelope')
        witness=pushes(unhex(tx['inputs'][0]['signatureScript']))
        require(len(witness)==5 and list(map(len,witness[:3]))==[32,32,128],'witness ABI')
        require(all(int.from_bytes(x,'little')<FR and x[16:]==bytes(16) for x in witness[:2]),'noncanonical/range tag scalar')
        require(p2sh(witness[4]).hex()==self.bundle['states'][self.state]['spk_hex'],'wrong current redeem script')
        require(witness[3] in ([b'\x00',b'\x01'] if self.state=='s0' else [b'\x01']),'wrong raw selector')
        branch='s0_continue' if witness[3]==b'\x00' else self.state+'_terminal'
        expected=self.bundle['branches'][branch]
        require(len(tx['outputs'])==len(expected['outputs']),'wrong output count')
        for actual,want in zip(tx['outputs'],expected['outputs']):
            require(rpc_uint(actual['value'])==decimal(want['value']) and rpc_spk(actual['scriptPublicKey']).hex()==want['spk_hex'] and actual['covenant'] is None,'wrong ordered output/metadata')
        reserve=decimal(self.bundle['states'][self.state]['R'])
        fee=reserve-sum(rpc_uint(x['value']) for x in tx['outputs'])
        require(fee==decimal(expected['fee']),'wrong fee')
        spent=self.current
        if branch=='s0_continue':
            payout=rpc_uint(tx['outputs'][1]['value']);self.state='s1';self.current=(asserted,0)
        else:
            payout=rpc_uint(tx['outputs'][0]['value']);self.state='terminal';self.current=None
        self.paid+=payout;self.fees+=fee
        self.transitions.append({'branch':branch,'spent':spent,'txid':asserted,'paid':payout,'fee':fee})
        remaining=0 if self.state=='terminal' else decimal(self.bundle['states'][self.state]['R'])
        require(decimal(self.bundle['states']['s0']['R'])==self.paid+self.fees+remaining,'lineage conservation')

    def _replay(self):
        self.state='s0';self.current=self.s0;self.paid=0;self.fees=0;self.transitions=[]
        self.funding_authenticated=False
        seen={}
        for accepting in self.chain:
            for tx in self.groups[accepting]['acceptedTransactions']:
                self._apply_body(tx,seen)

    def page(self,record,horizon):
        """Transactional page application: no cursor advance on incomplete data."""
        keys(record,'startHash response','archived v2 request/response')
        require(record['startHash']==self.cursor,'pagination cursor gap/reorder')
        response=record['response']
        keys(response,'removedChainBlockHashes addedChainBlockHashes chainBlockAcceptedTransactions','v2 response')
        added=response['addedChainBlockHashes'];removed=response['removedChainBlockHashes'];groups=response['chainBlockAcceptedTransactions']
        require(isinstance(added,list) and isinstance(removed,list) and isinstance(groups,list),'page collections')
        require(len(set(added))==len(added) and len(set(removed))==len(removed),'duplicate chain hash in page')
        require(len(groups)==len(added),'pagination missing acceptance groups')
        for h,g in zip(added,groups):
            unhex(h,32)
            require(g.get('chainBlockHeader',{}).get('hash')==h and isinstance(g.get('acceptedTransactions'),list),'reordered/incomplete acceptance groups')
        before=(self.cursor,list(self.chain),dict(self.groups),self.state,self.current,self.paid,self.fees,list(getattr(self,'transitions',[])),self.funding_authenticated)
        try:
            # Removed hashes must form a suffix; restoring any older checkpoint needs external replay.
            if removed:
                require(set(removed).issubset(self.chain),'removed unavailable history: need independent archive/checkpoint')
                first=min(self.chain.index(h) for h in removed)
                require(set(self.chain[first:])==set(removed),'noncontiguous removal history')
                self.chain=self.chain[:first]
                for h in removed:self.groups.pop(h)
                self.cursor=self.chain[-1] if self.chain else self.checkpoint
            require(not any(h in self.groups for h in added),'duplicate/replayed chain page')
            self.chain.extend(added);self.groups.update(zip(added,copy.deepcopy(groups)))
            self._replay()
            if added:self.cursor=added[-1]
            require(added or removed or self.cursor==horizon,'no progress before horizon; pruned/gap')
            self.observations.append(copy.deepcopy(record))
        except Exception:
            self.cursor,self.chain,self.groups,self.state,self.current,self.paid,self.fees,self.transitions,self.funding_authenticated=before
            raise
        return self.report(horizon)

    def reconcile_utxos(self,utxos,horizon):
        require(self.cursor==horizon,'scan horizon not reached')
        points={}
        for item in utxos:
            point=(item['transaction_id'],decimal(item['index'],32))
            require(point not in points,'duplicate UTXO observation');points[point]=item
        if self.state=='terminal':
            require(self.s0 not in points and all((x['txid'],0) not in points for x in self.transitions if x['branch']=='s0_continue'),'terminal reserve still unspent')
        else:
            require(self.current in points,'unknown/missing current UTXO')
            actual=points[self.current];expected=self.bundle['states'][self.state]
            require(actual['value']==expected['R'] and actual['spk_hex']==expected['spk_hex'] and actual['covenant'] is None,'current UTXO terms mismatch')
            if self.state=='s1':require(self.s0 not in points,'S0 and S1 double-counted')
        return self.report(horizon)|{'current_utxo_reconciled':True}

    def report(self,horizon):
        return {'scope':'offline-archive-observation','lineage_history_complete':self.cursor==horizon and self.funding_authenticated,'funding_body_verified':self.funding_authenticated,'state':self.state,'current_outpoint':self.current,'paid':str(self.paid),'fees':str(self.fees),'cursor':self.cursor,'transitions':copy.deepcopy(getattr(self,'transitions',[])),'terminal_spendability_demonstrated':False,'live_tn10_demonstrated':False,'independent_machine_loss_demonstrated':False}


def check_private_backup(bundle,secret,recipient_public_key):
    require(len(secret)==32 and hashlib.sha256(secret).hexdigest()==bundle['claim_commitment_hex'],'wrong claim secret')
    require(len(recipient_public_key)==32 and ('000020'+recipient_public_key.hex()+'ac')==bundle['recipient']['spk_hex'],'wrong recipient recovery key')
    return {'claim_secret_matches':True,'recipient_key_matches':True}
