FROM python:3.10-slim

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /

COPY ataka/common/requirements.txt /ataka/common/
RUN pip install --no-cache-dir -r /ataka/common/requirements.txt
COPY ataka/common /ataka/common

VOLUME /ataka/ctfconfig
VOLUME /data/shared

COPY ataka/ctfcode/requirements.txt /ataka/ctfcode/
RUN pip install --no-cache-dir -r /ataka/ctfcode/requirements.txt
COPY ataka/ctfcode /ataka/ctfcode

CMD [ "bash", "/ataka/common/delayed_start.sh", "--", "python", "-m", "ataka.ctfcode" ]

