ARG TEAM_CLOUD_PYTHON_BASE_IMAGE=python:3.13-slim-bookworm
FROM ${TEAM_CLOUD_PYTHON_BASE_IMAGE}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY README.md pyproject.toml /app/
COPY team_cloud /app/team_cloud

RUN python -m pip install --no-cache-dir --upgrade pip==26.0 \
    && python -m pip install --no-cache-dir '.[web]'

EXPOSE 8780

CMD ["python", "-m", "uvicorn", "team_cloud.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8780"]
