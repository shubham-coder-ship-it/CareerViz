"""Print a password hash for ADMIN_PASSWORD_HASH without storing the password."""
import getpass
import hashlib
import secrets
password = getpass.getpass('Admin password: ')
if len(password) < 10:
    raise SystemExit('Use at least 10 characters.')
if password != getpass.getpass('Confirm password: '):
    raise SystemExit('Passwords do not match.')
salt = secrets.token_bytes(16)
iterations = 600000
digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, iterations).hex()
print('ADMIN_PASSWORD_HASH=pbkdf2_sha256$%d$%s$%s' % (iterations, salt.hex(), digest))
