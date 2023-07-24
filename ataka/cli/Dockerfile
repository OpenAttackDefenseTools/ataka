FROM python:3.11-slim

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /

COPY ataka/common/requirements.txt /ataka/common/
RUN pip install --no-cache-dir -r /ataka/common/requirements.txt
COPY ataka/common /ataka/common

COPY ataka/cli/requirements.txt /ataka/cli/
RUN pip install --no-cache-dir -r /ataka/cli/requirements.txt
COPY ataka/cli /ataka/cli

CMD [ "sleep", "infinity" ]

