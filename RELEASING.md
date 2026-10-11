# Releasing

chalktalk is published to PyPI by `.github/workflows/release.yml`, using PyPI
trusted publishing: GitHub proves to PyPI which repository and workflow is
uploading, so no API token is stored anywhere.

## Before the first release

A package on PyPI is public, source included. The license still applies
(PolyForm Noncommercial 1.0.0), but anyone can download and read the code.
The project links on the PyPI page point at this repository, so make the
repository public at the same time, or those links won't open for anyone else.

One-time setup:

1. Create accounts on [pypi.org](https://pypi.org/account/register/) and
   [test.pypi.org](https://test.pypi.org/account/register/) (they are separate),
   and turn on two-factor authentication for both.
2. On PyPI, open *Your account > Publishing* and add a pending publisher:

   | Field | Value |
   |---|---|
   | PyPI project name | `chalktalk` |
   | Owner | `matthewbakerthompson` |
   | Repository name | `chalktalk` |
   | Workflow name | `release.yml` |
   | Environment name | `pypi` |

   Do the same on TestPyPI, with environment name `testpypi`.
3. On GitHub, open the repository's *Settings > Environments* and create two
   environments, `pypi` and `testpypi`. Adding yourself as a required reviewer
   on `pypi` means every upload waits for your click.

## Each release

1. Set the version in `chalktalk/__init__.py` (`__version__`). That is the only
   place it is written; `pyproject.toml` reads it from there.
2. In `CHANGELOG.md`, rename `## Unreleased` to `## X.Y.Z`. A test fails if the
   version has no section.
3. Check the package locally:

   ```bash
   python -m pytest
   python -m build
   python -m twine check --strict dist/*
   ```

4. Merge to `main`.
5. Dry run on TestPyPI: *Actions > release > Run workflow*. Then try it in a
   clean environment:

   ```bash
   python -m venv /tmp/try
   /tmp/try/bin/python -m pip install --index-url https://test.pypi.org/simple/ \
       --extra-index-url https://pypi.org/simple/ chalktalk
   /tmp/try/bin/python -m chalktalk
   ```

   On Windows the interpreter is `\tmp\try\Scripts\python.exe`. TestPyPI
   refuses a version it has already seen, so a second dry run of the same
   version needs a new version number (for example `0.13.0rc2`).
6. Publish: on GitHub, *Releases > Draft a new release*, tag `vX.Y.Z` (it must
   match `__version__`, or the workflow stops), paste the CHANGELOG section as
   the notes, and publish. The workflow uploads to PyPI.
7. Check it: `python -m pip install --upgrade chalktalk` in a clean
   environment, then `chalk`.

## Without the workflow

From a clean checkout of the release commit, with a PyPI API token:

```bash
python -m build
python -m twine upload dist/*
```

twine asks for the token; the username is `__token__`.
