//! Checked integer accounting and canonical fixed contexts (ADR-0003).
use serde::{Deserialize, Serialize};
pub const MAX_SOMPI: u64 = 2_900_000_000_000_000_000;
pub const LABEL: &[u8] = b"KPI-A1/TN10/finite/v1\0";
pub const GENESIS_HEX: &str = "f896a3034873be1739fc4359236899fd3d65d2bc94f9780df0d0da3eb1cc4370";
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Branch {
    S0Continue,
    S0Terminal,
    S1Terminal,
}
impl Branch {
    pub const ALL: [Self; 3] = [Self::S0Continue, Self::S0Terminal, Self::S1Terminal];
    pub fn name(self) -> &'static str {
        match self {
            Self::S0Continue => "s0_continue",
            Self::S0Terminal => "s0_terminal",
            Self::S1Terminal => "s1_terminal",
        }
    }
    pub fn stage_mode(self) -> (u8, u8) {
        match self {
            Self::S0Continue => (0, 0),
            Self::S0Terminal => (0, 1),
            Self::S1Terminal => (1, 1),
        }
    }
    pub fn selector(self) -> u8 {
        self.stage_mode().1
    }
}
#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Terms {
    pub l0: u64,
    pub b0: u64,
    pub w: u64,
    pub f0: u64,
    pub fc: u64,
    pub f1: u64,
}
#[derive(Clone, Copy, Debug, Serialize)]
pub struct Accounting {
    pub l0: u64,
    pub b0: u64,
    pub r0: u64,
    pub l1: u64,
    pub b1: u64,
    pub r1: u64,
    pub p0: u64,
    pub p1: u64,
    pub w: u64,
    pub f0: u64,
    pub fc: u64,
    pub f1: u64,
}
fn amount(x: u64) -> Result<u64, String> {
    if x > MAX_SOMPI {
        Err("native monetary range".into())
    } else {
        Ok(x)
    }
}
fn add(a: u64, b: u64) -> Result<u64, String> {
    amount(a.checked_add(b).ok_or("integer overflow")?)
}
impl Terms {
    pub fn checked(self) -> Result<Accounting, String> {
        for x in [self.l0, self.b0, self.w, self.f0, self.fc, self.f1] {
            amount(x)?;
        }
        if self.w == 0
            || self.w >= self.l0
            || self.f0 == 0
            || self.fc == 0
            || self.f1 == 0
            || self.f0 > self.b0
            || self.fc > self.b0
        {
            return Err("partial payout or S0 fee-credit range".into());
        }
        let l1 = self.l0.checked_sub(self.w).ok_or("principal underflow")?;
        let b1 = self.b0.checked_sub(self.fc).ok_or("credit underflow")?;
        if self.f1 > b1 {
            return Err("S1 fee-credit underflow".into());
        }
        let r0 = add(self.l0, self.b0)?;
        let r1 = add(l1, b1)?;
        let p0 = r0.checked_sub(self.f0).ok_or("exit underflow")?;
        let p1 = r1.checked_sub(self.f1).ok_or("exit underflow")?;
        if add(add(self.w, r1)?, self.fc)? != r0
            || add(p0, self.f0)? != r0
            || add(p1, self.f1)? != r1
        {
            return Err("conservation".into());
        }
        Ok(Accounting {
            l0: self.l0,
            b0: self.b0,
            r0,
            l1,
            b1,
            r1,
            p0,
            p1,
            w: self.w,
            f0: self.f0,
            fc: self.fc,
            f1: self.f1,
        })
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OutputTerm {
    pub value: u64,
    pub spk: Vec<u8>,
}
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BranchContext {
    pub stage: u8,
    pub mode: u8,
    pub genesis: [u8; 32],
    pub instance: [u8; 32],
    pub claim: [u8; 32],
    pub reserve: u64,
    pub principal: u64,
    pub credit: u64,
    pub fee: u64,
    pub next_reserve: u64,
    pub next_principal: u64,
    pub next_credit: u64,
    pub outputs: Vec<OutputTerm>,
}
pub fn full_spk(b: &[u8]) -> Result<(), String> {
    if b.len() < 3 || b[..2] != [0, 0] || b.len() > 10_002 {
        Err("SPK version/length".into())
    } else {
        Ok(())
    }
}
impl BranchContext {
    pub fn from_terms(
        branch: Branch,
        terms: Terms,
        instance: [u8; 32],
        claim: [u8; 32],
        recipient: &[u8],
        successor: &[u8],
    ) -> Result<Self, String> {
        let a = terms.checked()?;
        full_spk(recipient)?;
        if recipient.len() != 36 || recipient[2] != 32 || recipient[35] != 0xac {
            return Err("recipient P2PK".into());
        }
        let (stage, mode) = branch.stage_mode();
        let (r, l, b, fee, nr, nl, nb, outputs) = match branch {
            Branch::S0Continue => {
                full_spk(successor)?;
                if successor.len() != 37 || successor[2..4] != [0xaa, 0x20] || successor[36] != 0x87
                {
                    return Err("successor P2SH".into());
                }
                (
                    a.r0,
                    a.l0,
                    a.b0,
                    a.fc,
                    a.r1,
                    a.l1,
                    a.b1,
                    vec![
                        OutputTerm {
                            value: a.r1,
                            spk: successor.to_vec(),
                        },
                        OutputTerm {
                            value: a.w,
                            spk: recipient.to_vec(),
                        },
                    ],
                )
            }
            Branch::S0Terminal => (
                a.r0,
                a.l0,
                a.b0,
                a.f0,
                0,
                0,
                0,
                vec![OutputTerm {
                    value: a.p0,
                    spk: recipient.to_vec(),
                }],
            ),
            Branch::S1Terminal => (
                a.r1,
                a.l1,
                a.b1,
                a.f1,
                0,
                0,
                0,
                vec![OutputTerm {
                    value: a.p1,
                    spk: recipient.to_vec(),
                }],
            ),
        };
        Ok(Self {
            stage,
            mode,
            genesis: hex::decode(GENESIS_HEX).unwrap().try_into().unwrap(),
            instance,
            claim,
            reserve: r,
            principal: l,
            credit: b,
            fee,
            next_reserve: nr,
            next_principal: nl,
            next_credit: nb,
            outputs,
        })
    }
    pub fn validate(&self) -> Result<(), String> {
        if hex::encode(self.genesis) != GENESIS_HEX
            || ![(0, 0), (0, 1), (1, 1)].contains(&(self.stage, self.mode))
        {
            return Err("domain/stage/mode".into());
        }
        for x in [
            self.reserve,
            self.principal,
            self.credit,
            self.fee,
            self.next_reserve,
            self.next_principal,
            self.next_credit,
        ] {
            amount(x)?;
        }
        if self.principal == 0
            || self.fee == 0
            || self.fee > self.credit
            || add(self.principal, self.credit)? != self.reserve
        {
            return Err("reserve/fee relation".into());
        }
        let mut sum = self.fee;
        for o in &self.outputs {
            if o.value == 0 {
                return Err("zero output".into());
            }
            full_spk(&o.spk)?;
            sum = add(sum, o.value)?;
        }
        if sum != self.reserve {
            return Err("output conservation".into());
        }
        let recipient = if self.mode == 0 {
            if self.outputs.len() != 2
                || self.next_principal == 0
                || self.next_credit != self.credit - self.fee
                || add(self.next_principal, self.next_credit)? != self.next_reserve
                || self.outputs[0].value != self.next_reserve
                || add(self.next_principal, self.outputs[1].value)? != self.principal
            {
                return Err("continuation relation".into());
            }
            let s = &self.outputs[0].spk;
            if s.len() != 37 || s[2..4] != [0xaa, 0x20] || s[36] != 0x87 {
                return Err("successor P2SH".into());
            }
            &self.outputs[1].spk
        } else {
            if self.outputs.len() != 1
                || [self.next_reserve, self.next_principal, self.next_credit] != [0; 3]
            {
                return Err("terminal relation".into());
            }
            &self.outputs[0].spk
        };
        if recipient.len() != 36 || recipient[2] != 32 || recipient[35] != 0xac {
            return Err("recipient P2PK".into());
        }
        Ok(())
    }
    pub fn encode(&self) -> Result<Vec<u8>, String> {
        self.validate()?;
        let mut b = LABEL.to_vec();
        b.extend(self.genesis);
        b.extend(self.instance);
        b.extend([self.stage, self.mode]);
        b.extend(self.claim);
        for n in [
            self.reserve,
            self.principal,
            self.credit,
            self.fee,
            self.next_reserve,
            self.next_principal,
            self.next_credit,
        ] {
            b.extend(n.to_le_bytes());
        }
        b.push(self.outputs.len().try_into().map_err(|_| "count")?);
        for o in &self.outputs {
            b.extend(o.value.to_le_bytes());
            b.extend((o.spk.len() as u32).to_le_bytes());
            b.extend(&o.spk);
            b.push(0);
        }
        Ok(b)
    }
    pub fn decode(b: &[u8]) -> Result<Self, String> {
        struct Reader<'a> {
            b: &'a [u8],
            p: usize,
        }
        impl<'a> Reader<'a> {
            fn take(&mut self, n: usize) -> Result<&'a [u8], String> {
                let end = self.p.checked_add(n).ok_or("length overflow")?;
                let v = self.b.get(self.p..end).ok_or("truncated context")?;
                self.p = end;
                Ok(v)
            }
            fn u64(&mut self) -> Result<u64, String> {
                Ok(u64::from_le_bytes(self.take(8)?.try_into().unwrap()))
            }
        }
        let mut r = Reader { b, p: 0 };
        if r.take(LABEL.len())? != LABEL {
            return Err("context label".into());
        }
        let genesis = r.take(32)?.try_into().unwrap();
        let instance = r.take(32)?.try_into().unwrap();
        let stage = r.take(1)?[0];
        let mode = r.take(1)?[0];
        let claim = r.take(32)?.try_into().unwrap();
        let reserve = r.u64()?;
        let principal = r.u64()?;
        let credit = r.u64()?;
        let fee = r.u64()?;
        let next_reserve = r.u64()?;
        let next_principal = r.u64()?;
        let next_credit = r.u64()?;
        let count = r.take(1)?[0];
        if count > 2 {
            return Err("count".into());
        }
        let mut outputs = vec![];
        for _ in 0..count {
            let value = r.u64()?;
            let n = u32::from_le_bytes(r.take(4)?.try_into().unwrap()) as usize;
            if n > 10_002 {
                return Err("SPK length".into());
            }
            let spk = r.take(n)?.to_vec();
            if r.take(1)? != [0] {
                return Err("covenant metadata must be None".into());
            }
            outputs.push(OutputTerm { value, spk });
        }
        if r.p != b.len() {
            return Err("trailing context".into());
        }
        let c = Self {
            stage,
            mode,
            genesis,
            instance,
            claim,
            reserve,
            principal,
            credit,
            fee,
            next_reserve,
            next_principal,
            next_credit,
            outputs,
        };
        c.validate()?;
        Ok(c)
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};
    fn terms() -> Terms {
        Terms {
            l0: 1_000_000_000,
            b0: 60_000_000,
            w: 400_000_000,
            f0: 20_000_000,
            fc: 20_000_000,
            f1: 20_000_000,
        }
    }
    #[test]
    fn frozen_oracles() {
        let rec =
            hex::decode("00002079be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ac")
                .unwrap();
        let next = hex::decode(format!("0000aa20{}87", "aa".repeat(32))).unwrap();
        let instance = std::array::from_fn(|i| i as u8);
        let claim = hex::decode("72dbb7336c76780023f83da4c355f2eeea85733b13d3477697917790c1229084")
            .unwrap()
            .try_into()
            .unwrap();
        for (branch, hash) in Branch::ALL.into_iter().zip([
            "0af7df62cf63215e4c4388f114c3582a737996978c2b976451205664a0fe6ed5",
            "37dfc0262dfc6ba7c9cbade0539b8c1337cb1fe7f5412874ecb6e2752f2ff3e2",
            "4ed80e53e56a98bdbd2f6a4b039b6dbaedd054351258a47c4b9a2fb4d26c1583",
        ]) {
            let c =
                BranchContext::from_terms(branch, terms(), instance, claim, &rec, &next).unwrap();
            let b = c.encode().unwrap();
            assert_eq!(hex::encode(Sha256::digest(&b)), hash);
            assert_eq!(BranchContext::decode(&b).unwrap(), c);
            let mut extra = b.clone();
            extra.push(0);
            assert!(BranchContext::decode(&extra).is_err());
            assert!(BranchContext::decode(&b[..b.len() - 1]).is_err());
        }
    }
    #[test]
    fn arithmetic_boundaries() {
        let a = terms().checked().unwrap();
        assert_eq!(a.r0, a.w + a.r1 + a.fc);
        for t in [
            Terms { w: 0, ..terms() },
            Terms {
                w: 1_000_000_000,
                ..terms()
            },
            Terms {
                f1: 40_000_001,
                ..terms()
            },
            Terms {
                l0: MAX_SOMPI,
                ..terms()
            },
            Terms {
                b0: u64::MAX,
                ..terms()
            },
        ] {
            assert!(t.checked().is_err());
        }
        assert!(
            Terms {
                l0: MAX_SOMPI - 60_000_000,
                ..terms()
            }
            .checked()
            .is_ok()
        );
    }
}
