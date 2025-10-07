# Basis image
FROM python:3.13-slim

# Werkdirectory
WORKDIR /app

# Dependencies installeren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Genesis installeren
COPY app ./app
COPY pyproject.toml .
RUN pip install .

# App kopiëren
COPY . .

# Zorg dat output directory bestaat
RUN mkdir -p /app/output /app/configs

# Flask draait op poort 5000
EXPOSE 5000

# Start commando
RUN pip install gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
