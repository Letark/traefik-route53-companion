FROM python:3.12-slim

LABEL org.opencontainers.image.title="traefik-route53-companion" \
      org.opencontainers.image.description="Automatically create and remove Route53 DNS records for containers served by Traefik" \
      org.opencontainers.image.source="https://github.com/Letark/traefik-route53-companion" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

CMD ["python", "-u", "app.py"]
