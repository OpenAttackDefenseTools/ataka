FROM python:3.10-slim

RUN groupadd -r ataka && useradd --no-log-init -m -r -g ataka ataka
USER ataka
ENV PATH="/home/ataka/.local/bin:${PATH}"

RUN pip install --no-cache-dir --user --upgrade pip

WORKDIR /home/ataka/

VOLUME /home/ataka/ataka/ctfconfig

COPY --chown=ataka:ataka ataka/common/requirements.txt ataka/common/
RUN pip install --no-cache-dir --user -r ataka/common/requirements.txt
COPY --chown=ataka:ataka ataka/common ataka/common

COPY --chown=ataka:ataka ataka/cli/requirements.txt ataka/cli/
RUN pip install --no-cache-dir --user -r ataka/cli/requirements.txt
COPY --chown=ataka:ataka ataka/cli ataka/cli

CMD [ "sleep", "infinity" ]

