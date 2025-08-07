# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (for google-auth, etc.)
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (so pip cache can be reused)
COPY requirements.txt .

# Install Python dependencies AND show what was actually installed
RUN pip install --no-cache-dir -r requirements.txt && pip freeze

# Copy all app files
COPY . .

# Set environment variables for Flask
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Start Flask app
CMD ["python", "main.py"]
