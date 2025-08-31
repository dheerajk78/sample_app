class StorageBackend:
    def get_transactions(self):
        """
        Should return (header, rows)
        """
        raise NotImplementedError("Subclasses must implement get_transactions()")

    def save_transactions(self, header, rows):
        """
        Should accept header (list[str]) and rows (list[list[str]])
        """
        raise NotImplementedError("Subclasses must implement save_transactions()")
