from abc import ABC, abstractmethod
from collections.abc import AsyncIterator


class DataProvider(ABC):

    @abstractmethod
    def stream_messages(self) -> AsyncIterator[dict]:
        """Yield raw AIS messages from the provider."""
        raise NotImplementedError