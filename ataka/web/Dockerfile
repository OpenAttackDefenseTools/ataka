FROM python:3.10-slim

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /

COPY ataka/common/requirements.txt /ataka/common/
RUN pip install --no-cache-dir -r /ataka/common/requirements.txt
COPY ataka/common /ataka/common

VOLUME /data/shared
VOLUME /data/exploits

COPY ataka/web/requirements.txt /ataka/web/
RUN pip install --no-cache-dir -r /ataka/web/requirements.txt
COPY ataka/web /ataka/web

CMD [ "bash", "/ataka/common/delayed_start.sh", "--", "python", "-m", "ataka.web" ]
