"""Generate self-signed TLS certificate for local development/ staging.

Usage:
    python scripts/setup_ssl.py

Generates cert.pem + key.pem in the project root.
Set env vars before starting the server:
    SSL_CERTFILE=cert.pem
    SSL_KEYFILE=key.pem

For production, use a CA-issued certificate or deploy behind
a TLS-terminating reverse proxy (Caddy, Nginx, Cloudflare).
"""
from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        print("Installing cryptography...")
        os.system(f"{sys.executable} -m pip install cryptography")
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "KA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Bangalore"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SEO Autopilot Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False)
        .sign(key, hashes.SHA256())
    )

    (ROOT / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (ROOT / "key.pem").write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    print("Generated cert.pem + key.pem")
    print()
    print("Start the server with HTTPS:")
    print("    SSL_CERTFILE=cert.pem SSL_KEYFILE=key.pem python -m api.main")
    print()
    print("Or set these in your .env file:")
    print("    SSL_CERTFILE=cert.pem")
    print("    SSL_KEYFILE=key.pem")


if __name__ == "__main__":
    main()
