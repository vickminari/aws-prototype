FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Usuário sem privilégios: a API não precisa de root
RUN useradd --create-home --uid 1000 appuser

COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install .

COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

USER appuser
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
