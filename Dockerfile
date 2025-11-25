FROM python:3.11-slim

# install bash + dos2unix (needed for your entrypoint.sh)
RUN apt-get update && \
    apt-get install -y --no-install-recommends bash dos2unix && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collect static files into /app/staticfiles
RUN python manage.py collectstatic --noinput

# fix windows line endings + make script executable
RUN dos2unix docker/entrypoint.sh && chmod +x docker/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["bash", "docker/entrypoint.sh"]

CMD ["gunicorn", "ajerlo.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "2"]

