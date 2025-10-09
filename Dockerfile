# Basis image
FROM python:3.13-slim

# Werkdirectory
WORKDIR /app

# Dependencies installeren
COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt

# Maak volume mountpoints
RUN mkdir -p /output /configs

# Genesis installeren
COPY config /config
COPY logtools ./logtools
COPY genesis.py ./genesis.py
COPY pyproject.toml .
RUN pip install .

# App kopiëren
COPY . .

# Flask draait op poort 5000
EXPOSE 5000

# Start commando
RUN pip install gunicorn
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
