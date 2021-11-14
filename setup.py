"""Setup Package Module"""

from pathlib import Path
from setuptools import find_packages, setup

HERE = Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name="timehoarder",
    version="0.1.0",
    description="Identify business days that are overbooked with meetings and 'hoard' time by generating Outlook calendar appointments for focus time.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/mmachir",
    license="MIT",
    author="Martha Bass",
    author_email="mmachirbass@gmail.com",
    packages=find_packages(where=".", exclude=('demos',))
)
