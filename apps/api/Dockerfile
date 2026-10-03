FROM python:3.12-slim
WORKDIR /srv/medisphere-api
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=10001:10001 app ./app
COPY --chown=10001:10001 migrations ./migrations
COPY --chown=10001:10001 alembic.ini ./
ENV PYTHONPATH=/srv/medisphere-api
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=30s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=2)"
USER 10001:10001
CMD ["sh", "-c", "if [ \"${RUN_MIGRATIONS:-true}\" != false ]; then alembic upgrade head; fi && if [ \"${SEED_DEMO_DATA:-false}\" = true ]; then python -m app.seed; fi && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
