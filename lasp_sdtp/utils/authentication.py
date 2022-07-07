"""Functions for authentication

Authors
-------
    Matthew Bourque

Use
---
"""

import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from lasp_sdtp.config import admin_config


def build_certificate():
    """
    """

    one_day = datetime.timedelta(1, 0, 0)

    # Create private and public keys
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Initialize the certificate
    builder = x509.CertificateBuilder()

    # Set subject and issuer names
    builder = builder.subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, admin_config['certificate_authority'])]))
    builder = builder.issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'LASP')]))
    
    # Set validation range
    builder = builder.not_valid_before(datetime.datetime.utcnow().date() - one_day)
    builder = builder.not_valid_after(datetime.datetime.utcnow().date() + (one_day * 30))

    # Build the rest of the certificate
    builder = builder.serial_number(x509.random_serial_number())
    builder = builder.public_key(public_key)
    builder = builder.add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
    certificate = builder.sign(private_key=private_key, algorithm=hashes.SHA256())

    # Write the certificate to file
    with open("ca.key", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.BestAvailableEncryption(b"openstack-ansible")
        ))
    with open("ca.crt", "wb") as f:
        f.write(certificate.public_bytes(
            encoding=serialization.Encoding.PEM,
        ))

if __name__ == '__main__':

    build_certificate()
    