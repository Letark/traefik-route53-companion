#!/usr/bin/env python3
"""
traefik-route53-companion
Watches Docker events and automatically creates/removes Route53 DNS records
for containers using Traefik as a reverse proxy.

Created by Kiro (AI assistant) — https://github.com/Letark/traefik-route53-companion
"""

import os
import re
import logging
import signal
import sys

import boto3
import docker
from botocore.exceptions import ClientError

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    level=getattr(logging, log_level, logging.INFO),
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (all via environment variables)
# ---------------------------------------------------------------------------
AWS_ACCESS_KEY_ID     = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION            = os.environ.get("AWS_REGION", "us-east-1")
HOSTED_ZONE_ID        = os.environ.get("HOSTED_ZONE_ID")
TARGET_DOMAIN         = os.environ.get("TARGET_DOMAIN")          # e.g. internal2.example.com or 1.2.3.4
TARGET_RECORD_TYPE    = os.environ.get("TARGET_RECORD_TYPE", "CNAME")  # CNAME or A
DOMAINS               = os.environ.get("DOMAINS", "")            # comma-separated list of zones to manage
RECORD_TTL            = int(os.environ.get("RECORD_TTL", "300"))
DRY_RUN               = os.environ.get("DRY_RUN", "false").lower() == "true"
DOCKER_HOST           = os.environ.get("DOCKER_HOST", "unix://var/run/docker.sock")

# Parse managed domains into a list
MANAGED_DOMAINS = [d.strip().rstrip(".") for d in DOMAINS.split(",") if d.strip()]

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_config():
    missing = []
    if not HOSTED_ZONE_ID:
        missing.append("HOSTED_ZONE_ID")
    if not TARGET_DOMAIN:
        missing.append("TARGET_DOMAIN")
    if not MANAGED_DOMAINS:
        missing.append("DOMAINS")
    if missing:
        log.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

# ---------------------------------------------------------------------------
# Route53 helpers
# ---------------------------------------------------------------------------
def get_route53_client():
    kwargs = {"region_name": AWS_REGION}
    if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = AWS_SECRET_ACCESS_KEY
    return boto3.client("route53", **kwargs)


def upsert_record(client, hostname):
    """Create or update a DNS record pointing hostname → TARGET_DOMAIN."""
    if DRY_RUN:
        log.info("[DRY RUN] Would upsert %s %s → %s", TARGET_RECORD_TYPE, hostname, TARGET_DOMAIN)
        return
    try:
        client.change_resource_record_sets(
            HostedZoneId=HOSTED_ZONE_ID,
            ChangeBatch={
                "Comment": f"traefik-route53-companion: upsert {hostname}",
                "Changes": [{
                    "Action": "UPSERT",
                    "ResourceRecordSet": {
                        "Name": hostname,
                        "Type": TARGET_RECORD_TYPE,
                        "TTL": RECORD_TTL,
                        "ResourceRecords": [{"Value": TARGET_DOMAIN}],
                    },
                }],
            },
        )
        log.info("Upserted %s %s → %s", TARGET_RECORD_TYPE, hostname, TARGET_DOMAIN)
    except ClientError as e:
        log.error("Failed to upsert %s: %s", hostname, e)


def delete_record(client, hostname):
    """Delete a DNS record for hostname if it exists and points to TARGET_DOMAIN."""
    if DRY_RUN:
        log.info("[DRY RUN] Would delete %s %s", TARGET_RECORD_TYPE, hostname)
        return
    try:
        client.change_resource_record_sets(
            HostedZoneId=HOSTED_ZONE_ID,
            ChangeBatch={
                "Comment": f"traefik-route53-companion: delete {hostname}",
                "Changes": [{
                    "Action": "DELETE",
                    "ResourceRecordSet": {
                        "Name": hostname,
                        "Type": TARGET_RECORD_TYPE,
                        "TTL": RECORD_TTL,
                        "ResourceRecords": [{"Value": TARGET_DOMAIN}],
                    },
                }],
            },
        )
        log.info("Deleted %s %s", TARGET_RECORD_TYPE, hostname)
    except ClientError as e:
        # InvalidChangeBatch means the record didn't exist — that's fine
        if "InvalidChangeBatch" in str(e):
            log.debug("Record %s not found in Route53, skipping delete", hostname)
        else:
            log.error("Failed to delete %s: %s", hostname, e)

# ---------------------------------------------------------------------------
# Label parsing
# ---------------------------------------------------------------------------
# Matches: Host(`foo.example.com`) or Host(`a.com`, `b.com`)
HOST_RULE_RE = re.compile(r"Host\(`([^`]+)`\)")


def extract_hosts_from_labels(labels: dict) -> list[str]:
    """Extract all Host() values from Traefik v2 router rule labels."""
    hosts = []
    for key, value in labels.items():
        if re.match(r"traefik\.http\.routers\..+\.rule", key):
            for match in HOST_RULE_RE.finditer(value):
                host = match.group(1).rstrip(".")
                if any(host.endswith(f".{d}") or host == d for d in MANAGED_DOMAINS):
                    hosts.append(host)
    return hosts

# ---------------------------------------------------------------------------
# Docker event loop
# ---------------------------------------------------------------------------
def process_container(client_r53, docker_client, container_id, action):
    try:
        container = docker_client.containers.get(container_id)
        labels = container.labels or {}
    except docker.errors.NotFound:
        log.debug("Container %s not found (already removed)", container_id)
        return

    hosts = extract_hosts_from_labels(labels)
    if not hosts:
        return

    for host in hosts:
        if action == "start":
            upsert_record(client_r53, host)
        elif action == "die":
            delete_record(client_r53, host)


def sync_running_containers(client_r53, docker_client):
    """On startup, upsert records for all currently running containers."""
    log.info("Syncing records for running containers...")
    for container in docker_client.containers.list():
        hosts = extract_hosts_from_labels(container.labels or {})
        for host in hosts:
            upsert_record(client_r53, host)


def watch(client_r53, docker_client):
    log.info("Watching Docker events (managed domains: %s)...", ", ".join(MANAGED_DOMAINS))
    for event in docker_client.events(decode=True, filters={"type": "container"}):
        action = event.get("Action")
        if action not in ("start", "die"):
            continue
        container_id = event.get("id")
        log.debug("Event: %s %s", action, container_id[:12])
        process_container(client_r53, docker_client, container_id, action)

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main():
    validate_config()

    if DRY_RUN:
        log.info("DRY RUN mode enabled — no Route53 changes will be made")

    log.info("traefik-route53-companion starting")
    log.info("Target: %s %s | Zone: %s | TTL: %s",
             TARGET_RECORD_TYPE, TARGET_DOMAIN, HOSTED_ZONE_ID, RECORD_TTL)

    client_r53 = get_route53_client()
    docker_client = docker.DockerClient(base_url=DOCKER_HOST)

    # Graceful shutdown
    def _shutdown(sig, frame):
        log.info("Shutting down")
        sys.exit(0)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    sync_running_containers(client_r53, docker_client)
    watch(client_r53, docker_client)


if __name__ == "__main__":
    main()
