FROM python:3.11-slim

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /

COPY ataka/common/requirements.txt /ataka/common/
RUN pip install --no-cache-dir -r /ataka/common/requirements.txt
COPY ataka/common /ataka/common

VOLUME /data/shared
VOLUME /data/exploits
VOLUME /data/persist

COPY ataka/executor/requirements.txt /ataka/executor/
RUN pip install --no-cache-dir -r /ataka/executor/requirements.txt
COPY ataka/executor /ataka/executor

CMD [ "bash", "/ataka/common/delayed_start.sh", "--", "python", "-m", "ataka.executor" ]
