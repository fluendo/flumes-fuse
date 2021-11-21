import logging
import os
from stat import S_IFDIR, S_IFREG

import fuse
from flumes.schema import Base, File, Info
from sqlalchemy.orm.collections import InstrumentedList

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class VirtualFile(object):
    def __init__(self, session, obj):
        self.session = session
        self.obj = obj

    def read(self, size, offset):
        raise NotImplementedError

    def getattr(self):
        raise NotImplementedError


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
    def __init__(self, session):
        self.session = session

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


class TablePath(Path):
    """
    Base class for common methods on Paths related to a table
    """

    cls_name = None

    def _get_columns(self, obj=None, with_primary_key=False):
        # In case we want to explore a table out of the defined table, for relationships
        # for example
        if obj:
            cls_name = type(obj)
        else:
            cls_name = self.cls_name
        ret = []
        for field in [f for f in cls_name.__table__.columns]:
            if not with_primary_key and field.primary_key:
                continue
            if hasattr(cls_name, field.name):
                ret.append(field.name)
        return ret


class TreeTablePath(TablePath):
    """
    This class will parse paths in the form
    /<table>/<id>/<field>
    """

    def __init__(self, session, **kwargs):
        super().__init__(session)
        self.table = None
        self.field_path = []
        self.field = None
        self.fields = []
        self.obj = None
        # In case the field is another class relationship list, keep the primary key
        # Get the name of the primary key field
        self.pk = [f.name for f in self.cls_name.__table__.columns if f.primary_key][0]
        self.filtered_stmt = None
        if kwargs:
            self.filtered_stmt = kwargs.get("filtered")

    def _get_relationships(self, obj):
        cls_name = type(obj)
        ret = []
        for relationship in [r for r in cls_name.__mapper__.relationships]:
            r = relationship.key
            logger.debug("Relationship {}".format(r))
            if hasattr(cls_name, r):
                # Avoid a relationship that we have traversed already
                # We won't move to the class this Path points to
                if relationship.mapper.class_ == self.cls_name:
                    logger.debug("Avoid pointing to '{}' again".format(cls_name))
                    continue
                # We don't want to traverse again the same object as before
                # FIXME Check the path, assuming the there are no columns with the same name
                if r in self.field_path:
                    logger.debug(
                        "Relationship already traversed {} {}".format(
                            r, self.field_path
                        )
                    )
                    continue
                # Check the actual object
                field = getattr(obj, r, None)
                if field in self.fields:
                    logger.debug(
                        "Relationship already traversed {} {}".format(
                            r, self.field_path
                        )
                    )
                    continue
                ret.append(r)
        return ret

    def _get_field(self, attr):
        obj = self.obj
        field = None
        prev_obj = None
        prev_attr = None
        logger.debug("Getting fields {}".format(attr))
        while attr:
            a = attr[0]
            field = None
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
            elif a in [vf[0] for vf in self.extra_fields]:
                logger.debug("Handling extra field {}".format(a))
                field = [vf[1] for vf in self.extra_fields if vf[0] == a][0](
                    self.session, self.obj
                )
            else:
                logger.debug("Handling basic field {} for {}".format(a, obj))
                if a in self._get_columns(obj) or a in self._get_relationships(obj):
                    field = getattr(obj, a, None)
                    if not field:
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

    def _get_obj_contents(self, obj):
        cls_name = type(obj)
        logger.debug("Class name {}".format(cls_name))
        # First the fields
        for field in self._get_columns(obj):
            yield fuse.Direntry(field)
        # Now the relationships
        for relationship in self._get_relationships(obj):
            yield fuse.Direntry(relationship)

    def parse(self, path):
        logger.debug("Parsing {}".format(path))
        # Reset vars
        self.table = None
        self.field_path = []
        self.field = None
        self.fields = []
        self.obj = None

        path.pop(0)
        self.table = self.cls_name

        # Check the existance of the id
        if not path:
            return
        if self.filtered_stmt == None:
            stmt = self.session.query(self.cls_name)
        else:
            stmt = self.filtered_stmt
        stmt = stmt.filter(getattr(self.cls_name, self.pk) == path[0])
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
            elif isinstance(self.field, VirtualFile):
                ret = self.field.getattr()
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
        logger.debug("Reading directory {}".format(self.field_path))
        common = [".", ".."]
        for r in common:
            yield fuse.Direntry(r)

        if self.field:
            if isinstance(self.field, Base):
                yield from self._get_obj_contents(self.field)
            elif isinstance(self.field, InstrumentedList):
                for i in self.field:
                    # FIXME this can be done before the loop
                    list_object_id = [
                        f.name for f in type(i).__table__.columns if f.primary_key
                    ][0]
                    yield fuse.Direntry(str(getattr(i, list_object_id)))
        elif self.obj:
            # Get the columns and relationships
            yield from self._get_obj_contents(self.obj)
            # Get the extra fields
            for ef in self.extra_fields:
                yield fuse.Direntry(ef[0])
        else:
            if self.filtered_stmt == None:
                stmt = self.session.query(self.cls_name)
            else:
                stmt = self.filtered_stmt
            result = self.session.execute(stmt)
            for row in result.scalars().all():
                yield fuse.Direntry(str(getattr(row, self.pk)))

    def open(self, flags):
        if not self.field:
            raise FileNotFoundError

    def read(self, size, offset):
        if isinstance(self.field, VirtualFile):
            return self.field.read(size, offset)
        else:
            sfield = str(self.field)
            slen = len(sfield)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = sfield[offset : offset + size]
            else:
                buf = ""
            return bytes(buf, encoding="UTF-8")


