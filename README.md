# flume-fuse
`Fuse` (Filesystem in Userspace) based filesystem to manage the `flume` database

## Features
* [x] Tree mode for File
* [x] Search mode
* [ ] Read media content directly from the FS

## Setup
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
