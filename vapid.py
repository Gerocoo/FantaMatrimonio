# generate_vapid.py
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

def generate_vapid_keys():
    """Genera le chiavi VAPID per push notifications"""
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    
    # Chiave privata
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Chiave pubblica
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    print("=" * 80)
    print("CHIAVE PRIVATA (da mettere in config.py):")
    print("=" * 80)
    print(repr(private_pem))
    print("\n" + "=" * 80)
    print("CHIAVE PUBBLICA (da mettere in base.html):")
    print("=" * 80)
    print(repr(public_pem))

if __name__ == '__main__':
    generate_vapid_keys()
