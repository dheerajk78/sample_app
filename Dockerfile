# Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Copy all other source files
COPY . .

# Expose the correct port for cloud providers
EXPOSE 8080

# Run the app with gunicorn (cloud-agnostic)
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
#CMD ["python", "app.py"]

