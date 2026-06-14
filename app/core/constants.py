# app/core/constants.py

# FastAPI
APP_TITLE: str = 'Digital Wallet'
DESCRIPTION: str = (
    'API for managing digital wallets,'
    ' peer-to-peer transfers,'
    ' top-ups via Stripe etc.'
)

# Character limit for the database
STR_MINI: int = 10
STR_SHORT: int = 20
STR_MED: int = 128
STR_LONG: int = 256
STR_XL: int = 1024

# Settings for Decimal
FIAT_PRECISION: int = 18
FIAT_SCALE: int = 2
CRYPTO_PRECISION: int = 36
CRYPTO_SCALE: int = 18

# JWT expires
ACCESS_EXPIRE: int = 60 * 15
REFRESH_EXPIRE: int = 60 * 60 * 24 * 7

# Transactions
class EntryType:
    DEBIT = 'DEBIT'
    CREDIT = 'CREDIT'

class TransactionType:
    LOCAL = 'LOCAL'
    STRIPE = 'STRIPE'
