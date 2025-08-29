# dataverse-client

[![License](https://img.shields.io/badge/license-MIT-brightgreen)](LICENSE)
![Code Style](https://img.shields.io/badge/code%20style-black-black)
[![semantic-release: angular](https://img.shields.io/badge/semantic--release-angular-e10079?logo=semantic-release)](https://github.com/semantic-release/semantic-release)
![Interrogate](https://img.shields.io/badge/interrogate-100.0%25-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)
![Python](https://img.shields.io/badge/python->=3.10-blue?logo=python)

## Usage

- `set DATAVERSE_password=<password>` to set an environment variable with the account password used to access dataverse

```python
config = DataverseConfig() # instantiating config reads from env vars
client = DataverseRestClient(config)

entry = client.get_entry(table, entry_id)
```

## REST API and Queries

URLs are formatted like `https://<ORG_ID>.crm.dynamics.com/api/data/v9.2/<TABLE><QUERY>`

To fetch an entity by its primary key: `https://<ORG_ID>.crm.dynamics.com/api/data/v9.2/<TABLE>({entry_primary_id})`
To fetch an entity by an alternate key: `https://<ORG_ID>.crm.dynamics.com/api/data/v9.2/<TABLE>({alt_key_name}={entry_primary_id})`
    - Note: string values must include single quotes: e.g. `(mouse_id='123456')`

To filter and query: 
- [odata query docs](https://docs.oasis-open.org/odata/odata/v4.0/errata03/os/complete/part1-protocol/odata-v4.0-errata03-os-part1-protocol-complete.html#_The_$filter_System)
- `https://<ORG_ID>.crm.dynamics.com/api/data/v9.2/<TABLE>?$filter=contains(crb81_mouse_id, 614)`
- `https://<ORG_ID>.crm.dynamics.com/api/data/v9.2/<TABLE>?$filter=crb81_sex eq 0`

## Repo setup
 - To use this template, click the green `Use this template` button and `Create new repository`.
 - After github initially creates the new repository, please wait an extra minute for the initialization scripts to finish organizing the repo.
 - To enable the automatic semantic version increments: in the repository go to `Settings` and `Collaborators and teams`. Click the green `Add people` button. Add `svc-aindscicomp` as an admin. Modify the file in `.github/workflows/tag_and_publish.yml` and remove the if statement in line 65. The semantic version will now be incremented every time a code is committed into the main branch.
 - To publish to PyPI, enable semantic versioning and uncomment the publish block in `.github/workflows/tag_and_publish.yml`. The code will now be published to PyPI every time the code is committed into the main branch.
 - The `.github/workflows/test_and_lint.yml` file will run automated tests and style checks every time a Pull Request is opened. If the checks are undesired, the `test_and_lint.yml` can be deleted. The strictness of the code coverage level, etc., can be modified by altering the configurations in the `pyproject.toml` file and the `.flake8` file.
 - Please make any necessary updates to the README.md and CITATION.cff files

## Level of Support
Please indicate a level of support:
 - [ ] Supported: We are releasing this code to the public as a tool we expect others to use. Issues are welcomed, and we expect to address them promptly; pull requests will be vetted by our staff before inclusion.
 - [ ] Occasional updates: We are planning on occasional updating this tool with no fixed schedule. Community involvement is encouraged through both issues and pull requests.
 - [ ] Unsupported: We are not currently supporting this code, but simply releasing it to the community AS IS but are not able to provide any guarantees of support. The community is welcome to submit issues, but you should not expect an active response.

## Release Status
GitHub's tags and Release features can be used to indicate a Release status.

 - Stable: v1.0.0 and above. Ready for production.
 - Beta:  v0.x.x or indicated in the tag. Ready for beta testers and early adopters.
 - Alpha: v0.x.x or indicated in the tag. Still in early development.

## Installation
To use the software, in the root directory, run
```bash
pip install -e .
```

To develop the code, run
```bash
pip install -e .[dev]
```
