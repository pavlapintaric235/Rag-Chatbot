FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /usr/src/app

COPY requirements.txt .
RUN python -m pip install --upgrade pip && \
    pip install -r requirements.txt

COPY app ./app
COPY scripts ./scripts
COPY data ./data
COPY frontend ./frontend
COPY run.py ./run.py

EXPOSE 8010

CMD ["python", "run.py"]