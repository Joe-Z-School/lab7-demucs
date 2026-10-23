#!/bin/sh
set -eu

# Install or update RustFS using the official RustFS Helm chart repository.
helm repo add rustfs https://www.charts.rustfs.com
helm repo update
helm upgrade --install rustfs rustfs/rustfs \
    --values ./rustfs-config.yaml

# To access, port forward using:
# kubectl port-forward svc/rustfs-svc 9000:9000 9001:9001