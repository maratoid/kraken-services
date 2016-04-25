FROM python:2.7-slim

RUN apt-get update && apt-get install -y build-essential --no-install-recommends \
    && pip install locustio \
    && apt-get purge -y --auto-remove build-essential
RUN ulimit -c -m -s -t unlimited
COPY scripts /scripts

ENTRYPOINT ["locust"]
