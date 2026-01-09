from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import base64

print("🔐 Generazione chiavi VAPID...")
private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
with open('vapid_private.pem', 'wb') as f:
    f.write(private_pem)

print("✅ File 'vapid_private.pem' creato")
public_key = private_key.public_key()
public_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)
public_b64 = base64.urlsafe_b64encode(public_bytes).decode('utf-8').rstrip('=')
print(f"\nconst VAPID_PUBLIC_KEY = '{public_b64}';\n")

