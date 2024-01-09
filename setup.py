import setuptools

VERSION = "0.0.1"

setuptools.setup(
    name="KCBot",
    version=VERSION,
    author="ZanNen",
    author_email="",
    description="A simple KuCoin trading bot",
    long_description="",
    long_description_content_type="text/markdown",
    url="https://github.com/zannen/kcbot",
    packages=setuptools.find_packages(),
    package_data={"kcbot": ["py.typed"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[],
    setup_requires=["wheel"],
    zip_safe=False,
)
