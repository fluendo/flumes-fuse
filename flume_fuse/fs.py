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

# from fuse import FUSE, FuseOSError, Operations, LoggingMixIn
import fuse
from flume.config import Config
from flume.options import Options
from flume.schema import File, Info, Schema
from fuse import Fuse
from sqlalchemy import create_engine
from sqlalchemy.sql import select

from .path import PathParser, TreeTablePath

logger = logging.getLogger(__name__)
fuse.fuse_python_api = (0, 2)


class FilePath(TreeTablePath):
    cls_name = File


class FlumeFuse(Fuse):
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
        self.path_parser = PathParser(self.schema)
        # Regiter all the tables
        self.path_parser.register("files", FilePath)
        self.now = time()

    def _get_file(self, path):
        session = self.schema.create_session()
        return session.query(File).filter_by(id=path.file).first()

    def _get_values(self, path):
        # get the table we refer to from the field
        table_name = path.conditions[len(path.conditions) - 1]["struct"]
        field_name = path.conditions[len(path.conditions) - 1]["field"]
        table = get_tables(alias=True)[table_name]
        field = table.columns[field_name]
        s = select([field])
        # now the conditions
        s = path.get_condition_stmt(s, table_name, field_name, alias=True)
        stmt = path.get_conditions_stmt()
        s = s.where(get_tables(alias=True)["info"].columns["id"].in_(stmt))
        with self.engine.connect() as conn:
            result = conn.execute(s.distinct()).fetchall()
            conn.close()
        return result

    def open(self, path, flags):
        try:
            p = self.path_parser.parse(path)
            return p.open(flags)
        except FileNotFoundError:
            return -errno.ENOENT

    def read(self, path, size, offset):
        try:
            p = self.path_parser.parse(path)
            return p.read(size, offset)
        except FileNotFoundError:
            return -errno.ENOENT

    def readdir(self, path, offset):
        try:
            p = self.path_parser.parse(path)
            return p.readdir(offset)
        except FileNotFoundError:
            return -errno.ENOENT

    def getattr(self, path):
        try:
            p = self.path_parser.parse(path)
            return p.getattr()
        except FileNotFoundError:
            return -errno.ENOENT
