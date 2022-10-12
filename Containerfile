FROM registry.access.redhat.com/ubi9/ubi:latest

WORKDIR /app

COPY . .

RUN dnf -y update && \
    dnf -y install python3-pip binutils && \
    curl -sL https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-client-linux.tar.gz | tar -C /usr/local/bin -xzf - oc && \
    pip3 install --upgrade pip && \
    pip3 install -r requirements.txt && \
    pip3 install pyinstaller
RUN pyinstaller openshift-checks.py


FROM registry.access.redhat.com/ubi9/ubi-micro:latest

WORKDIR /app

COPY --from=0 /usr/lib64/libcrypt.so.1 /usr/lib64/libcrypt.so.1
COPY --from=0 /usr/local/bin/oc /usr/local/bin/oc
COPY --from=0 /app/dist/openshift-checks .

ENV KUBECONFIG=/kubeconfig
ENV LD_LIBRARY_PATH=/app

ENTRYPOINT ["/app/openshift-checks"]
