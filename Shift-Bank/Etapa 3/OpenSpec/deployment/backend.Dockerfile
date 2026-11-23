FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

RUN groupadd --system --gid 10001 shiftbank \
    && useradd --system --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin shiftbank

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY --chown=10001:10001 backend/*.py ./
RUN mkdir -p /var/lib/shift-bank && chown 10001:10001 /var/lib/shift-bank

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=4s --start-period=20s --retries=6 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=3).read()"

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=172.29.240.2"]
