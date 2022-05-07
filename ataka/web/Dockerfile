FROM python:3.10-slim

RUN groupadd -r ataka && useradd --no-log-init -m -r -g ataka ataka
USER ataka
ENV PATH="/home/ataka/.local/bin:${PATH}"

RUN pip install --no-cache-dir --user --upgrade pip

WORKDIR /home/ataka/

COPY --chown=ataka:ataka ataka/common ataka/common
COPY --chown=ataka:ataka ataka/web/requirements.txt ataka/web/
RUN pip install --no-cache-dir --user -r ataka/web/requirements.txt

COPY --chown=ataka:ataka ataka/web ataka/web

CMD [ "python", "-m", "ataka.web" ]

