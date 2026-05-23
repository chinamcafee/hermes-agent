# Hermes Team Cloud Offline Bundle

This directory defines the air-gapped bundle contract for Team Cloud. A generated bundle contains:

- `manifest.yaml`
- `images/*.tar`
- `charts/hermes-team-cloud-0.1.0.tgz`
- `SHA256SUMS`
- `install.sh`
- a deployment `values.yaml`

## Build

Run from the repository root:

```bash
scripts/team-cloud-offline-bundle.sh
```

The builder packages the Helm chart, writes `images.txt`, saves required Docker images, and produces `SHA256SUMS`.

## Install

Copy the generated bundle to the air-gapped host, review `values.yaml`, then run:

```bash
cd hermes-team-cloud-offline
sha256sum -c SHA256SUMS
./install.sh
```

The installer verifies `SHA256SUMS`, runs `docker load` for image archives, and executes `helm upgrade --install`.

