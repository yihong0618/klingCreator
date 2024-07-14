# klingCreator
About High quality video and image generation by  https://klingai.kuaishou.com Reverse engineered API.



## How to
- Login https://klingai.kuaishou.com/ and generate video or images
- Use `Chrome` or other browsers to inspect the network requests (F12 -> XHR).
- Clone this REPO -> `git clone https://github.com/yihong0618/klingCreator.git`
- Copy the cookie.
- export Kling_COOKIE='xxxxx'.

## Usage

```
# image
python -m kling --prompt 'a big dog'
# image based on image
python -m kling --prompt 'wear a yellow hat' -I dog.png

# video
python -m kling --type video --prompt 'make this picture alive'
# video based on image
python -m kling --type video --prompt 'make this picture alive'  -I cat.png

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
i.save_image("a blue cyber dream", './output', image_url="xxxx.png")

v = VideoGen('cookie') # Replace 'cookie' 
# xxxx_url means your based kling ur
v.save_video("a blue cyber dream", './output', image_url="xxxxx_url.png")
```
