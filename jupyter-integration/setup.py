from setuptools import setup, find_packages


def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()


setup(
    name="cadence-edu",
    version="0.1.0",
    author="Liv Vage",
    author_email="contact@cadence-dash.com",
    description="Cadence — live student progress dashboards for Jupyter teaching",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://cadence-dash.com",
    project_urls={
        "Homepage": "https://cadence-dash.com",
        "Source": "https://github.com/livvage/cadence",
        "Bug Tracker": "https://github.com/livvage/cadence/issues",
        "Documentation": "https://cadence-dash.com/guide",
    },
    license="MIT",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Education",
        "Framework :: Jupyter",
    ],
    python_requires=">=3.10",
    install_requires=[
        "jupyter>=1.0.0",
        "notebook>=6.0.0",
        "ipywidgets>=7.0.0",
        "requests>=2.25.0",
        "nbformat>=5.0.0",
        "pyyaml>=5.0.0",
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-cov>=2.0.0",
            "black>=21.0.0",
            "flake8>=3.8.0",
            "mypy>=0.800",
        ],
    },
    entry_points={
        "console_scripts": [
            "cadence-cli=cadence.cli:main",
        ],
    },
    zip_safe=False,
    keywords="jupyter, education, classroom, dashboard, checkpoints",
)
