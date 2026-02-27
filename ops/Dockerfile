FROM python:3.12-slim
WORKDIR /app
COPY ops /app/ops
ENV AGENTTEST_OPS_HOST=0.0.0.0
ENV AGENTTEST_OPS_PORT=8787
EXPOSE 8787
CMD ["python", "ops/server.py"]
