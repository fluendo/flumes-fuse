from datetime import datetime

from flumes.config import Config
from flumes.options import Options
from flumes.schema import Audio, File, Info, Schema, Video

from flumes_fuse import __version__
from flumes_fuse.fs import Root


def test_version():
    """The purpose of this test is to verify that the version of the package
    is the expected"""
    assert __version__ == "0.1.2"


def test_root_path():
    """The purpose of this test is to verify that the content of root path
    used by fuse to generate the filesystem is as expected"""

    # Create a schema in SQLAlchemy with sqlite in memory
    options = Options()
    args = options.parse_args(["-i", "sqlite://", "-b", ":memory:"])
    config = Config(args)
    schema = Schema(config)

    # Create an SQL session and add a dummy file entry to the database
    session = schema.create_session()
    dummy_file = File(name="test.mp4", path="", mtime=datetime.now())
    dummy_info = Info(
        file=dummy_file,
        video_streams=1,
        audio_streams=1,
        subtitle_streams=0,
        seekable=True,
        duration=5000000000,
        live=False,
    )
    dummy_audio = Audio(
        info=dummy_info, media_type="audio/mpeg", bitrate=131072, channels=2, depth=8
    )
    dummy_video = Video(
        info=dummy_info, media_type="video/x-h264", width=1920, height=1080
    )

    session.add(dummy_video)
    session.add(dummy_audio)
    session.commit()

    # Initialize root path based on current SQL session
    root = Root(session)

    # Expected values for root path content
    expected_root_path_content = [".", ".."]
    for i in range(len(root.cls_paths)):
        expected_root_path_content.append(str(root.cls_paths[i][0]))

    # Actual values of root path content
    actual_root_path_content = [entry.name for entry in root.readdir(0)]

    # Assert that the actual content of root path coincides with the expected
    assert actual_root_path_content == expected_root_path_content
