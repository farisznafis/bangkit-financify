FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Serves the committed artifacts (artifacts/, data/processed/); training happens offline via train.py.
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 60 app:app
