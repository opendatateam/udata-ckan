# CKAN

[![Crowdin](https://d322cqt584bo4o.cloudfront.net/udata-ckan/localized.svg)](https://crowdin.com/project/udata-ckan)

CKAN integration for uData

## Usage

Install the harvester package in you udata environement:

```bash
pip install udata-ckan
```

The harvester will be automatically available as a backend choice.

## Develop

### Python dependencies

Assuming you are in an active virtualenv with `udata` installed and in the current project cloned repository directory, install all dependencies using:

```shell
pip install -e requirements/develop.pip
```

### CKAN instance

A docker-compose is availbe to start up a CKAN instance if you want to test your harvester on a custom catalog.

### Testing

Tests are located into the `tests` folder and be run with:

```shell
inv test
```
