import argparse
import os
import time
import contextlib
from typing import Optional
from enum import Enum
from http.cookies import SimpleCookie

from fake_useragent import UserAgent
import requests
from requests.utils import cookiejar_from_dict
from rich import print
import threading

browser_version = "edge101"
ua = UserAgent(browsers=["edge"])
base_url = "https://klingai.kuaishou.com/"
base_url_not_cn = "https://klingai.com/"


def call_for_daily_check(session: requests.Session, is_cn: bool) -> bool:
    if is_cn:
        r = session.get(f"{base_url}api/pay/reward?activity=login_bonus_daily")
    else:
        r = session.get(f"{base_url_not_cn}api/pay/reward?activity=login_bonus_daily")
    if r.ok:
        print(f"Call daily login success with {is_cn}:\n{r.json()}\n")
        return True

    raise Exception(
        "Call daily login failed with CN or Non-CN. The token may be incorrect."
    )


class TaskStatus(Enum):
    PENDING = 0
    COMPLETED = 1
    FAILED = 3


class BaseGen:
    def __init__(self, cookie: str) -> None:
        self.session: requests.Session = requests.Session()
        self.cookie = cookie
        self.session.cookies, is_cn = self.parse_cookie_string(self.cookie)
        self.session.headers["user-agent"] = ua.random
        # check the daily login
        call_for_daily_check(self.session, is_cn)
        if is_cn:
            self.base_url = base_url
            image_upload_base_url = "https://upload.kuaishouzt.com/"
        else:
            self.base_url = base_url_not_cn
            image_upload_base_url = "https://upload.uvfuns.com/"

        self.apis_dict = {
            "image_upload_gettoken": f"{self.base_url}api/upload/issue/token?filename=",
            "image_upload_resume": f"{image_upload_base_url}api/upload/resume?upload_token=",
            "image_upload_fragment": f"{image_upload_base_url}api/upload/fragment",
            "image_upload_complete": f"{image_upload_base_url}api/upload/complete",
            "image_upload_geturl": f"{self.base_url}api/upload/verify/token?token=",
        }

        self.submit_url = f"{self.base_url}api/task/submit"
        self.daily_url = f"{self.base_url}api/pay/reward?activity=login_bonus_daily"
        self.point_url = f"{self.base_url}api/account/point"
        # store the video id list maybe for future use or extend
        self.video_id_list = []

    @staticmethod
    def parse_cookie_string(cookie_string):
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        cookies_dict = {}
        cookiejar = None
        is_cn = False
        for key, morsel in cookie.items():
            if key.startswith("kuaishou"):
                is_cn = True
            cookies_dict[key] = morsel.value
            cookiejar = cookiejar_from_dict(
                cookies_dict, cookiejar=None, overwrite=True
            )
        return cookiejar, is_cn

    def get_account_point(self) -> float:
        bonus_req = self.session.get(self.daily_url)
        bonus_data = bonus_req.json()
        assert bonus_data.get("status") == 200

        point_req = self.session.get(self.point_url)
        point_data = point_req.json()
        assert point_data.get("status") == 200

        total_point = point_data["data"]["total"]
        return total_point / 100

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

    def fetch_metadata(self, task_id: str) -> tuple[dict, TaskStatus]:
        url = f"{self.base_url}api/task/status?taskId={task_id}"
        response = self.session.get(url)
        data = response.json().get("data")
        assert data is not None
        # this is very interesting it use resolution to check if the image is ready
        if data.get("status") >= 90:
            return data, TaskStatus.COMPLETED
        elif data.get("status") in [9, 50]:
            return data, TaskStatus.FAILED
        else:
            return data, TaskStatus.PENDING


