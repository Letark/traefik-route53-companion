# traefik-route53-companion

[![Build and Publish Docker Image](https://github.com/Letark/traefik-route53-companion/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/Letark/traefik-route53-companion/actions/workflows/docker-publish.yml)
[![GitHub release](https://img.shields.io/github/v/release/Letark/traefik-route53-companion)](https://github.com/Letark/traefik-route53-companion/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker Pulls](https://img.shields.io/badge/container-ghcr.io-blue)](https://github.com/Letark/traefik-route53-companion/pkgs/container/traefik-route53-companion)

Automatically create and remove **Amazon Route 53** DNS records for containers served by [Traefik](https://traefik.io), by watching Docker events and reading Traefik router labels.

Inspired by [tiredofit/docker-traefik-cloudflare-companion](https://github.com/tiredofit/docker-traefik-cloudflare-companion) — the same concept, built for AWS Route 53.

> **Created by [Kiro](https://kiro.dev)** — an AI software development assistant — in collaboration with the Letark homelab project.

---

## How it works

1. On startup, scans all running containers and upserts Route 53 records for any that have Traefik `Host()` labels matching your configured domains.
2. Watches the Docker event stream for `start` and `die` events.
3. On `start` — creates or updates a DNS record pointing the hostname to your `TARGET_DOMAIN`.
4. On `die` — removes the DNS record.

No polling. No restarts required. Records are managed in real time.

---

## Quick start

```yaml
services:
  traefik-route53-companion:
    image: ghcr.io/letark/traefik-route53-companion:latest
    container_name: traefik-route53-companion
    restart: unless-stopped
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
    environment:
      - HOSTED_ZONE_ID=ZXXXXXXXXXXXXXXXXXXXX
      - TARGET_DOMAIN=home.example.com
      - DOMAINS=example.com
      - AWS_ACCESS_KEY_ID=your_key_id
      - AWS_SECRET_ACCESS_KEY=your_secret_key
      - AWS_REGION=us-east-1
```

Any container with a Traefik label like this will automatically get a DNS record:

```yaml
labels:
  - "traefik.http.routers.myapp.rule=Host(`myapp.example.com`)"
```

This creates: `myapp.example.com CNAME → home.example.com`

---

## Configuration

All configuration is via environment variables.

| Variable | Required | Default | Description |
|---|---|---|---|
| `HOSTED_ZONE_ID` | ✅ | — | Route 53 hosted zone ID |
| `TARGET_DOMAIN` | ✅ | — | DNS value all records point to (hostname or IP) |
| `DOMAINS` | ✅ | — | Comma-separated list of domains to manage |
| `TARGET_RECORD_TYPE` | | `CNAME` | Record type: `CNAME` or `A` |
| `RECORD_TTL` | | `300` | TTL in seconds for created records |
| `DRY_RUN` | | `false` | Log actions without making Route 53 changes |
| `LOG_LEVEL` | | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `AWS_ACCESS_KEY_ID` | | — | AWS access key (omit to use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | | — | AWS secret key (omit to use IAM role) |
| `AWS_REGION` | | `us-east-1` | AWS region |
| `DOCKER_HOST` | | `unix://var/run/docker.sock` | Docker socket path |

### IAM authentication

If running on EC2 or ECS, you can omit `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` entirely. The companion will use the instance profile or task role automatically via the standard AWS credential chain.

### Required IAM permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:ChangeResourceRecordSets",
        "route53:ListResourceRecordSets"
      ],
      "Resource": "arn:aws:route53:::hostedzone/YOUR_ZONE_ID"
    }
  ]
}
```

---

## Multiple domains

Set `DOMAINS` to a comma-separated list. Only hostnames matching one of these domains will be managed:

```
DOMAINS=example.com,internal.example.com
```

---

## Dry run mode

Set `DRY_RUN=true` to log all actions without making any Route 53 changes. Useful for verifying your setup before going live.

---

## Docker socket security

The companion requires read access to the Docker socket to watch events and read container labels. Mount it read-only:

```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

If you prefer not to expose the socket directly, you can use a Docker socket proxy such as [Tecnativa/docker-socket-proxy](https://github.com/Tecnativa/docker-socket-proxy) and set `DOCKER_HOST` accordingly.

---

## Building locally

```bash
git clone https://github.com/Letark/traefik-route53-companion.git
cd traefik-route53-companion
docker build -t traefik-route53-companion .
```

---

## Releases

Docker images are published to the [GitHub Container Registry](https://github.com/Letark/traefik-route53-companion/pkgs/container/traefik-route53-companion) on every tagged release, built for `linux/amd64`, `linux/arm64`, and `linux/arm/v7`.

```
ghcr.io/letark/traefik-route53-companion:latest
ghcr.io/letark/traefik-route53-companion:v1.0.0
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — see [LICENSE](LICENSE).

---

## Acknowledgements

- [tiredofit/docker-traefik-cloudflare-companion](https://github.com/tiredofit/docker-traefik-cloudflare-companion) — the original inspiration for this project
- [Traefik](https://traefik.io) — the reverse proxy that makes this possible
- [Kiro](https://kiro.dev) — the AI assistant that designed and built this project
