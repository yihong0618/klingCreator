import argparse
import os
import time
import contextlib
from http.cookies import SimpleCookie

from fake_useragent import UserAgent
import requests
from requests.utils import cookiejar_from_dict
from rich import print
import threading

browser_version = "edge101"
ua = UserAgent(browsers=["edge"])
base_url = "https://klingai.kuaishou.com/"

# for daily login to get token
daily_url = "https://klingai.kuaishou.com/api/pay/reward?activity=login_bonus_daily"


def call_for_daily_login(session):
    # TODO support out of China
    r = session.get(daily_url)
    if r.ok:
        print("Call daily login success")
        return r.json()
    raise Exception(f"Call daily login failed {r.text}")


class BaseGen:
    def __init__(self, cookie: str) -> None:
        self.session: requests.Session = requests.Session()
        self.cookie = cookie
        self.session.cookies = self.parse_cookie_string(self.cookie)
        self.session.headers["user-agent"] = ua.random
        self.apis_dict = {
            "image_upload_gettoken": "https://klingai.kuaishou.com/api/upload/issue/token?filename=",
            "image_upload_resume": "https://upload.kuaishouzt.com/api/upload/resume?upload_token=",
            "image_upload_fragment": "https://upload.kuaishouzt.com/api/upload/fragment",
            "image_upload_complete": "https://upload.kuaishouzt.com/api/upload/complete",
            "image_upload_geturl": "https://klingai.kuaishou.com/api/upload/verify/token?token=",
        }
        self.submit_url = "https://klingai.kuaishou.com/api/task/submit"
        call_for_daily_login(self.session)

    @staticmethod
    def parse_cookie_string(cookie_string):
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        cookies_dict = {}
        cookiejar = None
        for key, morsel in cookie.items():
            cookies_dict[key] = morsel.value
            cookiejar = cookiejar_from_dict(
                cookies_dict, cookiejar=None, overwrite=True
            )
        return cookiejar

    def image_uploader(self, image_path) -> str:
        """
        from https://github.com/dolacmeo/acfunsdk/blob/ece6f42e2736b316fea35d89ba1d0ccbec6c98f7/acfun/page/utils.py
        great thanks to him
        """
        with open(image_path, "rb") as f:
            image_data = f.read()
        # get the image file name
        file_name = image_path.split("/")[-1]
        upload_url = self.apis_dict["image_upload_gettoken"] + file_name
        token_req = self.session.get(upload_url)
        token_data = token_req.json()

        assert token_data.get("status") == 200

        token = token_data["data"]["token"]
        resume_url = self.apis_dict["image_upload_resume"] + token
        resume_req = self.session.get(resume_url)
        resume_data = resume_req.json()

        assert resume_data.get("result") == 1
        fragment_req = self.session.post(
            self.apis_dict["image_upload_fragment"],
            data=image_data,
            params=dict(upload_token=token, fragment_id=0),
            headers={"Content-Type": "application/octet-stream"},
        )
        fragment_data = fragment_req.json()
        assert fragment_data.get("result") == 1
        complete_req = self.session.post(
            self.apis_dict["image_upload_complete"],
            params=dict(upload_token=token, fragment_count=1),
        )
        complete_data = complete_req.json()
        assert complete_data.get("result") == 1
        verify_url = self.apis_dict["image_upload_geturl"] + token
        result_req = self.session.get(verify_url)
        result_data = result_req.json()
        assert result_data.get("status") == 200
        return result_data.get("data").get("url")

    def fetch_metadata(self, task_id: str) -> dict:
        url = f"https://klingai.kuaishou.com/api/task/status?taskId={task_id}"
        response = self.session.get(url)
        data = response.json().get("data")
        assert data is not None
        # this is very interesting it use resolution to check if the image is ready
        if data.get("status") >= 90:
            return data
        else:
            return None


