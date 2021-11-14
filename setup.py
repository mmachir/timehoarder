"""Setup Package Module"""

import timehoarder
from pathlib import Path
from setuptools import find_packages, setup

HERE = Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="timehoarder",
    version=timehoarder.__version__,
    description="Identify business days that are overbooked with meetings and 'hoard' time by generating Outlook calendar appointments for focus time.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/mmachir",
    license="MIT",
    author="Martha Bass",
    author_email="mmachirbass@gmail.com",
    py_modules=["timehoarder"],
)
