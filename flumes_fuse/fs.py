import argparse
import errno
import importlib
import logging
import os
import sys
from datetime import datetime
from errno import EACCES, ENOENT
from stat import S_IFDIR, S_IFREG
from time import time
from urllib.parse import urlparse

import fuse
from flumes.config import Config
from flumes.options import Options
from flumes.schema import (
    Audio,
    Field,
    File,
    Info,
    Meta,
    Schema,
    Stream,
    Subtitle,
    Video,
)
from fuse import Fuse
from sqlalchemy import create_engine
from sqlalchemy.sql import select

from .options import FlumesFuseOptions
from .path import (
    PathParser,
    RootPath,
    SearchPath,
    SearchTablePath,
    Stat,
    TreeTablePath,
    VirtualFile,
)

logger = logging.getLogger(__name__)
fuse.fuse_python_api = (0, 2)


class FileContent(VirtualFile):
    def _real_file(self, obj):
        meta = self.session.query(Meta).one()
        # Media dir + path + name
        return os.path.join(meta.root, self.obj.path, self.obj.name)

    def read(self, size, offset):
        with open(self._real_file(self.obj), "rb") as f:
            f.seek(offset)
            content = f.read(size)
            return content

    def getattr(self):
        ret = Stat()
        ret.st_mode = S_IFREG | 0o444
        ret.st_size = os.path.getsize(self._real_file(self.obj))
        return ret


class FilePath(TreeTablePath):
    cls_name = File
    extra_fields = [("contents", FileContent)]


class SearchByStream(SearchTablePath):
    cls_name = Stream


class SearchBySubtitle(SearchTablePath):
    cls_name = Subtitle


class SearchByVideo(SearchTablePath):
    cls_name = Video


class SearchByAudio(SearchTablePath):
    cls_name = Audio


class SearchByField(SearchTablePath):
    cls_name = Field


class Search(SearchPath):
    queries = [
        ("stream", SearchByStream),
        ("video", SearchByVideo),
        ("audio", SearchByAudio),
        ("subtitle", SearchBySubtitle),
        ("field", SearchByField),
    ]
    results = FilePath

    def get_join_stmt(self):
        return select(File).join(File.info).join(Info.streams)


class Root(RootPath):
    cls_paths = [("files", FilePath), ("search", Search)]


class FlumesFuse(Fuse):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        # Make sure to have default arguments
        options = Options()
        for o in options._actions[1:]:
            setattr(self, o.dest, None)

    def fsinit(self):
        # Initialize our own config
        self.config = Config(self)
        self.schema = Schema(self.config)
        self.session = self.schema.create_session()
        self.path_parser = PathParser(self.schema, Root)
        self.now = time()

    def open(self, path, flags):
        try:
            self.path_parser.parse(path)
            return self.path_parser.open(flags)
        except FileNotFoundError:
            return -errno.ENOENT

    def read(self, path, size, offset):
        try:
            p = self.path_parser.parse(path)
            return self.path_parser.read(size, offset)
        except FileNotFoundError:
            return -errno.ENOENT

    def readdir(self, path, offset):
        try:
            p = self.path_parser.parse(path)
            return self.path_parser.readdir(offset)
        except FileNotFoundError:
            return -errno.ENOENT

    def getattr(self, path):
        try:
            p = self.path_parser.parse(path)
            return self.path_parser.getattr()
        except FileNotFoundError:
            return -errno.ENOENT


def run():
    # SQlite driver "can not work" in a multithread environment
    # Make the option always available
    fuse = FlumesFuse(parser_class=FlumesFuseOptions, dash_s_do="setsingle")
    args = fuse.parse(values=fuse)
    fuse.main()