class VideoGen(BaseGen):

    def extend_video(self, video_id: int, prompt: str = "") -> str:
        # get the video url and init_prompt
        data, status = self.fetch_metadata(video_id)
        assert status == TaskStatus.COMPLETED
        works = data.get("works", [])
        if not works:
            print("No Video found.")
            raise Exception("No Video found.")
        else:
            video_type, resource, prompt_init = None, None, None
            work = works[0]
            work_id = work.get("workId")
            resource = work.get("resource", {}).get("resource")
            arguments = work.get("taskInfo", {}).get("arguments", [])
            video_type = work.get("taskInfo", {}).get("type")

            for arg in arguments:
                if arg.get("name") == "prompt":
                    prompt_init = arg.get("value")
                    break
            if not resource:
                print("No Video found.")
                raise Exception("No Video found.")

        payload = {
            "type": "m2v_extend_video",
            "inputs": [
                {
                    "name": "input",
                    "inputType": "URL",
                    "url": resource,
                    "fromWorkId": work_id,
                },
            ],
            "arguments": [
                {
                    "name": "prompt",
                    "value": "",
                },
                {
                    "name": "biz",
                    "value": "klingai",
                },
                {
                    "name": "__initialType",
                    "value": video_type,
                },
                {
                    "name": "__initialPrompt",
                    "value": prompt_init,
                },
            ],
        }
        return self._get_video_with_payload(payload)

    def _get_video_with_payload(self, payload: dict) -> list:
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
        # store the video id list
        self.video_id_list.append(request_id)
        start_wait = time.time()
        print("Waiting for results... will take 2mins to 5mins")
        while True:
            if int(time.time() - start_wait) > 1200:
                raise Exception("Request timeout")
            image_data, status = self.fetch_metadata(request_id)
            if status == TaskStatus.PENDING:
                print(".", end="", flush=True)
                # spider rule
                time.sleep(5)
            elif status == TaskStatus.FAILED:
                print("Request failed")
                return []
            else:
                result = []
                works = image_data.get("works", [])
                if not works:
                    print("No video found.")
                    return []
                else:
                    for work in works:
                        resource = work.get("resource", {}).get("resource")
                        if resource:
                            # sleep for 2s for waiting the video to be ready in kuaishou server
                            time.sleep(2)
                            result.append(resource)
                return result

    def get_video(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        is_high_quality: bool = False,
        auto_extend: bool = False,
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
        if auto_extend:
            print("will generate and extending video...")
            self._get_video_with_payload(payload)
            print("Auto extending video...")
            video_id = self.video_id_list.pop()
            return self.extend_video(video_id)
        else:
            return self._get_video_with_payload(payload)

    def save_video(
        self,
        prompt: str,
        output_dir: str,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
        is_high_quality: bool = False,
        auto_extend: bool = False,
    ) -> None:
        mp4_index = 0
        try:
            links = self.get_video(
                prompt,
                image_path=image_path,
                image_url=image_url,
                is_high_quality=is_high_quality,
                auto_extend=auto_extend,
            )
        except Exception as e:
            print(e)
            raise
        with contextlib.suppress(FileExistsError):
            os.mkdir(output_dir)
        print()
        if not links:
            print("No video found.")
            return
        link = links[0]
        while os.path.exists(os.path.join(output_dir, f"{mp4_index}.mp4")):
            mp4_index += 1
        response = self.session.get(link)
        if response.status_code != 200:
            raise Exception("Could not download image")
        # save response to file
        with open(os.path.join(output_dir, f"{mp4_index}.mp4"), "wb") as output_file:
            output_file.write(response.content)
        mp4_index += 1


class ImageGen(BaseGen):
    def get_images(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
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
        request_id = (response_body.get("data", {}).get("task") or {}).get("id")
        if not request_id:
            raise Exception("Could not get request ID")
        start_wait = time.time()
        print("Waiting for results...")
        while True:
            if int(time.time() - start_wait) > 1200:
                raise Exception("Request timeout")
            image_data, status = self.fetch_metadata(request_id)
            if status == TaskStatus.PENDING:
                print(".", end="", flush=True)
                # spider rule
                time.sleep(2)
            elif status == TaskStatus.FAILED:
                print("Request failed")
                return []
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
                            # sleep for 2s for waiting the video to be ready in kuaishou server
                            time.sleep(2)
                            result.append(resource)
                return result

    def save_images(
        self,
        prompt: str,
        output_dir: str,
        image_path: Optional[str] = None,
        image_url: Optional[str] = None,
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
    parser.add_argument(
        "--auto-extend",
        help="Auto extend video",
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
        print(
            f"The balance of points in your account is: {image_generator.get_account_point()}"
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
            auto_extend=args.auto_extend,
        )
        print(
            f"The balance of points in your account is: {video_generator.get_account_point()}"
        )


if __name__ == "__main__":
    main()
