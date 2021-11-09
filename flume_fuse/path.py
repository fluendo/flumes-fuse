import logging
import os
from stat import S_IFDIR, S_IFREG

import fuse
from flume.schema import Base, File, Info
from sqlalchemy.orm.collections import InstrumentedList

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class Stat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class NullField(object):
    def __str__(self):
        return ""


class Path(object):
    def __init__(self, session, prev_path=None):
        self.session = session
        self.prev_path = prev_path

    def parse(self, path):
        raise NotImplementedError

    def open(self, flags):
        raise NotImplementedError

    def read(self, size, offset):
        raise NotImplementedError

    def readdir(self, offset):
        raise NotImplementedError

    def getattr(self):
        raise NotImplementedError


class TreeTablePath(Path):
    """
    This class will parse paths in the form
    /<table>/<id>/<field>
    """

    def __init__(self, session, prev_path=None):
        super().__init__(session, prev_path=prev_path)
        self.table = None
        self.field_path = []
        self.field = None
        self.fields = []
        self.obj = None
        # In case the field is another class relationship list, keep the primary key
        # Get the name of the primary key field
        self.pk = [f.name for f in self.cls_name.__table__.columns if f.primary_key][0]

    def _get_field(self, attr):
        obj = self.obj
        field = None
        prev_obj = None
        prev_attr = None
        logger.debug("Getting fields {}".format(attr))
        # TODO avoid recursion
        while attr:
            a = attr[0]
            logger.debug("Getting field {}".format(a))
            # Handle the primary key case of an InstrumentedList
            if isinstance(obj, InstrumentedList):
                logger.debug(
                    "Handling InstrumentedList in {} for {}".format(prev_obj, obj)
                )
                # Get the relationship that matches
                r = [
                    r
                    for r in prev_obj.__class__.__mapper__.relationships
                    if r.key == prev_attr
                ][0]
                r_class = r.mapper.class_
                pk = [f.name for f in r_class.__table__.columns if f.primary_key][0]
                stmt = self.session.query(r_class).filter(getattr(r_class, pk) == a)
                result = self.session.execute(stmt)
                field = result.scalar()
            else:
                logger.debug("Handling basic field {} for {}".format(a, obj))
                field = getattr(obj, a, None)
                if not field and hasattr(obj, a):
                    logger.debug("Null field {} in {}".format(a, obj))
                    field = NullField()

            if not field:
                logger.debug("Field {} not found in {}".format(a, obj))
                break

            self.fields.append(field)
            self.field_path.append(a)

            prev_obj = obj
            prev_attr = a
            obj = field
            attr.pop(0)

        return field

    def _get_obj_contents(self, cls_name):
        logger.debug("Class name {}".format(cls_name))
        # First the fields
        for field in [f.name for f in cls_name.__table__.columns if not f.primary_key]:
            if hasattr(cls_name, field):
                yield fuse.Direntry(field)
        # Now the relationships
        for relationship in [r.key for r in cls_name.__mapper__.relationships]:
            if hasattr(cls_name, relationship):
                yield fuse.Direntry(relationship)

    def parse(self, path):
        logger.debug("Parsing {}".format(path))
        self.table = path.pop(0)

        # Check the existance of the id
        if not path:
            return
        stmt = self.session.query(self.cls_name).filter(
            getattr(self.cls_name, self.pk) == path[0]
        )
        result = self.session.execute(stmt)
        obj = result.scalar()
        if obj:
            self.obj = obj
            path.pop(0)
        else:
            raise FileNotFoundError

        # Check the existance of the field
        if path:
            self.field = self._get_field(path)

        logger.debug(
            "Obj: {}, Field: {}, Field path {}, Fields: {}".format(
                self.obj, self.field, self.field_path, self.fields
            )
        )

    def getattr(self):
        if self.field:
            # Depending on the type, if another field, dir, file otherwise
            if isinstance(self.field, Base) or isinstance(self.field, list):
                ret = Stat()
                ret.st_mode = S_IFDIR | 0o755
                ret.st_nlink = 2
            else:
                ret = Stat()
                ret.st_mode = S_IFREG | 0o444
                ret.st_size = len(str(self.field))
        else:
            ret = Stat()
            ret.st_mode = S_IFDIR | 0o755
            ret.st_nlink = 2
        return ret

    def readdir(self, offset):
        common = [".", ".."]
        for r in common:
            yield fuse.Direntry(r)

        if self.field:
            if isinstance(self.field, Base):
                yield from self._get_obj_contents(type(self.field))
            elif isinstance(self.field, InstrumentedList):
                for i in self.field:
                    # FIXME this can be done before the loop
                    list_object_id = [
                        f.name for f in type(i).__table__.columns if f.primary_key
                    ][0]
                    yield fuse.Direntry(str(getattr(i, list_object_id)))
        elif self.obj:
            yield from self._get_obj_contents(self.cls_name)
        else:
            for row in self.session.query(self.cls_name).all():
                yield fuse.Direntry(str(getattr(row, self.pk)))

    def open(self, flags):
        if not self.field:
            raise FileNotFoundError

    def read(self, size, offset):
        sfield = str(self.field)
        slen = len(sfield)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = sfield[offset : offset + size]
        else:
            buf = ""
        return bytes(buf, encoding="UTF-8")


class SearchTablePath(Path):
    """
    This class will parse paths in the form
    /<table>/<field>/<value>
    """

    def __init__(self, session, prev_path=None):
        super().__init__(session, prev_path=prev_path)
        self.table = None
        self.field = None
        self.value = None

    def parse(self, path):
        logger.debug("Parsing {}".format(path))
        self.table = path.pop(0)
        # Check the existance of the field
        if len(path):
            if path[0] in [f.name for f in self.cls_name.__table__.columns]:
                self.field = path.pop(0)
                # Check the existance of the value
                if len(path):
                    value_exists = self.session.query(
                        self.session.query(self.cls_name)
                        .filter(getattr(self.cls_name, self.field) == path[0])
                        .exists()
                    ).scalar()
                    if value_exists:
                        self.value = path.pop(0)
                    else:
                        raise FileNotFoundError
            else:
                raise FileNotFoundError


class RootPath(Path):
    def parse(self, path):
        path.pop(0)
        return 0

    def getattr(self):
        ret = Stat()
        ret.st_mode = S_IFDIR | 0o755
        # ret.st_ctime = self.now,
        # ret.st_mtime = self.now,
        # ret.st_atime = self.now,
        ret.st_nlink = 2
        return ret

    def readdir(self, offset):
        # TODO add a parameter to know if the registered path should appear at root or not
        for r in ".", "..", "files":
            yield fuse.Direntry(r)


class SearchPath(Path):
    pass


class PathParser(object):
    def __init__(self, schema):
        self.schema = schema
        self.session = self.schema.create_session()
        self.paths = {}
        # Register the root
        self.register("", RootPath)

    def register(self, d, cls):
        self.paths[d] = cls

    def parse(self, path):
        # Iterate over the path components and gneerate the
        # corresponding Path instance
        components = path.split(os.path.sep)
        parsed_root = False
        prev_path = []
        ret = None
        while components:
            p = components[0]
            # Handle the ["/", ""] case
            if not p:
                if parsed_root:
                    components.pop(0)
                    continue
                parsed_root = True
            if p in self.paths:
                pc = self.paths[p](self.session, prev_path=prev_path)
                pc.parse(components)
                ret = pc
                prev_path.append(pc)
            else:
                raise FileNotFoundError
        return ret
