from src.security import decrypt, decrypt_key_material, encrypt, generate_key_material, hmac_hash


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        plaintext = "MRN12345"
        encrypted = encrypt(plaintext)
        assert encrypted != plaintext.encode()
        assert decrypt(encrypted) == plaintext

    def test_encrypt_produces_different_ciphertext(self):
        """Fernet uses random IV, so same plaintext produces different ciphertext."""
        a = encrypt("same")
        b = encrypt("same")
        assert a != b


class TestHMAC:
    def test_hmac_deterministic(self):
        assert hmac_hash("MRN001") == hmac_hash("MRN001")

    def test_hmac_different_inputs(self):
        assert hmac_hash("MRN001") != hmac_hash("MRN002")

    def test_hmac_returns_hex(self):
        h = hmac_hash("test")
        assert len(h) == 64
        int(h, 16)  # Should not raise


class TestKeyMaterial:
    def test_generate_and_decrypt_key(self):
        encrypted_key = generate_key_material()
        raw_key = decrypt_key_material(encrypted_key)
        # Fernet keys are 44-char base64 strings
        assert len(raw_key) == 44
