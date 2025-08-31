# storage/base.py

from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    def load_csv(self, filename: str):
        """Load CSV file and return header and a set of unique rows"""
        pass

    @abstractmethod
    def save_csv(self, filename: str, header, rows: set):
        """Save header and rows to CSV file"""
        pass
