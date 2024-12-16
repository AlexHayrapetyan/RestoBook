from OpenSSL import crypto
import os

def generate_self_signed_cert(cert_dir, cert_file="cert.pem", key_file="key.pem"):
    # Create a self-signed certificate
    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)
    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)

    cert = crypto.X509()
    cert.set_version(2)
    cert.set_serial_number(1000)
    cert.get_subject().CN = "localhost"
    cert.set_issuer(cert.get_subject())
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(31536000)  # One year validity
    cert.set_pubkey(key)
    cert.sign(key, 'sha256')

    with open(os.path.join(cert_dir, key_file), 'wb') as key_file_obj:
        key_file_obj.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
    
    with open(os.path.join(cert_dir, cert_file), 'wb') as cert_file_obj:
        cert_file_obj.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))

generate_self_signed_cert('./ssl')
