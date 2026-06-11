# Throwaway mail-egress probe Space — stdlib only, builds in seconds.
FROM python:3.12-slim

# HF Spaces convention: non-root user with uid 1000.
RUN useradd -m -u 1000 user
USER user
WORKDIR /app

COPY probe.py .

EXPOSE 7860
CMD ["python", "probe.py"]
