FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
ENV PORT=8000 MEM0_TELEMETRY=false
EXPOSE 8000
CMD ["sh", "-c", "python -m gunicorn observatory.wsgi:application --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 180"]
