use kpi_private_note_wallet::{circuit::WalletCircuit, protocol::*, wallet::Wallet};
fn transfer() -> WalletCircuit {
    let a = Wallet::new();
    let b = Wallet::new();
    let input = a.note(1_000_000_000);
    let outputs = [b.note(400_000_000), a.note(600_000_000)];
    let mut tree = Tree::default();
    tree.append(input.commitment()).unwrap();
    let (siblings, directions) = tree.path(0).unwrap();
    let mut s = Statement::new(TRANSFER, [7; 32], tree.root());
    s.nullifier = a.nf(&input);
    for i in 0..2 {
        let d = outputs[i].deliver().unwrap();
        s.outputs[i] = d.commitment;
        s.delivery[i] = hash(&d.ciphertext)
    }
    WalletCircuit {
        statement: s,
        witness: a.witness(input, outputs, siblings, directions),
    }
}
#[test]
fn exact_packing_and_recipient_validation() {
    let c = transfer();
    assert_eq!(c.statement.bytes().len(), 410);
    assert_eq!(c.statement.inputs().len(), 14);
    let a = Wallet::new();
    let n = a.note(4);
    let d = n.deliver().unwrap();
    assert_eq!(d.ciphertext.len(), 185);
    let mut t = Tree::default();
    t.append(d.commitment).unwrap();
    assert_eq!(a.discover(&[d.clone()], &t, &Default::default()).len(), 1);
    let b = Wallet::new();
    assert!(b.discover(&[d.clone()], &t, &Default::default()).is_empty());
    let mut corrupt = d;
    corrupt.ciphertext[50] ^= 1;
    assert!(a.discover(&[corrupt], &t, &Default::default()).is_empty());
    let mut bad = n.clone();
    bad.incoming = b.address.incoming;
    let d = bad.deliver().unwrap();
    let mut t = Tree::default();
    t.append(d.commitment).unwrap();
    assert!(a.discover(&[d.clone()], &t, &Default::default()).is_empty());
    assert!(b.discover(&[d], &t, &Default::default()).is_empty());
}
#[test]
fn constrained_membership_authority_nullifier_and_domain() {
    let c = transfer();
    let (n, valid) = c.check().unwrap();
    assert!(valid);
    assert!(n > 100_000);
    for mode in 0..6 {
        let mut bad = c.clone();
        match mode {
            0 => bad.witness.secret[0] ^= 1,
            1 => bad.witness.siblings[0][0] ^= 1,
            2 => bad.witness.directions[0] = !bad.witness.directions[0],
            3 => bad.statement.nullifier[0] ^= 1,
            4 => bad.statement.domain[0] ^= 1,
            _ => bad.statement.kind = 255,
        };
        assert!(!bad.check().unwrap().1, "attack {mode}");
    }
}
#[test]
fn integer_conservation_and_output_commitment() {
    let c = transfer();
    for mode in 0..4 {
        let mut bad = c.clone();
        match mode {
            0 => bad.witness.outputs[0].value += 1,
            1 => bad.witness.outputs[0].owner[0] ^= 1,
            2 => bad.statement.outputs[1][0] ^= 1,
            _ => bad.statement.fee = 1,
        };
        assert!(!bad.check().unwrap().1, "attack {mode}");
    }
    // Refresh every other valid binding: this case fails actual integer equality,
    // not just an old note commitment/root after changing the input amount.
    let mut bad = c.clone();
    bad.witness.input.value = u64::MAX;
    bad.witness.outputs[0].value = u64::MAX;
    bad.witness.outputs[1].value = 1;
    let mut tree = Tree::default();
    tree.append(bad.witness.input.commitment()).unwrap();
    bad.statement.anchor = tree.root();
    let (p, d) = tree.path(0).unwrap();
    bad.witness.siblings = p;
    bad.witness.directions = d;
    bad.statement.nullifier = nullifier(&bad.witness.secret, &bad.witness.input);
    for i in 0..2 {
        bad.statement.outputs[i] = bad.witness.outputs[i].commitment()
    }
    assert!(
        !bad.check().unwrap().1,
        "u64 wrap cannot conserve value modulo Fr"
    );
}
#[test]
fn note_encoding_nullifier_and_duplicate_leaf() {
    let a = Wallet::new();
    let n = a.note(10);
    assert_eq!(
        Note::parse(&n.plaintext()).unwrap().commitment(),
        n.commitment()
    );
    let nf = a.nf(&n);
    let mut t = Tree::default();
    t.append(n.commitment()).unwrap();
    let before = t.root();
    t.append(a.note(1).commitment()).unwrap();
    assert_ne!(t.root(), before);
    assert_eq!(a.nf(&n), nf);
    assert!(t.append(n.commitment()).is_err());
    let mut b = n.plaintext();
    b.push(0);
    assert!(Note::parse(&b).is_err());
}

#[test]
fn credit_exit_recovery_shapes_are_constrained() {
    let a = Wallet::new();
    let n = a.note(10);
    let id = hash(b"deposit fixture");
    let mut tree = Tree::default();
    tree.append(n.commitment()).unwrap();
    let (p, b) = tree.path(0).unwrap();
    for kind in [CREDIT, EXIT, RECOVER] {
        let anchor = if kind == EXIT {
            tree.root()
        } else {
            Tree::default().root()
        };
        let mut s = Statement::new(kind, [7; 32], anchor);
        let input = if kind == EXIT {
            n.clone()
        } else {
            a.authority_note()
        };
        let outputs = if kind == CREDIT {
            [n.clone(), Note::dummy()]
        } else {
            [Note::dummy(), Note::dummy()]
        };
        if kind != EXIT {
            s.deposit = id;
            s.deposit_owner = a.address.owner;
            s.deposit_value = 10
        } else {
            s.nullifier = a.nf(&n)
        }
        if kind != CREDIT {
            s.exit_value = 10;
            s.exit_destination = hash(b"destination")
        }
        if kind == CREDIT {
            let d = n.deliver().unwrap();
            s.outputs[0] = d.commitment;
            s.delivery[0] = hash(&d.ciphertext)
        }
        let c = WalletCircuit {
            statement: s,
            witness: a.witness(input, outputs, p, b),
        };
        assert!(c.check().unwrap().1, "kind {kind}");
    }
}
#[test]
fn valid_u64_boundaries_and_packed_encoding() {
    let base = transfer();
    for value in [2, u64::MAX] {
        let mut c = base.clone();
        c.witness.input.value = value;
        c.witness.outputs[0].value = 1;
        c.witness.outputs[1].value = value - 1;
        let mut tree = Tree::default();
        tree.append(c.witness.input.commitment()).unwrap();
        c.statement.anchor = tree.root();
        let (p, d) = tree.path(0).unwrap();
        c.witness.siblings = p;
        c.witness.directions = d;
        c.statement.nullifier = nullifier(&c.witness.secret, &c.witness.input);
        for i in 0..2 {
            c.statement.outputs[i] = c.witness.outputs[i].commitment()
        }
        assert!(c.check().unwrap().1, "valid u64 boundary {value}");
        let bytes = c.statement.bytes();
        assert_eq!(Statement::parse(&bytes).unwrap().bytes(), bytes);
    }
}
