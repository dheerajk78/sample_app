# storage/gcs_backend.py

import csv
import io
from google.cloud import storage
from .base import StorageBackend

class GCSBackend(StorageBackend):
    def __init__(self, bucket_name):
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def load_csv(self, filename):
        blob = self.bucket.blob(filename)
        existing_rows = set()
        existing_header = None

        if blob.exists():
            content = blob.download_as_text()
            reader = csv.reader(io.StringIO(content))
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

        blob = self.bucket.blob(filename)
        blob.upload_from_string(output_buffer.getvalue(), content_type="text/csv")
