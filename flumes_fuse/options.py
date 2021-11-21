from flumes.options import Options
from fuse import FuseOptParse


class FlumesFuseOptions(FuseOptParse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = Options()
        for o in options._actions[1:]:
            self.add_option(mountopt=o.dest, action="store", help=o.help)
