class StorageBackend:
    def get_transactions(self):
        raise NotImplementedError

    def save_transactions(self, transactions):
        raise NotImplementedError
