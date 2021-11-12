# flume-fuse
`Fuse` (Filesystem in Userspace) based filesystem to manage the `flume` database

## Features
* [x] Tree mode for File
* [x] Search mode
* [x] Read media content directly from the FS

## Setup

Mount the corresponding `flume` database by running
```
flume-fuse -s <MOUNT DIR>
```

### Tree Mode
You can navigate over `flume` files and read the fields and relationships
![Tree mode example](rsc/tree-mode.svg)

### Search Mode
You can navigate over `flume` files by generating queries in the filesystem through paths


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

## License
## References
* [Flume](https://github.com/turran/flume)
* [Poetry Template](https://github.com/yunojuno/poetry-template)
