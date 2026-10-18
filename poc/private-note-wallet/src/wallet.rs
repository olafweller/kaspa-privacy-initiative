use crate::{
    circuit::{WalletCircuit, Witness},
    protocol::*,
    Result,
};
use ark_bn254::Bn254;
use ark_ec::AffineRepr;
use ark_groth16::{prepare_verifying_key, Groth16, PreparedVerifyingKey, Proof, ProvingKey};
use ark_serialize::{CanonicalDeserialize, CanonicalSerialize};
use crypto_box::{PublicKey, SecretKey};
use rand::{rngs::OsRng, RngCore};

#[derive(Clone)]
pub struct Address {
    pub owner: H,
    pub incoming: H,
}
pub struct Wallet {
    secret: H,
    view: SecretKey,
    pub address: Address,
}
impl Wallet {
    pub fn new() -> Self {
        let mut secret = [0; 32];
        OsRng.fill_bytes(&mut secret);
        let view = SecretKey::generate(&mut OsRng);
        let incoming = *view.public_key().as_bytes();
        Self {
            secret,
            view,
            address: Address {
                owner: owner(&secret, &incoming),
                incoming,
            },
        }
    }
    pub fn note(&self, value: u64) -> Note {
        Note::for_address(&self.address, value)
    }
    pub fn witness(
        &self,
        input: Note,
        outputs: [Note; 2],
        siblings: [H; DEPTH],
        directions: [bool; DEPTH],
    ) -> Witness {
        Witness {
            secret: self.secret,
            input,
            outputs,
            siblings,
            directions,
        }
    }
    pub fn authority_note(&self) -> Note {
        Note {
            owner: self.address.owner,
            incoming: self.address.incoming,
            value: 0,
            rho: [0; 32],
        }
    }
    pub fn nf(&self, n: &Note) -> H {
        nullifier(&self.secret, n)
    }
    pub fn discover(
        &self,
        records: &[Delivery],
        tree: &Tree,
        spent: &std::collections::BTreeSet<H>,
    ) -> Vec<(Note, usize)> {
        records
            .iter()
            .filter_map(|d| {
                let raw = self.view.unseal(&d.ciphertext).ok()?;
                let n = Note::parse(&raw).ok()?;
                if n.owner != self.address.owner
                    || n.incoming != self.address.incoming
                    || n.commitment() != d.commitment
                    || spent.contains(&self.nf(&n))
                {
                    return None;
                }
                let index = tree.leaves.iter().position(|x| *x == d.commitment)?;
                Some((n, index))
            })
            .collect()
    }
}
impl Note {
    pub fn for_address(address: &Address, value: u64) -> Self {
        let mut rho = [0; 32];
        OsRng.fill_bytes(&mut rho);
        Self {
            owner: address.owner,
            incoming: address.incoming,
            value,
            rho,
        }
    }
    pub fn deliver(&self) -> Result<Delivery> {
        if self.value == 0 {
            return Ok(Delivery::absent());
        }
        let ciphertext = PublicKey::from(self.incoming)
            .seal(&mut OsRng, &self.plaintext())
            .map_err(|_| "encryption")?;
        Ok(Delivery {
            commitment: self.commitment(),
            ciphertext,
        })
    }
}
pub struct Engine {
    pk: ProvingKey<Bn254>,
    pvk: PreparedVerifyingKey<Bn254>,
    id: H,
}
impl Engine {
    pub fn setup(sample: WalletCircuit) -> Result<Self> {
        let pk = Groth16::<Bn254>::generate_random_parameters_with_reduction(sample, &mut OsRng)
            .map_err(|e| e.to_string())?;
        let pvk = prepare_verifying_key(&pk.vk);
        let mut v = vec![];
        pk.vk
            .serialize_compressed(&mut v)
            .map_err(|e| e.to_string())?;
        Ok(Self {
            pk,
            pvk,
            id: hash(&v),
        })
    }
    pub fn prove(
        &self,
        mut statement: Statement,
        witness: Witness,
        deliveries: [Delivery; 2],
    ) -> Result<Operation> {
        statement.verifier = self.id;
        for (i, d) in deliveries.iter().enumerate() {
            statement.outputs[i] = d.commitment;
            statement.delivery[i] = if d.ciphertext.is_empty() {
                [0; 32]
            } else {
                hash(&d.ciphertext)
            }
        }
        let proof = Groth16::<Bn254>::create_random_proof_with_reduction(
            WalletCircuit {
                statement: statement.clone(),
                witness,
            },
            &self.pk,
            &mut OsRng,
        )
        .map_err(|e| e.to_string())?;
        let mut bytes = vec![];
        proof
            .serialize_compressed(&mut bytes)
            .map_err(|e| e.to_string())?;
        let op = Operation {
            statement,
            deliveries,
            proof: bytes,
        };
        self.verify(&op)?;
        Ok(op)
    }
    pub fn id(&self) -> H {
        self.id
    }
    pub fn verifier(&self) -> Verifier {
        Verifier {
            pvk: self.pvk.clone(),
            id: self.id,
        }
    }
    pub fn verify(&self, op: &Operation) -> Result<()> {
        self.verifier().verify(op)
    }
    pub fn proving_key_bytes(&self) -> usize {
        self.pk.compressed_size()
    }
    pub fn vk_bytes(&self) -> Vec<u8> {
        let mut v = vec![];
        self.pk.vk.serialize_compressed(&mut v).unwrap();
        v
    }
}

pub struct Verifier {
    pvk: PreparedVerifyingKey<Bn254>,
    id: H,
}
impl Verifier {
    pub fn from_bytes(bytes: &[u8], expected: H) -> Result<Self> {
        if hash(bytes) != expected {
            return Err("unexpected verifier identity".into());
        }
        let mut input = bytes;
        let vk = ark_groth16::VerifyingKey::<Bn254>::deserialize_compressed(&mut input)
            .map_err(|_| "malformed VK")?;
        let mut canonical = vec![];
        vk.serialize_compressed(&mut canonical)
            .map_err(|e| e.to_string())?;
        if !input.is_empty() || canonical != bytes || vk.gamma_abc_g1.len() != 15 {
            return Err("VK encoding/arity".into());
        }
        Ok(Self {
            pvk: prepare_verifying_key(&vk),
            id: expected,
        })
    }
    pub fn id(&self) -> H {
        self.id
    }
    pub fn verify(&self, op: &Operation) -> Result<()> {
        let s = &op.statement;
        if s.version != 1
            || s.domain != domain()
            || s.verifier != self.id
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
        if op.proof.len() != 128 {
            return Err("proof size".into());
        }
        let mut input = op.proof.as_slice();
        let proof =
            Proof::<Bn254>::deserialize_compressed(&mut input).map_err(|_| "malformed proof")?;
        let mut canonical = vec![];
        proof
            .serialize_compressed(&mut canonical)
            .map_err(|e| e.to_string())?;
        if proof.a.is_zero() || proof.b.is_zero() || proof.c.is_zero() {
            return Err("identity proof point".into());
        }
        if !input.is_empty()
            || canonical != op.proof
            || !Groth16::<Bn254>::verify_proof(&self.pvk, &proof, &s.inputs())
                .map_err(|_| "verification")?
        {
            return Err("invalid proof".into());
        }
        Ok(())
    }
}
