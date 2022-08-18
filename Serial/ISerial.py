from typing import Protocol


class ISerial(Protocol):
    def readline(self) -> bytes:
        ...
