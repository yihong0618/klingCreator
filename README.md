# klingCreator
About High quality video and image generation by  https://klingai.kuaishou.com Reverse engineered API.



## How to
- Login https://klingai.kuaishou.com/ or https://klingai.com/ and generate video or images
- Use `Chrome` or other browsers to inspect the network requests (F12 -> XHR).
- Clone this REPO -> `git clone https://github.com/yihong0618/klingCreator.git`
- Copy the whole cookie.
- export KLING_COOKIE='xxxxx'.
- code [example](https://github.com/yihong0618/2024/blob/main/get_up.py)

## Usage

```
# image
python -m kling --prompt 'a big dog'
# image based on image
python -m kling --prompt 'wear a yellow hat' -I dog.png

# video
python -m kling --type video --prompt 'a big running cat'
# high quality
python -m kling --type video --prompt 'a big running cat' --high-quality
# video based on image
python -m kling --type video --prompt 'make this picture alive'  -I cat.png
# high quality
python -m kling --type video --prompt 'make this picture alive'  -I cat.png --high-quality
# if you want extend the video length to 10s
python -m kling --type video --prompt 'make this picture alive'  -I cat.png --high-quality --extend
```

or
```
pip install -U kling-creator 
```

```python
from kling import ImageGen, VideoGen
i = ImageGen('cookie') # Replace 'cookie'
i.save_image("a blue cyber dream", './output')
# xxxx_url means your based kling ur
i.save_images("a blue cyber dream", './output', image_url="xxxx.png")

v = VideoGen('cookie') # Replace 'cookie' 
# xxxx_url means your based kling ur
v.save_video("a blue cyber dream", './output', image_url="xxxxx_url.png")
# you can also use high quality
v.save_video("a blue cyber dream", './output', image_url="xxxxx_url.png", is_high_quality=True)

# extend the video length to 10s with video id
v.extend_video(video_id, prompt="a blue cyber dream")

# or you just want to get auto extend the video
v.save_video("a blue cyber dream", './output', image_url="xxxxx_url.png", is_high_quality=True, auto_extend=True)
```