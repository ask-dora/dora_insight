FROM python:3.11-slim

WORKDIR /app

# Install system dependencies that might be needed for psycopg2 or other libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt 
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY ./code /app/code

# Expose the port the app runs on
EXPOSE 8000

ENV PYTHONPATH=/app
ENV GEMINI_API_KEY=${GEMINI_API_KEY}

# Ensure main.py is in the 'code' subdirectory as per your structure
CMD ["uvicorn", "code.main:app", "--host", "0.0.0.0", "--port", "8000"]
