#!/usr/bin/env python3
"""Generate a VAPID key pair for Web Push — prints the two .env lines.

Usage:
    python scripts/gen-vapid-keys.py            # repo venv or any env with `cryptography`
    # then paste the output into .env (VAPID_SUBJECT can stay a mailto:)

The notifications service reads them from the environment; without them
subscribe/unsubscribe answer 503 and no reminder can ever be sent.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def main() -> None:
    key = ec.generate_private_key(ec.SECP256R1())
    private = key.private_numbers().private_value.to_bytes(32, "big")
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    print("# Web Push (VAPID) — keep the private key secret")
    print(f"VAPID_PUBLIC_KEY={b64url(public)}")
    print(f"VAPID_PRIVATE_KEY={b64url(private)}")
    print("VAPID_SUBJECT=mailto:you@yourdomain.com")


if __name__ == "__main__":
    main()
