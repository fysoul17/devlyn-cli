# Keyring rotation contract

A rejected key rotation is observationally absent: if rewrapping any stored secret raises an exception, the active key, every stored ciphertext, and the completed-rotation count all retain their pre-call values.

Only a fully successful rotation may publish the replacement ciphertexts and advance the active key.