class SearchTablePath(TablePath):
    """
    This class will parse paths in the form
    /<table>/<field>/<value>
    """

    def __init__(self, session, **kwargs):
        super().__init__(session)
        self.table = None
        self.field = None
        self.value = None

    def get_filter_clause(self, stmt):
        return stmt.filter(getattr(self.cls_name, self.field) == self.value)

    def parse(self, path):
        logger.debug("Parsing {}".format(path))
        path.pop(0)
        self.table = self.cls_name
        # Check the existance of the field
        if len(path):
            if path[0] in [f.name for f in self.cls_name.__table__.columns]:
                self.field = path.pop(0)
                # Check the existance of the value
                if len(path):
                    value = path[0].replace("_-_", os.path.sep)
                    value_exists = self.session.query(
                        self.session.query(self.cls_name)
                        .filter(getattr(self.cls_name, self.field) == value)
                        .exists()
                    ).scalar()
                    if value_exists:
                        self.value = value
                        path.pop(0)
                    else:
                        raise FileNotFoundError
            else:
                raise FileNotFoundError

    def getattr(self):
        ret = Stat()
        ret.st_mode = S_IFDIR | 0o755
        # ret.st_ctime = self.now,
        # ret.st_mtime = self.now,
        # ret.st_atime = self.now,
        ret.st_nlink = 2
        return ret

    def readdir(self, offset):
        common = [".", ".."]
        for r in common:
            yield fuse.Direntry(r)
        if not self.field:
            # Get all the columns
            for f in self._get_columns():
                yield fuse.Direntry(f)
        else:
            # Get all the values
            stmt = self.session.query(getattr(self.cls_name, self.field)).distinct()
            result = self.session.execute(stmt)
            for obj in result.scalars():
                # Make the value "pathable", change / by _-_
                dirname = str(obj).replace(os.path.sep, "_-_")
                yield fuse.Direntry(dirname)