class VideoGen(BaseGen):
    def get_video(
        self,
        prompt: str,
        image_path: str | None = None,
        image_url: str | None = None,
        is_high_quality: bool = False,
    ) -> list:
        self.session.headers["user-agent"] = ua.random
        if image_path or image_url:
            if image_path:
                image_payload_url = self.image_uploader(image_path)
            else:
                image_payload_url = image_url
            if is_high_quality:
                model_type = "m2v_img2video_hq"
            else:
                model_type = "m2v_img2video"
            payload = {
                "arguments": [
                    {"name": "prompt", "value": prompt},
                    {
                        "name": "negative_prompt",
                        "value": "",
                    },
                    {
                        "name": "cfg",
                        "value": "0.5",
                    },
                    {
                        "name": "duration",
                        "value": "5",
                    },
                    {
                        "name": "tail_image_enabled",
                        "value": "false",
                    },
                    {
                        "name": "camera_json",
                        "value": '{"type":"empty","horizontal":0,"vertical":0,"zoom":0,"tilt":0,"pan":0,"roll":0}',
                    },
                    {
                        "name": "biz",
                        "value": "klingai",
                    },
                ],
                "inputs": [
                    {
                        "inputType": "URL",
                        "url": image_payload_url,
                        "name": "input",
                    },
                ],
                "type": model_type,
            }

        else:
            if is_high_quality:
                model_type = "m2v_txt2video_hq"
            else:
                model_type = "m2v_txt2video"
            payload = {
                "arguments": [
                    {"name": "prompt", "value": prompt},
                    {
                        "name": "negative_prompt",
                        "value": "",
                    },
                    {
                        "name": "cfg",
                        "value": "0.5",
                    },
                    {
                        "name": "duration",
                        "value": "5",
                    },
                    {
                        "name": "aspect_ratio",
                        "value": "16:9",
                    },
                    {
                        "name": "camera_json",
                        "value": '{"type":"empty","horizontal":0,"vertical":0,"zoom":0,"tilt":0,"pan":0,"roll":0}',
                    },
                    {
                        "name": "biz",
                        "value": "klingai",
                    },
                ],
                "inputs": [],
                "type": model_type,
            }

        response = self.session.post(
            self.submit_url,
            json=payload,
        )
        if not response.ok:
            print(response.text)
            raise Exception(f"Error response {str(response)}")
        response_body = response.json()
        if response_body.get("data").get("status") == 7:
            message = response_body.get("data").get("message")
            raise Exception(f"Request failed message {message}")
        request_id = response_body.get("data", {}).get("task", {}).get("id")
        if not request_id:
            raise Exception("Could not get request ID")
        start_wait = time.time()
        print("Waiting for results... will take 2mins to 5mins")
        while True:
            if int(time.time() - start_wait) > 1200:
                raise Exception("Request timeout")
            image_data = self.fetch_metadata(request_id)
            if not image_data:
                print(".", end="", flush=True)
                # spider rule
                time.sleep(5)
            else:
                result = []
                works = image_data.get("works", [])
                if not works:
                    print("No images found.")
                    return []
                else:
                    for work in works:
                        resource = work.get("resource", {}).get("resource")
                        if resource:
                            result.append(resource)
                return result

    def save_video(
        self,
        prompt: str,
        output_dir: str,
        image_path: str | None = None,
        image_url: str | None = None,
        is_high_quality: bool = False,
    ) -> None:
        mp4_index = 0
        try:
            links = self.get_video(prompt, image_path, image_url, is_high_quality)
        except Exception as e:
            print(e)
            raise
        with contextlib.suppress(FileExistsError):
            os.mkdir(output_dir)
        print()
        for link in links:
            while os.path.exists(os.path.join(output_dir, f"{mp4_index}.mp4")):
                mp4_index += 1
            print(link)
            response = self.session.get(link)
            if response.status_code != 200:
                raise Exception("Could not download image")
            # save response to file
            with open(
                os.path.join(output_dir, f"{mp4_index}.mp4"), "wb"
            ) as output_file:
                output_file.write(response.content)
            mp4_index += 1


