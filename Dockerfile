FROM python:3.11-slim

WORKDIR /app

# Only system libs needed by Pillow at runtime (small)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY creators.py .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080
# Tokens come from PandaStack env only — never bake secrets into the image

EXPOSE 8080
CMD ["python", "creators.py"]
