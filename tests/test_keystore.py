import keyring
import keyring.backend
import keyring.backends.fail
import keyring.backends.null
import keyring.errors
import pytest

from openrouter_image_mcp import keystore
from openrouter_image_mcp.config import KEYRING_SERVICE, KEYRING_USER


class PlaintextKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def get_password(self, service, username):
        return None

    def set_password(self, service, username, password):
        pass

    def delete_password(self, service, username):
        pass


def test_roundtrip(memory_keyring):
    assert keystore.get_key() is None
    keystore.set_key("sk-or-v1-secret")
    assert keystore.get_key() == "sk-or-v1-secret"
    assert memory_keyring.store == {(KEYRING_SERVICE, KEYRING_USER): "sk-or-v1-secret"}
    keystore.delete_key()
    assert keystore.get_key() is None


def test_delete_absent_ok(memory_keyring):
    keystore.delete_key()


@pytest.mark.parametrize(
    "backend",
    [
        keyring.backends.fail.Keyring(),
        keyring.backends.null.Keyring(),
        PlaintextKeyring(),
    ],
    ids=["fail", "null", "plaintext"],
)
def test_refuses_insecure_backend(memory_keyring, backend):
    keyring.set_keyring(backend)  # memory_keyring fixture restores afterwards
    with pytest.raises(keystore.InsecureKeyringError, match="no plaintext fallback"):
        keystore.set_key("sk-or-v1-secret")
    with pytest.raises(keystore.InsecureKeyringError, match="no plaintext fallback"):
        keystore.get_key()


def test_refuses_insecure_backend_inside_chainer(memory_keyring):
    from keyring.backends import chainer

    class FakeChain(chainer.ChainerBackend):
        @property
        def backends(self):
            return [memory_keyring, PlaintextKeyring()]

    keyring.set_keyring(FakeChain())
    with pytest.raises(keystore.InsecureKeyringError):
        keystore.get_key()


def test_accepts_chainer_of_secure_backends(memory_keyring):
    from keyring.backends import chainer

    other = type(memory_keyring)()

    class FakeChain(chainer.ChainerBackend):
        @property
        def backends(self):
            return [memory_keyring, other]

    keyring.set_keyring(FakeChain())
    keystore.set_key("sk-or-v1-secret")
    assert keystore.get_key() == "sk-or-v1-secret"
    keystore.delete_key()
    assert keystore.get_key() is None


def test_set_key_deletes_the_old_entry_first(memory_keyring):
    class StackingKeyring(type(memory_keyring)):
        """Like Windows' fallback entries: set adds an entry, get returns the oldest."""

        def __init__(self):
            super().__init__()
            self.entries: list[str] = []

        def get_password(self, service, username):
            return self.entries[0] if self.entries else None

        def set_password(self, service, username, password):
            self.entries.append(password)

        def delete_password(self, service, username):
            if not self.entries:
                raise keyring.errors.PasswordDeleteError("not found")
            self.entries.pop(0)

    backend = StackingKeyring()
    keyring.set_keyring(backend)  # memory_keyring fixture restores afterwards
    keystore.set_key("sk-or-v1-old")
    keystore.set_key("sk-or-v1-new")
    assert backend.entries == ["sk-or-v1-new"]
    assert keystore.get_key() == "sk-or-v1-new"
