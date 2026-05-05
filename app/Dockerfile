FROM python:3.11-slim

# Crear usuario no-root para la aplicación
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libldap2-dev \
    libsasl2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY app.py .
COPY templates/ ./templates/

# Crear directorio para certificados CA
RUN mkdir -p /app/certs && chown -R appuser:appuser /app

# Cambiar a usuario no-root
USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
