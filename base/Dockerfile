FROM alpine:3.18.12
ARG CKAN_VERSION=main

# Internals, you probably don't need to change these
ENV TZ=UTC
ENV APP_DIR=/srv/app
ENV SRC_DIR=/srv/app/src
ENV CKAN_INI=${APP_DIR}/ckan.ini
ENV PIP_SRC=${SRC_DIR}
ENV CKAN_STORAGE_PATH=/var/lib/ckan
ENV GIT_URL=https://github.com/datopian/sse-ckan.git

# CKAN version to build
ENV GIT_BRANCH=${CKAN_VERSION}
# Customize these on the .env file if needed
ENV CKAN_SITE_URL=http://localhost:5000
ENV CKAN__PLUGINS="image_view text_view recline_view datastore envvars"

# UWSGI options
ENV UWSGI_HARAKIRI=50
WORKDIR ${APP_DIR}

# Set up timezone
RUN apk add --no-cache tzdata
RUN echo ${TZ} > /etc/timezone
# Make sure both files are not exactly the same
RUN if ! [ /usr/share/zoneinfo/${TZ} -ef /etc/localtime ]; then \
    cp /usr/share/zoneinfo/${TZ} /etc/localtime ;\
    fi ;

# Install necessary packages to run CKAN
RUN apk add --no-cache git \
    gettext \
    postgresql-client \
    python3 \
    libxml2 \
    libxslt \
    musl-dev \
    uwsgi \
    uwsgi-http \
    uwsgi-corerouter \
    uwsgi-python \
    libmagic \
    curl \
    patch \
    bash && \
    # Packages to build CKAN requirements and plugins
    apk add --no-cache --virtual .build-deps \
    postgresql-dev \
    gcc \
    make \
    g++ \
    autoconf \
    automake \
    libtool \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    linux-headers \
    openssl-dev \
    libffi-dev \
    cargo && \
    # Create SRC_DIR
    mkdir -p ${SRC_DIR} && \
    # Install pip, supervisord and uwsgi
    curl -o ${SRC_DIR}/get-pip.py https://bootstrap.pypa.io/get-pip.py && \
    python3 ${SRC_DIR}/get-pip.py && \
    pip3 install supervisor && \
    mkdir /etc/supervisord.d && \
    rm -rf ${SRC_DIR}/get-pip.py

COPY base/setup/supervisord.conf /etc

# Install CKAN
RUN pip3 install -e git+${GIT_URL}@${GIT_BRANCH}#egg=ckan && \
    cd ${SRC_DIR}/ckan && \
    pip3 install --no-binary markdown -r requirements.txt && \
    # Install gRPC RPC service dependencies
    pip3 install grpcio==1.68.0 grpcio-tools==1.68.0 protobuf==5.27.2 && \
    # Install CKAN envvars to support loading config from environment variables
    pip3 install -e git+https://github.com/okfn/ckanext-envvars.git@v0.0.6#egg=ckanext-envvars && \
    # Create and update CKAN config
    ckan generate config ${CKAN_INI} && \
    ckan config-tool ${CKAN_INI} "beaker.session.secret = " && \
    ckan config-tool ${CKAN_INI} "ckan.plugins = ${CKAN__PLUGINS}"

# Create a local user and group to run the app
RUN addgroup -g 92 -S ckan && \
    adduser -u 92 -h /srv/app -H -D -S -G ckan ckan

# Create local storage folder
RUN mkdir -p ${CKAN_STORAGE_PATH} && \
    chown -R ckan:ckan ${CKAN_STORAGE_PATH}

COPY base/setup/prerun.py ${APP_DIR}
COPY base/setup/start_ckan.sh ${APP_DIR}
COPY base/setup/start_rpc.sh ${APP_DIR}
ADD https://raw.githubusercontent.com/ckan/ckan/ckan-2.10.5/wsgi.py ${APP_DIR}
RUN chmod 644 ${APP_DIR}/wsgi.py

# Compile gRPC Protocol Buffer files
RUN mkdir -p ${SRC_DIR}/ckan/ckan/rpc/proto && \
    cd ${SRC_DIR}/ckan && \
    python3 -m grpc_tools.protoc \
    -I./ckan/rpc/proto \
    --python_out=./ckan/rpc/proto \
    --grpc_python_out=./ckan/rpc/proto \
    ./ckan/rpc/proto/ckan_rpc.proto 2>/dev/null || echo "Proto files will be compiled at runtime"

# Create entrypoint directory for children image scripts
ONBUILD RUN mkdir /docker-entrypoint.d

RUN chown ckan -R /srv/app

# Expose both web and gRPC ports
EXPOSE 5000 50051

HEALTHCHECK --interval=60s --timeout=5s --retries=5 CMD curl --fail http://localhost:5000/api/3/action/status_show || exit 1

CMD ["/srv/app/start_ckan.sh"]
