import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from kling import ImageGen, VideoGen, BaseGen, call_for_daily_check, TaskStatus

import pytest
from unittest.mock import patch, MagicMock, mock_open


@pytest.fixture
def mock_session():
    with patch("requests.Session") as mock:
        yield mock.return_value


@pytest.fixture
def base_gen(mock_session):
    return BaseGen("mock_cookie")


@pytest.fixture
def image_gen(mock_session):
    return ImageGen("mock_cookie")


@pytest.fixture
def video_gen(mock_session):
    return VideoGen("mock_cookie")


def test_base_gen_init(base_gen):
    assert isinstance(base_gen, BaseGen)
    assert base_gen.cookie == "mock_cookie"


def test_image_gen_init(image_gen):
    assert isinstance(image_gen, ImageGen)
    assert image_gen.cookie == "mock_cookie"


def test_video_gen_init(video_gen):
    assert isinstance(video_gen, VideoGen)
    assert video_gen.cookie == "mock_cookie"


def test_parse_cookie_string():
    cookie_string = "key1=value1; key2=value2; kuaishou_key=value3"
    cookiejar, is_cn = BaseGen.parse_cookie_string(cookie_string)
    assert is_cn == True
    assert dict(cookiejar) == {
        "key1": "value1",
        "key2": "value2",
        "kuaishou_key": "value3",
    }


@pytest.mark.parametrize("gen_class", [ImageGen, VideoGen])
def test_get_account_point(gen_class, mock_session):
    gen = gen_class("mock_cookie")
    mock_session.get.return_value.json.side_effect = [
        {"status": 200},
        {"status": 200, "data": {"total": 1000}},
    ]
    assert gen.get_account_point() == 10.0


@patch("builtins.open", new_callable=MagicMock)
def test_image_uploader(mock_open, image_gen, mock_session):
    mock_open.return_value.__enter__.return_value.read.return_value = b"image_data"
    mock_session.get.return_value.json.side_effect = [
        {"status": 200, "data": {"token": "mock_token"}},
        {"result": 1},
        {"status": 200, "data": {"url": "mock_url"}},
    ]
    mock_session.post.return_value.json.side_effect = [{"result": 1}, {"result": 1}]

    result = image_gen.image_uploader("mock_image_path")
    assert result == "mock_url"


def test_fetch_metadata(base_gen, mock_session):
    mock_session.get.return_value.json.return_value = {
        "data": {"status": 100, "key": "value"}
    }
    result, status = base_gen.fetch_metadata("mock_task_id")
    assert result == {"status": 100, "key": "value"}
    assert status == TaskStatus.COMPLETED

    mock_session.get.return_value.json.return_value = {"data": {"status": 50}}
    result, status = base_gen.fetch_metadata("mock_task_id")
    assert result == {"status": 50}
    assert status == TaskStatus.FAILED

    mock_session.get.return_value.json.return_value = {"data": {"status": 80}}
    result, status = base_gen.fetch_metadata("mock_task_id")
    assert result == {"status": 80}
    assert status == TaskStatus.PENDING


@pytest.mark.parametrize(
    "gen_class,method_name", [(ImageGen, "get_images"), (VideoGen, "get_video")]
)
def test_get_content(gen_class, method_name, mock_session):
    gen = gen_class("mock_cookie")
    mock_session.post.return_value.json.return_value = {
        "data": {"task": {"id": "mock_id"}}
    }
    mock_session.get.return_value.json.return_value = {
        "data": {"status": 100, "works": [{"resource": {"resource": "mock_resource"}}]}
    }

    method = getattr(gen, method_name)
    result = method("mock_prompt")
    assert result == ["mock_resource"]


@pytest.mark.parametrize(
    "gen_class,method_name", [(ImageGen, "save_images"), (VideoGen, "save_video")]
)
@patch("os.path.exists", return_value=False)
@patch("os.mkdir")
def test_save_content(mock_mkdir, mock_exists, gen_class, method_name, mock_session):
    gen = gen_class("mock_cookie")
    mock_session.post.return_value.json.return_value = {
        "data": {"task": {"id": "mock_id"}}
    }
    mock_session.get.return_value.json.return_value = {
        "data": {"status": 100, "works": [{"resource": {"resource": "mock_resource"}}]}
    }

    mock_session.get.return_value.status_code = 200

    with patch("builtins.open", new_callable=MagicMock):
        method = getattr(gen, method_name)
        method("mock_prompt", "mock_output_dir")

    mock_mkdir.assert_called_once_with("mock_output_dir")


