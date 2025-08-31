# storage/firestore_backend.py

import base64
import csv
import io
from google.cloud import firestore
from .base import StorageBackend

class FirestoreBackend(StorageBackend):
    def __init__(self):
        self.db = firestore.Client()

    def load_csv(self, filename):
        doc_ref = self.db.collection("csv_files").document(filename)
        doc = doc_ref.get()

        existing_rows = set()
        existing_header = None

        if doc.exists:
            data = doc.to_dict()
            encoded_csv = data.get("content")
            decoded = base64.b64decode(encoded_csv).decode("utf-8")
            reader = csv.reader(io.StringIO(decoded))
            existing_header = next(reader, None)
            for row in reader:
                if row and any(cell.strip() for cell in row):
                    existing_rows.add(tuple(row))

        return existing_header, existing_rows

    def save_csv(self, filename, header, rows):
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)
        if header:
            writer.writerow(header)
        for row in sorted(rows):
            writer.writerow(row)

        encoded = base64.b64encode(output_buffer.getvalue().encode("utf-8")).decode("utf-8")
        self.db.collection("csv_files").document(filename).set({
            "content": encoded
        })
