# Contributing

Thank you for considering contributing to traefik-route53-companion! All contributions are welcome.

## How to contribute

1. **Fork** the repository and create a branch from `main`.
2. **Make your changes** — keep them focused and minimal.
3. **Test your changes** locally using `DRY_RUN=true` before submitting.
4. **Open a pull request** with a clear description of what you changed and why.

## Reporting bugs

Open an [issue](https://github.com/Letark/traefik-route53-companion/issues) and include:
- Your `docker-compose` configuration (with secrets removed)
- Relevant log output (`LOG_LEVEL=DEBUG` helps)
- Expected vs. actual behavior

## Requesting features

Open an issue with the `enhancement` label. Describe your use case — not just the feature.

## Code style

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Keep functions small and focused
- Prefer clarity over cleverness

## Security

**Never include real AWS credentials, zone IDs, or domain names in issues, PRs, or code.**
Use placeholder values like `ZXXXXXXXXXXXXXXXXXXXX` and `example.com`.

If you discover a security vulnerability, please open a private security advisory rather than a public issue.