class RootPath(Path):
    cls_paths = []

    def __init__(self, session, **kwargs):
        super().__init__(session)
        self.child_path = None

    def parse(self, paths):
        self.child_path = None
        paths.pop(0)
        while paths:
            p = paths[0]
            # The case ["", ""] for "/"
            if not p:
                paths.pop(0)
                continue
            found = False
            for name, cls in self.cls_paths:
                if p != name:
                    continue
                pc = cls(self.session)
                pc.parse(paths)
                self.child_path = pc
                found = True
            if not found:
                raise FileNotFoundError

    def open(self, flags):
        if not self.child_path:
            raise FileNotFoundError
        else:
            return self.child_path.open(flags)

    def read(self, size, offset):
        if not self.child_path:
            raise FileNotFoundError
        else:
            return self.child_path.read(size, offset)

    def getattr(self):
        if not self.child_path:
            ret = Stat()
            ret.st_mode = S_IFDIR | 0o755
            # ret.st_ctime = self.now,
            # ret.st_mtime = self.now,
            # ret.st_atime = self.now,
            ret.st_nlink = 2
            return ret
        else:
            return self.child_path.getattr()

    def readdir(self, offset):
        if not self.child_path:
            for r in ".", "..":
                yield fuse.Direntry(r)
            for p, _unsued in self.cls_paths:
                yield fuse.Direntry(p)
        else:
            yield from self.child_path.readdir(offset)


class SearchPath(Path):
    """
    This class will parse paths in the form
    /<search/<query>/<query>/<results>
    """

    queries = []
    results = None

    def __init__(self, session, **kwargs):
        super().__init__(session)
        self.child_paths = []
        self.result_path = None

    def parse(self, paths):
        self.child_paths = []
        paths.pop(0)
        while paths:
            p = paths[0]
            found = False
            for name, cls in self.queries:
                if p != name:
                    continue
                pc = cls(self.session)
                pc.parse(paths)
                self.child_paths.append(pc)
                found = True

            if not found and not self.result_path:
                # Check we are in the results level
                if p == "results":
                    # Get the select statement to generate the dynamic query
                    stmt = self.get_join_stmt()
                    # Get the filters for each query
                    for q in self.child_paths:
                        stmt = q.get_filter_clause(stmt)
                    stmt = stmt.distinct()
                    self.result_path = self.results(self.session, filtered=stmt)
                    self.result_path.parse(paths)
                else:
                    raise FileNotFoundError

    def open(self, flags):
        if self.result_path:
            return self.result_path.open(flags)
        elif self.child_paths:
            return self.child_paths[-1].open(flags)
        else:
            raise FileNotFoundError

    def read(self, size, offset):
        if self.result_path:
            return self.result_path.read(size, offset)
        elif self.child_paths:
            return self.child_paths[-1].read(size, offset)
        else:
            raise FileNotFoundError

    def getattr(self):
        if self.result_path:
            return self.result_path.getattr()
        elif self.child_paths:
            return self.child_paths[-1].getattr()
        else:
            ret = Stat()
            ret.st_mode = S_IFDIR | 0o755
            # ret.st_ctime = self.now,
            # ret.st_mtime = self.now,
            # ret.st_atime = self.now,
            ret.st_nlink = 2
            return ret

    def readdir(self, offset):
        if self.result_path:
            yield from self.result_path.readdir(offset)
        else:
            ask_child = True
            if not self.child_paths:
                ask_child = False
            elif self.child_paths and self.child_paths[-1].value:
                ask_child = False

            for r in ".", "..":
                yield fuse.Direntry(r)
            if ask_child:
                yield from self.child_paths[-1].readdir(offset)
            else:
                for p, _unsued in self.queries:
                    yield fuse.Direntry(p)
                yield fuse.Direntry("results")


class PathParser(object):
    def __init__(self, schema, root):
        self.schema = schema
        self.session = self.schema.create_session()
        self.root = root(self.session)
        self.paths = []

    def parse(self, path):
        if not len(path):
            raise FileNotFoundError
        # corresponding Path instance
        self.paths = path.split(os.path.sep)
        self.root.parse(list(self.paths))

    def open(self, flags):
        logger.debug("Open {}".format(self.paths))
        return self.root.open(flags)

    def read(self, size, offset):
        logger.debug("Read {}".format(self.paths))
        return self.root.read(size, offset)

    def readdir(self, offset):
        logger.debug("Readdir {}".format(self.paths))
        return self.root.readdir(offset)

    def getattr(self):
        logger.debug("Getattr {}".format(self.paths))
        return self.root.getattr()