class ImageGen(BaseGen):
    def get_images(
        self, prompt: str, image_path: str | None = None, image_url: str | None = None
    ) -> list:
        self.session.headers["user-agent"] = ua.random
        if image_path or image_url:
            if image_path:
                image_payload_url = self.image_uploader(image_path)
            else:
                image_payload_url = image_url
            payload = {
                "arguments": [
                    {"name": "prompt", "value": prompt},
                    {
                        "name": "style",
                        "value": "默认",
                    },
                    {
                        "name": "aspect_ratio",
                        "value": "1:1",
                    },
                    {
                        "name": "imageCount",
                        "value": "4",
                    },
                    {
                        "name": "fidelity",
                        "value": "0.5",
                    },
                    {
                        "name": "biz",
                        "value": "klingai",
                    },
                ],
                "type": "mmu_img2img_aiweb",
                "inputs": [
                    {
                        "inputType": "URL",
                        "url": image_payload_url,
                        "name": "input",
                    },
                ],
            }
        else:
            payload = {
                "arguments": [
                    {
                        "name": "prompt",
                        "value": prompt,
                    },
                    {
                        "name": "style",
                        "value": "默认",
                    },
                    {
                        "name": "aspect_ratio",
                        "value": "1:1",
                    },
                    {
                        "name": "imageCount",
                        "value": "4",
                    },
                    {
                        "name": "biz",
                        "value": "klingai",
                    },
                ],
                "type": "mmu_txt2img_aiweb",
                "inputs": [],
            }

        response = self.session.post(
            self.submit_url,
            json=payload,
        )
        if not response.ok:
            print(response.text)
            raise Exception(f"Error response {str(response)}")
        response_body = response.json()
        if response_body.get("data").get("status") == 7:
            message = response_body.get("data").get("message")
            raise Exception(f"Request failed message {message}")
        request_id = response_body.get("data", {}).get("task", {}).get("id")
        if not request_id:
            raise Exception("Could not get request ID")
        start_wait = time.time()
        print("Waiting for results...")
        while True:
            if int(time.time() - start_wait) > 600:
                raise Exception("Request timeout")
            image_data = self.fetch_metadata(request_id)
            if not image_data:
                print(".", end="", flush=True)
                # spider rule
                time.sleep(2)
            else:
                result = []
                works = image_data.get("works", [])
                if not works:
                    print("No images found.")
                    return []
                else:
                    for work in works:
                        resource = work.get("resource", {}).get("resource")
                        if resource:
                            result.append(resource)
                return result

    def save_images(
        self,
        prompt: str,
        output_dir: str,
        image_path: str | None = None,
        image_url: str | None = None,
    ) -> None:
        png_index = 0
        try:
            links = self.get_images(prompt, image_path, image_url)
        except Exception as e:
            print(e)
            raise
        with contextlib.suppress(FileExistsError):
            os.mkdir(output_dir)
        print()

        def download_image(link: str, index: int) -> None:
            response = self.session.get(link)
            if response.status_code != 200:
                raise Exception("Could not download image")
            # save response to file
            with open(os.path.join(output_dir, f"{index}.png"), "wb") as output_file:
                output_file.write(response.content)

        threads = []
        for link in links:
            while os.path.exists(os.path.join(output_dir, f"{png_index}.png")):
                png_index += 1
            print(link)
            thread = threading.Thread(target=download_image, args=(link, png_index))
            threads.append(thread)
            thread.start()
            png_index += 1

        # Wait for all threads to complete
        for thread in threads:
            thread.join()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-U", help="Auth cookie from browser", type=str, default="")
    parser.add_argument(
        "-I", help="image file path if you want use image", type=str, default=""
    )
    # type image or video
    parser.add_argument(
        "--type",
        help="Type of generation",
        type=str,
        default="image",
        choices=["image", "video"],
    )
    parser.add_argument(
        "--prompt",
        help="Prompt to generate images for",
        type=str,
        required=True,
    )

    parser.add_argument(
        "--output-dir",
        help="Output directory",
        type=str,
        default="./output",
    )
    parser.add_argument(
        "--high-quality",
        help="Use high quality",
        action="store_true",
    )

    args = parser.parse_args()

    # Create video and image generator
    # follow old style
    if args.type == "image":
        image_generator = ImageGen(
            os.environ.get("KLING_COOKIE") or args.U,
        )
        image_generator.save_images(
            prompt=args.prompt,
            output_dir=args.output_dir,
            image_path=args.I,
        )
    else:
        video_generator = VideoGen(
            os.environ.get("KLING_COOKIE") or args.U,
        )
        video_generator.save_video(
            prompt=args.prompt,
            output_dir=args.output_dir,
            image_path=args.I,
            is_high_quality=args.high_quality,
        )


if __name__ == "__main__":
    main()
