"""Ed25519 manifest signing and verification CLI utility for release pipelines."""

from __future__ import annotations

import argparse
import json
import os
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from autosilenttrimmer.infrastructure.runtime.pack_manager import (
    canonical_manifest_bytes,
    verify_ed25519_hex,
)


def generate_keypair(out_dir: str) -> tuple[str, str]:
    """Generate Ed25519 signing private key hex + verify public key hex files."""
    os.makedirs(out_dir, exist_ok=True)
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    priv_path = os.path.join(out_dir, "manifest_ed25519.key.hex")
    pub_path = os.path.join(out_dir, "manifest_ed25519.pub.hex")
    with open(priv_path, "w", encoding="utf-8") as f:
        f.write(priv_bytes.hex())
    with open(pub_path, "w", encoding="utf-8") as f:
        f.write(pub_bytes.hex())
    return priv_path, pub_path


def sign_manifest(manifest_path: str, private_key_hex: str) -> str:
    """Attach canonical Ed25519 signature into release manifest JSON."""
    with open(manifest_path, encoding="utf-8") as f:
        data = json.load(f)

    priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex.strip()))
    payload = canonical_manifest_bytes(data)
    sig_hex = priv.sign(payload).hex()
    data["signature_ed25519"] = sig_hex

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return sig_hex


def main() -> int:
    parser = argparse.ArgumentParser(description="Ed25519 Release Manifest Signer")
    parser.add_argument("--keygen", type=str, help="Directory to output test Ed25519 keypair")
    parser.add_argument("--manifest", type=str, help="Path to release-manifest.json")
    parser.add_argument("--privkey-hex", type=str, help="Hex string or file path of private key")
    parser.add_argument("--verify-pubkey", type=str, help="Hex string or file path of public key")
    args = parser.parse_args()

    if args.keygen:
        priv_p, pub_p = generate_keypair(args.keygen)
        print(f"Generated private key: {priv_p}")
        print(f"Generated public key : {pub_p}")
        return 0

    if not args.manifest:
        parser.error("--manifest is required unless --keygen is passed")

    if args.privkey_hex:
        if os.path.isfile(args.privkey_hex):
            with open(args.privkey_hex, encoding="utf-8") as kf:
                key_val = kf.read().strip()
        else:
            key_val = args.privkey_hex
        sig = sign_manifest(args.manifest, key_val)
        print(f"Signed manifest ({args.manifest}): {sig[:24]}...")

    if args.verify_pubkey:
        if os.path.isfile(args.verify_pubkey):
            with open(args.verify_pubkey, encoding="utf-8") as pf:
                pub_val = pf.read().strip()
        else:
            pub_val = args.verify_pubkey
        with open(args.manifest, encoding="utf-8") as f:
            data = json.load(f)
        verify_ed25519_hex(
            canonical_manifest_bytes(data), data.get("signature_ed25519", ""), pub_val
        )
        print("Manifest signature VERIFIED.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
