from datetime import datetime

from flumes.config import Config
from flumes.options import Options
from flumes.schema import Audio, File, Info, Schema, Video

from flumes_fuse import __version__
from flumes_fuse.path import PathParser, RootPath


def test_version():
    assert __version__ == "0.1.0"


def test_path():
    options = Options()
    # Create a schema in SQLAlchemy with sqlite in memory
    args = options.parse_args(["-i", "sqlite://"])
    config = Config(args)
    schema = Schema(config)
    # Add some data
    session = schema.create_session()
    f = File(name="test.mp4", path="", mtime=datetime.now())
    info = Info(
        file=f,
        video_streams=1,
        audio_streams=1,
        subtitle_streams=0,
        seekable=True,
        duration=5000000000,
        live=False,
    )
    audio = Audio(
        info=info, media_type="audio/mpeg", bitrate=131072, channels=2, depth=8
    )
    video = Video(info=info, media_type="video/x-h264", width=1920, height=1080)

    session.add(video)
    session.add(audio)
    session.commit()
    parser = PathParser(schema)
    path = parser.parse("/")
    assert type(path) == RootPath
    # parser.parse("/files/{}".format(f.id))