def test_call_for_daily_check():
    mock_session = MagicMock()
    mock_session.get.return_value.ok = True
    mock_session.get.return_value.json.return_value = {"status": "success"}

    result = call_for_daily_check(mock_session, True)
    assert result == True

    mock_session.get.return_value.ok = False
    with pytest.raises(Exception):
        call_for_daily_check(mock_session, False)


@patch("builtins.open", new_callable=mock_open, read_data=b"mock_image_data")
@patch.object(VideoGen, "image_uploader", return_value="mock_image_url")
def test_video_gen_get_video(mock_uploader, mock_file, video_gen, mock_session):
    mock_session.post.return_value.json.return_value = {
        "data": {"task": {"id": "mock_id"}}
    }
    mock_session.get.return_value.json.return_value = {
        "data": {"status": 100, "works": [{"resource": {"resource": "mock_video_url"}}]}
    }

    result = video_gen.get_video("mock_prompt")
    assert result == ["mock_video_url"]

    result = video_gen.get_video("mock_prompt", image_path="mock_image.jpg")
    assert result == ["mock_video_url"]

    result = video_gen.get_video("mock_prompt", image_url="http://mock.com/image.jpg")
    assert result == ["mock_video_url"]

    result = video_gen.get_video("mock_prompt", is_high_quality=True)
    assert result == ["mock_video_url"]


@patch("os.path.exists", return_value=False)
@patch("os.mkdir")
@patch("builtins.open", new_callable=mock_open)
def test_video_gen_save_video(
    mock_file, mock_mkdir, mock_exists, video_gen, mock_session
):
    mock_session.post.return_value.json.return_value = {
        "data": {"task": {"id": "mock_id"}}
    }
    mock_session.get.return_value.json.return_value = {
        "data": {"status": 100, "works": [{"resource": {"resource": "mock_video_url"}}]}
    }
    mock_session.get.return_value.content = b"mock_video_content"
    mock_session.get.return_value.status_code = 200

    video_gen.save_video("mock_prompt", "mock_output_dir")

    mock_mkdir.assert_called_once_with("mock_output_dir")
    mock_file.assert_called_once_with("mock_output_dir/0.mp4", "wb")
    mock_file().write.assert_called_once_with(b"mock_video_content")


@patch("builtins.open", new_callable=mock_open, read_data=b"mock_image_data")
@patch.object(ImageGen, "image_uploader", return_value="mock_image_url")
def test_image_gen_get_images(mock_uploader, mock_file, image_gen, mock_session):
    mock_session.post.return_value.json.return_value = {
        "data": {"task": {"id": "mock_id"}}
    }
    mock_session.get.return_value.json.return_value = {
        "data": {"status": 100, "works": [{"resource": {"resource": "mock_image_url"}}]}
    }

    result = image_gen.get_images("mock_prompt")
    assert result == ["mock_image_url"]

    result = image_gen.get_images("mock_prompt", image_path="mock_image.jpg")
    assert result == ["mock_image_url"]

    result = image_gen.get_images("mock_prompt", image_url="http://mock.com/image.jpg")
    assert result == ["mock_image_url"]


@patch("os.path.exists", return_value=False)
@patch("os.mkdir")
@patch("builtins.open", new_callable=mock_open)
@patch("threading.Thread")
def test_image_gen_save_images(
    mock_thread, mock_file, mock_mkdir, mock_exists, image_gen, mock_session
):
    mock_session.post.return_value.json.return_value = {
        "data": {"task": {"id": "mock_id"}}
    }
    mock_session.get.return_value.json.return_value = {
        "data": {"status": 100, "works": [{"resource": {"resource": "mock_image_url"}}]}
    }
    mock_session.get.return_value.content = b"mock_image_content"

    image_gen.save_images("mock_prompt", "mock_output_dir")

    mock_mkdir.assert_called_once_with("mock_output_dir")
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()
    mock_thread.return_value.join.assert_called_once()


if __name__ == "__main__":
    pytest.main()
