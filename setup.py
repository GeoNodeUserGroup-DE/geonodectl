#!/usr/bin/env python

from setuptools import setup

setup(
    name="geonodectl",
    version="0.1",
    description="",
    url="https://github.com/GeoNodeUserGroup-DE/geonodectl",
    author="marcel wallschlaeger",
    author_email="marcel.wallschlaeger@zalf.de",
    zip_safe=False,
    packages=["src"],
    scripts=["geonodectl"],
    install_requires=[
        "requests",
        "tabulate",
    ],
)
