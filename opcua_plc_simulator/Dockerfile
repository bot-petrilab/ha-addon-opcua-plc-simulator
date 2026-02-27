ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache python3 py3-pip

COPY rootfs /

RUN chmod a+x /usr/bin/opcua_plc_simulator.py \
    /etc/services.d/opcua_plc_simulator/run \
    /etc/services.d/opcua_plc_simulator/finish \
    && pip3 install --no-cache-dir asyncua==1.1.6 pyyaml==6.0.2
