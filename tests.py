# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'client'))
sys.path.insert(0, str(Path(__file__).parent / 'server'))

# Try importing the crypto client from the top-level module, falling back to the package path.
try:
    from crypto_client import RSAPublicKeyClient, CryptoClient
except ImportError:
    try:
        from client.crypto_client import RSAPublicKeyClient, CryptoClient
    except Exception:
        # Re-raise the original import error for visibility
        raise
