FROM python:3.11-bookworm

WORKDIR /app

ENV PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu

RUN apt-get update && apt-get install -y \
    libheif-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
