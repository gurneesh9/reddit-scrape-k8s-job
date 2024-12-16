FROM python:3.12-slim AS base

WORKDIR /app
COPY RedditDownloader.py /app
COPY requirements.txt /app
RUN apt-get update && apt-get -y --no-install-recommends install tor
RUN pip3 install -r requirements.txt
CMD ["python3", "RedditDownloader.py", "pics"]

