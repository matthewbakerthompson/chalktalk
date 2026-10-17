# Security

chalktalk runs on your own computer. `chalk design` serves the designer on
127.0.0.1 only, and nothing in the package makes requests outside the
machine. The things most worth reporting are ways a play or playbook file, or
a request to the designer's local server, could read or write files it
shouldn't.

## Reporting a vulnerability

Report it privately through
[GitHub's private vulnerability reporting](https://github.com/matthewbakerthompson/chalktalk/security/advisories/new),
not in a public issue. Include the chalktalk version (`chalk --version`), the
command or file that triggers it, and what it lets someone do.

## Supported versions

Fixes go into the latest release on PyPI. Upgrade with
`python -m pip install --upgrade chalktalk`.
