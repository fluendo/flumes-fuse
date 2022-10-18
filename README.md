<div align="center">
  <h1>Flumes-fuse
  <h4>Generate a filesystem from a database created by flumes</h4>
<div align="center">
  
  [![Maintenance](https://img.shields.io/maintenance/yes/2022.svg?style=for-the-badge)](https://img.shields.io/maintenance/yes/2022)
  [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
  [![Pull requests](https://img.shields.io/github/issues-pr-raw/fluendo/flumes-fuse.svg?style=for-the-badge)](https://img.shields.io/github/issues-pr-raw/fluendo/flumes-fuse)
  [![Contributors](https://img.shields.io/github/contributors/fluendo/flumes-fuse.svg?style=for-the-badge)](https://img.shields.io/github/contributors/fluendo/flumes-fuse)
  [![License](https://img.shields.io/github/license/fluendo/flumes-fuse.svg?style=for-the-badge)](https://github.com/fluendo/flumes-fuse/blob/master/LICENSE.LGPL)
  
</div>
</div><br>
  
# Table of Contents
- [About the project](#about_the_project)
    - [Features](#features)
- [Getting started](#getting_started)
  - [Supported platforms](#supported_platforms)
  - [System requirements](#system_requirements)
  - [Installation](#installation)  
- [Usage](#usage)
  - [Tree mode](#tree_mode)
  - [Search mode](#search_mode)
- [Development](#development)
  - [New releases](#new_releases)
  - [Tagging](#tagging)
  - [Testing](#testing)
- [License](#license)
- [References](#references)

# About the project <a name = "about_the_project"></a>
Flumes-fuse is a tool that utilises [Fuse](https://github.com/libfuse/libfuse) (Filesystem in Userspace) to generate and mount filesystems out of databases created by [flumes](https://github.com/fluendo/flumes/) tool. The purpose is to provide uncomplicated access to data via basic terminal commands.

## Features <a name = "features"></a>
* Tree mode: representation of each database file entry and its properties in tree-style hierarchy
* Search mode: database representation facilitating search by file entry property
* Direct content access: read media content directly from the filesystem

# Getting started <a name = "getting_started"></a>
## Supported platforms <a name = "supported_platforms"></a>
We depend upon [libfuse](https://github.com/libfuse/libfuse) supported platforms which are the following
* Linux
* BSD (partial)

## System requirements <a name = "system_requirements"></a>
* [Python >=3.9](https://www.python.org/downloads/)

## Installation <a name = "installation"></a>
For a successful and complete installation we recommend you to use [*poetry*](https://python-poetry.org/docs/) package manager.

* Install poetry
```
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
```

Make sure you are on the root path of the project repository before running the following commands.

* Install project dependencies
```
poetry install
```

# Usage <a name = "usage"></a>

Mount the corresponding *flumes* database by running
```
flumes-fuse -s <MOUNT DIR> -o uri=sqlite:///(<RELATIVE PATH TO DB> OR /<ABSOLUTE PATH TO DB>) -f
```
Note that directory <MOUNT DIR> should exist, otherwise the command will throw an error. `-f` calls the process in foreground mode.

## Tree Mode <a name = "tree_mode"></a>
You can navigate over `flumes` files and read the fields and relationships
![Tree mode example](rsc/tree-mode.svg)

## Search Mode <a name = "search_mode"></a>
You can navigate over `flumes` files by generating queries in the filesystem through paths
![Search mode example](rsc/search-mode.svg)

# Development <a name = "development"></a>
The project is based in `poetry` dependency management and packaging system.

* Install development pre-commit hooks
```
poetry run pre-commit install
```

* Update package dependencies in poetry.lock

The following command simply updates poetry.lock with the latest versions of the dependencies
```
poetry update --lock
```
If you also want poetry to install the latest versions in your local environment
```
poetry update
```

**New releases** <a name = "new_releases"></a>

To generate a new release you must update the version number. The following files will need to be updated: 
* init file
* tests/test_flumes_fuse.py
* pyproject.toml

Once it is merged, tagging must be done in order to distribute the new version correctly.

**Tagging** <a name = "tagging"></a>

```
git tag -a <version> -m "Release <version>"
```
```
git push origin --tags
```

## Testing <a name = "testing"></a>
All tests are located in the `tests` folder. The framework used is [*pytest*](https://docs.pytest.org/). 
* Run all tests with poetry 
```
poetry run pytest
```

# License <a name = "license"></a>
See `LICENSE.LGPL` for more information.

# References <a name = "references"></a>
* [Flumes](https://github.com/fluendo/flumes)
* [Poetry Template](https://github.com/yunojuno/poetry-template)
* [Asciinema](https://asciinema.org/)
* [Svg-term-cli](https://github.com/marionebl/svg-term-cli)
