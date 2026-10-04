"""API key storage in the OS keyring. Never falls back to plaintext storage."""

import keyring
import keyring.errors
from keyring.backends import chainer

from .config import KEYRING_SERVICE, KEYRING_USER

_INSECURE_MODULES = {"keyring.backends.fail", "keyring.backends.null"}


class InsecureKeyringError(RuntimeError):
    """Raised when the active keyring backend cannot store secrets securely."""


def _is_insecure(backend) -> bool:
    cls = type(backend)
    return cls.__module__ in _INSECURE_MODULES or "Plaintext" in cls.__name__


def _check_backend() -> None:
    backend = keyring.get_keyring()
    if isinstance(backend, chainer.ChainerBackend):
        backends = list(backend.backends)
        insecure = not backends or any(_is_insecure(b) for b in backends)
    else:
        insecure = _is_insecure(backend)
    if insecure:
        raise InsecureKeyringError(
            "No secure OS keyring is available, and there is no plaintext fallback. "
            "Set up a system keyring (Windows Credential Manager, macOS Keychain, "
            "or Secret Service) and try again."
        )


def get_key() -> str | None:
    _check_backend()
    return keyring.get_password(KEYRING_SERVICE, KEYRING_USER)


def set_key(key: str) -> None:
    _check_backend()
    # Remove the old entry first: some backends (e.g. a Windows fallback entry) would
    # otherwise keep returning a switched-away key.
    delete_key()
    keyring.set_password(KEYRING_SERVICE, KEYRING_USER, key)


def delete_key() -> None:
    _check_backend()
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
    except keyring.errors.PasswordDeleteError:
        pass
