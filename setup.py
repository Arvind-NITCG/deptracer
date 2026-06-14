from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="deptracer", 
    version="0.1.1",
    author="Arvind K N",
    author_email="sooryarvind@gmail.com", 
    description="OS-Level Dependency Resolver & Auto-Patcher for PyInstaller",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Arvind-NITCG/deptracer", 
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyInstaller>=5.0" 
    ],
    entry_points={
        "console_scripts": [
            "deptracer=deptracer.cli:main",
        ],
    },
)