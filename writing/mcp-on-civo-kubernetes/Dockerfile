FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY guard.py server.py http_app.py ./
RUN useradd --uid 10001 app
USER 10001
EXPOSE 8000
CMD ["python", "http_app.py"]
