FROM python:3.10-slim

RUN groupadd -r ataka && useradd --no-log-init -m -r -g ataka ataka
USER ataka
ENV PATH="/home/ataka/.local/bin:${PATH}"

RUN pip install --no-cache-dir --user --upgrade pip

WORKDIR /home/ataka/

VOLUME /home/ataka/ataka/ctfconfig

COPY --chown=ataka:ataka ataka/common ataka/common
COPY --chown=ataka:ataka ataka/ctfcode/requirements.txt ataka/ctfcode/
RUN pip install --no-cache-dir --user -r ataka/ctfcode/requirements.txt

COPY --chown=ataka:ataka ataka/ctfcode ataka/ctfcode

CMD [ "python", "-m", "ataka.ctfcode" ]

