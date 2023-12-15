from abc import ABC, abstractmethod


class SyncProvider(ABC):
    @abstractmethod
    def sync(self):
        pass
