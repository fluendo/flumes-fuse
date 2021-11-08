#!/usr/bin/env python

import sys

from flume_fuse.fs import FlumeFuse
from flume_fuse.options import FlumeFuseOptions


def main(args=None):
    # SQlite driver "can not work" in a multithread environment
    # Make the option always available
    fuse = FlumeFuse(parser_class=FlumeFuseOptions, dash_s_do="setsingle")
    args = fuse.parse(values=fuse)
    fuse.main()


if __name__ == "__main__":
    main(sys.argv[1:])
