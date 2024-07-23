from setuptools import find_packages, setup

setup(
    name="kling-creator",
    version="0.1.1",
    author="yihong0618",
    author_email="zouzou0208@gmail.com",
    description="High quality video generation by https://klingai.kuaishou.com/. Reverse engineered API.",
    url="https://github.com/yihong0618/klingCreator",
    install_requires=[
        "requests",
        "fake-useragent",
    ],
    packages=find_packages(),
    entry_points={
        "console_scripts": ["kling = kling.kling:main"],
    },
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
