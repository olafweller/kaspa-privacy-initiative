use crate::Result;
use ark_bn254::Fr;
use ark_ff::PrimeField;
use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

pub type H = [u8; 32];
pub const DEPTH: usize = 2;
pub const PUBLIC_LEN: usize = 410;
pub const CREDIT: u8 = 1;
pub const TRANSFER: u8 = 2;
pub const EXIT: u8 = 3;
pub const RECOVER: u8 = 4;
pub const OWNER_TAG: &[u8] = b"KPI-owner-v1\0";
pub const NOTE_TAG: &[u8] = b"KPI-note-v1\0";
pub const NODE_TAG: &[u8] = b"KPI-node-v1\0";
pub const NF_TAG: &[u8] = b"KPI-nullifier-v1\0";
pub fn hash(b: &[u8]) -> H {
    Sha256::digest(b).into()
}
pub fn domain() -> H {
    #[cfg(not(feature = "tn10-rehearsal"))]
    {
        hash(b"KPI/LOCAL-NO-FUNDING/native-KAS/private-note-experiment-1")
    }
    #[cfg(feature = "tn10-rehearsal")]
    {
        [
            0x0a, 0x71, 0x27, 0x63, 0xb5, 0x3b, 0x58, 0x72, 0xe2, 0x1f, 0x25, 0xea, 0x10, 0x94,
            0x87, 0xaa, 0x8d, 0x79, 0x33, 0x93, 0x2c, 0xc7, 0x61, 0xc5, 0x55, 0x83, 0xda, 0x41,
            0xe9, 0xe0, 0xcf, 0x54,
        ]
    }
}
pub fn tagged(tag: &[u8], fields: &[&[u8]]) -> H {
    let mut b = tag.to_vec();
    b.extend(domain());
    for v in fields {
        b.extend(*v)
    }
    hash(&b)
}
pub fn owner(secret: &H, incoming: &H) -> H {
    tagged(OWNER_TAG, &[secret, incoming])
}
pub fn node(l: &H, r: &H) -> H {
    tagged(NODE_TAG, &[l, r])
}
#[derive(Clone)]
pub struct Note {
    pub owner: H,
    pub incoming: H,
    pub value: u64,
    pub rho: H,
}
impl Note {
    pub fn commitment(&self) -> H {
        tagged(
            NOTE_TAG,
            &[
                &self.owner,
                &self.incoming,
                &self.value.to_le_bytes(),
                &self.rho,
            ],
        )
    }
    pub fn dummy() -> Self {
        Self {
            owner: [0; 32],
            incoming: [0; 32],
            value: 0,
            rho: [0; 32],
        }
    }
    pub fn plaintext(&self) -> Vec<u8> {
        let mut v = vec![1];
        v.extend(domain());
        v.extend(self.owner);
        v.extend(self.incoming);
        v.extend(self.value.to_le_bytes());
        v.extend(self.rho);
        v
    }
    pub fn parse(v: &[u8]) -> Result<Self> {
        if v.len() != 137 || v[0] != 1 || v[1..33] != domain() {
            return Err("note encoding/domain".into());
        }
        let value = u64::from_le_bytes(v[97..105].try_into().unwrap());
        if value == 0 {
            return Err("inactive note".into());
        }
        Ok(Self {
            owner: v[33..65].try_into().unwrap(),
            incoming: v[65..97].try_into().unwrap(),
            value,
            rho: v[105..137].try_into().unwrap(),
        })
    }
}
pub fn nullifier(secret: &H, note: &Note) -> H {
    let mut mac = Hmac::<Sha256>::new_from_slice(secret).unwrap();
    mac.update(NF_TAG);
    mac.update(&domain());
    mac.update(&note.commitment());
    mac.finalize().into_bytes().into()
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Statement {
    pub version: u8,
    pub kind: u8,
    pub domain: H,
    pub verifier: H,
    pub anchor: H,
    pub nullifier: H,
    pub outputs: [H; 2],
    pub delivery: [H; 2],
    pub deposit: H,
    pub deposit_owner: H,
    pub deposit_value: u64,
    pub exit_destination: H,
    pub exit_value: u64,
    pub fee_recipient: H,
    pub fee: u64,
}
impl Statement {
    pub fn new(kind: u8, verifier: H, anchor: H) -> Self {
        Self {
            version: 1,
            kind,
            domain: domain(),
            verifier,
            anchor,
            nullifier: [0; 32],
            outputs: [[0; 32]; 2],
            delivery: [[0; 32]; 2],
            deposit: [0; 32],
            deposit_owner: [0; 32],
            deposit_value: 0,
            exit_destination: [0; 32],
            exit_value: 0,
            fee_recipient: [0; 32],
            fee: 0,
        }
    }
    pub fn bytes(&self) -> Vec<u8> {
        let mut b = vec![self.version, self.kind];
        for x in [
            self.domain,
            self.verifier,
            self.anchor,
            self.nullifier,
            self.outputs[0],
            self.outputs[1],
            self.delivery[0],
            self.delivery[1],
            self.deposit,
            self.deposit_owner,
        ] {
            b.extend(x)
        }
        b.extend(self.deposit_value.to_le_bytes());
        b.extend(self.exit_destination);
        b.extend(self.exit_value.to_le_bytes());
        b.extend(self.fee_recipient);
        b.extend(self.fee.to_le_bytes());
        assert_eq!(b.len(), PUBLIC_LEN);
        b
    }
    pub fn inputs(&self) -> Vec<Fr> {
        self.bytes()
            .chunks(31)
            .map(Fr::from_le_bytes_mod_order)
            .collect()
    }
    pub fn id(&self) -> H {
        tagged(b"KPI-intent-v1\0", &[&self.bytes()])
    }
    pub fn output_count(&self) -> usize {
        if self.kind == CREDIT {
            1
        } else if self.kind == TRANSFER {
            2
        } else {
            0
        }
    }
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Delivery {
    pub commitment: H,
    pub ciphertext: Vec<u8>,
}
impl Delivery {
    pub fn absent() -> Self {
        Self {
            commitment: [0; 32],
            ciphertext: vec![],
        }
    }
}
#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Operation {
    pub statement: Statement,
    pub deliveries: [Delivery; 2],
    pub proof: Vec<u8>,
}
#[derive(Clone, Default, Serialize, Deserialize)]
pub struct Tree {
    pub leaves: Vec<H>,
}
impl Tree {
    pub fn levels(&self) -> Vec<Vec<H>> {
        let mut leaves = self.leaves.clone();
        leaves.resize(1 << DEPTH, [0; 32]);
        let mut levels = vec![leaves];
        for i in 0..DEPTH {
            levels.push(
                levels[i]
                    .chunks_exact(2)
                    .map(|p| node(&p[0], &p[1]))
                    .collect(),
            )
        }
        levels
    }
    pub fn root(&self) -> H {
        self.levels()[DEPTH][0]
    }
    pub fn path(&self, index: usize) -> Result<([H; DEPTH], [bool; DEPTH])> {
        if index >= self.leaves.len() {
            return Err("leaf index".into());
        }
        let levels = self.levels();
        Ok((
            std::array::from_fn(|i| levels[i][(index >> i) ^ 1]),
            std::array::from_fn(|i| (index >> i) & 1 == 1),
        ))
    }
    pub fn append(&mut self, cm: H) -> Result<()> {
        if self.leaves.len() >= 1 << DEPTH || cm == [0; 32] || self.leaves.contains(&cm) {
            return Err("tree capacity/duplicate/zero commitment".into());
        }
        self.leaves.push(cm);
        Ok(())
    }
}
impl Statement {
    pub fn parse(b: &[u8]) -> Result<Self> {
        if b.len() != PUBLIC_LEN
            || b[0] != 1
            || ![CREDIT, TRANSFER, EXIT, RECOVER].contains(&b[1])
            || b[2..34] != domain()
        {
            return Err("statement encoding/version/domain".into());
        }
        let h = |i| -> H { b[i..i + 32].try_into().unwrap() };
        let n = |i| u64::from_le_bytes(b[i..i + 8].try_into().unwrap());
        Ok(Self {
            version: b[0],
            kind: b[1],
            domain: h(2),
            verifier: h(34),
            anchor: h(66),
            nullifier: h(98),
            outputs: [h(130), h(162)],
            delivery: [h(194), h(226)],
            deposit: h(258),
            deposit_owner: h(290),
            deposit_value: n(322),
            exit_destination: h(330),
            exit_value: n(362),
            fee_recipient: h(370),
            fee: n(402),
        })
    }
}
impl Operation {
    pub fn wire_bytes(&self) -> Result<Vec<u8>> {
        if self.proof.len() != 128 {
            return Err("proof encoding size".into());
        }
        let mut b = self.statement.bytes();
        b.extend(&self.proof);
        for i in 0..self.statement.output_count() {
            if self.deliveries[i].ciphertext.len() != 185 {
                return Err("delivery encoding size".into());
            }
            b.extend(&self.deliveries[i].ciphertext)
        }
        Ok(b)
    }
    pub fn parse_wire(bytes: &[u8]) -> Result<Self> {
        if bytes.len() < PUBLIC_LEN + 128 {
            return Err("truncated operation".into());
        }
        let statement = Statement::parse(&bytes[..PUBLIC_LEN])?;
        let count = statement.output_count();
        if bytes.len() != PUBLIC_LEN + 128 + 185 * count {
            return Err("operation size/trailing bytes".into());
        }
        let mut deliveries = [Delivery::absent(), Delivery::absent()];
        for i in 0..count {
            deliveries[i] = Delivery {
                commitment: statement.outputs[i],
                ciphertext: bytes[PUBLIC_LEN + 128 + 185 * i..PUBLIC_LEN + 128 + 185 * (i + 1)]
                    .to_vec(),
            };
        }
        Ok(Self {
            statement,
            deliveries,
            proof: bytes[PUBLIC_LEN..PUBLIC_LEN + 128].to_vec(),
        })
    }
}

impl Operation {
    pub fn check_public(&self, expected_verifier: H) -> Result<()> {
        let op = self;
        let s = &op.statement;
        if s.version != 1
            || s.domain != domain()
            || s.verifier != expected_verifier
            || ![CREDIT, TRANSFER, EXIT, RECOVER].contains(&s.kind)
        {
            return Err("domain/version/verifier/kind".into());
        }
        for (i, d) in op.deliveries.iter().enumerate() {
            let active = i < s.output_count();
            if !active {
                if d.commitment != [0; 32]
                    || !d.ciphertext.is_empty()
                    || s.outputs[i] != [0; 32]
                    || s.delivery[i] != [0; 32]
                {
                    return Err("noncanonical inactive output".into());
                }
            } else if d.ciphertext.len() != 185
                || d.commitment != s.outputs[i]
                || hash(&d.ciphertext) != s.delivery[i]
            {
                return Err("output/delivery binding".into());
            }
        }
        Ok(())
    }
}
