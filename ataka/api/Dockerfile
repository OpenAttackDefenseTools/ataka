FROM python:3.10-slim

ARG CTF

RUN pip install --no-cache-dir --upgrade pip

WORKDIR /

COPY ataka/common/requirements.txt /ataka/common/
RUN pip install --no-cache-dir -r /ataka/common/requirements.txt
COPY ataka/common /ataka/common

VOLUME /data/shared
VOLUME /data/exploits

COPY ataka/api/requirements.txt /ataka/api/
RUN pip install --no-cache-dir -r /ataka/api/requirements.txt
COPY ataka/api /ataka/api

COPY ataka/player-cli/requirements.txt /ataka/player-cli/
RUN pip install --no-cache-dir -r /ataka/player-cli/requirements.txt
COPY ataka/player-cli /ataka/player-cli

COPY "ataka/ctfconfig/$CTF.py" /ataka/player-cli/player_cli/ctfconfig.py
RUN python -m zipapp /ataka/player-cli

CMD [ "bash", "/ataka/common/delayed_start.sh", "--", "python", "-m", "uvicorn", "--reload", "--host", "0.0.0.0", "ataka.api:app"]
