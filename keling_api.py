from kling import ImageGen, VideoGen
KLING_COOKIE="weblogger_did=web_7635309589C8F653; did=web_0fe1782299187fb4acb3fe2115cca4a74f14; multi-id-guide-new=true; dev-center-view-update-2025-01-07=true; release-notes-2025-01-23=true; multi-id-guide-cut=true; reference-image-guide=true; motivate-publish-image=true; skip-background-questionnaire=true; apdid=1ecf953a-688d-4fa0-a244-6c5517c010debcb485e7e62cdfde13ac06387cb34265:1740471112:1; hdige2wqwoino=PcxXKmbYrEXi3am8BpCKpQTP7kZHYePXcb28fac4; __risk_web_device_id=8a77b3851741005721032b01; userId=4241677602; motivate-publish-video=true; ehid=23cY-3i6y2Y_mfNasTSn2NJFdqroSGCtigUty; kuaishou.ai.portal_st=ChVrdWFpc2hvdS5haS5wb3J0YWwuc3QSoAGR3UgqqE9UvGDYJdOY82l-YE9XMMgVeIQaIXcuvpCm5LwCUHLjZBPdhAeDrDBPqY5GywxGEaYFygkQ6ZRpp7EKqFD75s08ryOGyHfmuFNk_9kLkklF__YpeFYudZuu5FRKGsphGnB7YwA6vOEB5El0sbWeigLLXADirpQKxRUVib8rJiztAcLT0ag8USFVC0yTIpMikKPnAY3pXK-ElPMYGhJXq8A1lpx7E_t82njEhNQYCW0iIPpTLQv-BSkBWDJRhuiCO-Z-Hi-JIhhdDEqlU5rn85xUKAUwAQ; kuaishou.ai.portal_ph=a4e15d3c3dcb7324b948cbcdd4cb9164c1e2"
i = ImageGen(KLING_COOKIE) # Replace 'cookie'
i.save_images("a blue cyber dream", './output')
# xxxx_url means your based kling ur
# i.save_images("a blue cyber dream", './output', image_url="xxxx.png")

v = VideoGen(KLING_COOKIE) # Replace 'cookie' 
# xxxx_url means your based kling ur
# v.save_video("a blue cyber dream", './output', image_url="xxxxx_url.png")
# you can also use high quality
# v.save_video("a blue cyber dream", './output', image_url="xxxxx_url_high_quality.png", is_high_quality=True)

# # extend the video length to 10s with video id
# v.extend_video(video_id, prompt="a blue cyber dream")

# or you just want to get auto extend the video
# v.save_video("a blue cyber dream", './output', image_url="xxxxx_url.png", is_high_quality=True, auto_extend=True)

# if you want to use new 1.5 model
v.save_video("a blue cyber dream", './output' is_high_quality=True, model_name="1.5")