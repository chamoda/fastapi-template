from passlib.context import CryptContext

context = CryptContext(schemes=["bcrypt"])


def hash_password(password: str):
    return context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return context.verify(plain_password, hashed_password)
