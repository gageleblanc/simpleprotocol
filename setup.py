import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()
import simpleprotocol

setuptools.setup(
    name='simple-protocol',
    version=simpleprotocol.__version__,
    scripts=[],
    author="Gage LeBlanc",
    author_email="gleblanc@symnet.io",
    description="Common library for spectre libs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/gageleblanc/simpleprotocol",
    install_requires=['clilib>=2.1.0'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)
