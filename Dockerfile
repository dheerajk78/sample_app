# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy app files
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

# Expose port
EXPOSE 8080

# Start the app
CMD ["gunicorn", "--bind", "0.0.0.0:80", "app:app"]
