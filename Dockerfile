FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 BOT_ENABLED=false DATA_DIR=/data
WORKDIR /app
COPY jat_design/ /app/jat_design/
COPY SYSTEM_PROMPT.txt /app/SYSTEM_PROMPT.txt
CMD ["python", "-m", "jat_design.cloud_worker"]
