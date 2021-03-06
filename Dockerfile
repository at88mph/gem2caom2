FROM opencadc/pandas:3.6-alpine

RUN apk --no-cache add \
        bash \
        coreutils \
        git \
        g++ \
        libmagic \
        wget

RUN pip install cadcdata && \
    pip install cadctap && \
    pip install caom2repo && \
    pip install ftputil && \
    pip install PyYAML && \
    pip install spherical-geometry && \
    pip install vos

WORKDIR /usr/src/app

RUN pip install bs4

RUN apk --no-cache add imagemagick

RUN mkdir /app && mkdir /app/data

ADD https://www.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/files/vault/cadcsw/2019-07-03_from_paul.txt /app/data/from_paul.txt

RUN git clone https://github.com/opencadc-metadata-curation/caom2tools.git && \
  cd caom2tools && git pull origin master && \
  pip install ./caom2utils && pip install ./caom2pipe && cd ..

RUN git clone https://github.com/opencadc-metadata-curation/gem2caom2.git && \
  pip install ./gem2caom2 && \
  cp ./gem2caom2/scripts/docker-entrypoint.sh / && \
  cp ./gem2caom2/scripts/config_with_ingest.yml / && \
  cp ./gem2caom2/scripts/config_with_visit.yml / && \
  cp ./gem2caom2/scripts/state.yml /

RUN apk --no-cache del git

ENTRYPOINT ["/docker-entrypoint.sh"]

