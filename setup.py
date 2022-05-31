from distutils.core import setup
from setuptools import find_packages


setup(
    name="multipage_form",
    description="Django app for creating multipage modelforms",
    author="Noel Taylor", 
    author_email="ntaylor@imagescape.com",
    keywords=[],
    version="1.0.0",
    url="https://github.com/ImaginaryLandscape/django-multipage-form",
    packages=find_packages(),
    install_requires=[
        "django >= 3.2",
    ],
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Framework :: Django :: 3.2",
    ]  
)
