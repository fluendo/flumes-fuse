# flumes-fuse
`Fuse` (Filesystem in Userspace) based filesystem to manage the `flumes` database

## Features
* [x] Tree mode for File
* [x] Search mode
* [x] Read media content directly from the FS

## Setup

Mount the corresponding `flumes` database by running
```
flumes-fuse -s <MOUNT DIR>
```

### Tree Mode
You can navigate over `flumes` files and read the fields and relationships
![Tree mode example](rsc/tree-mode.svg)

### Search Mode
You can navigate over `flumes` files by generating queries in the filesystem through paths
![Tree mode example](rsc/search-mode.svg)


## Development
The project is based in `poetry` dependency management and packaging system. The basic steps are

Install poetry
```
curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
```

Install the dependencies
```
poetry install
```

Install your development pre-commit hooks
```
poetry run pre-commit install
```

## References
* [Flume](https://github.com/turran/flumes)
* [Poetry Template](https://github.com/yunojuno/poetry-template)
* [Asciinema](https://asciinema.org/)
* [Svg-term-cli](https://github.com/marionebl/svg-term-cli)
