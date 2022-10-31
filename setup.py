import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()
import simpleprotocol

setuptools.setup(
    name='simple-protocol',
    version=simpleprotocol.__version__,
    scripts=[],
    entry_points={
        'console_scripts': ["pup = simpleprotocol.v2.cli:main"]
    },
    author="Gage LeBlanc",
    author_email="gleblanc@symnet.io",
    description="Common library for spectre libs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://github.com/gageleblanc/simpleprotocol",
    install_requires=['clilib>=3.7.3'],
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
)
