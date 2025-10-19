# Basis image
FROM python:3.13-slim

# Werkdirectory
WORKDIR /app

# Maak volume mountpoints
RUN mkdir -p /output /configs

# Installeer UV
RUN pip install uv

# Kopieer alleen de benodigde bestanden voor installatie
COPY pyproject.toml README.md ./
COPY src ./src

# Voeg src toe aan PYTHONPATH
ENV PYTHONPATH=/app/src

# Installeer dependencies en de applicatie met UV in system environment
RUN uv pip install --no-cache-dir --system .

# Installeer gunicorn in system environment
RUN uv pip install --no-cache-dir --system gunicorn

# Flask draait op poort 5000
EXPOSE 5000

# Start commando (updated to use 'app' package)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app.wsgi:app"]