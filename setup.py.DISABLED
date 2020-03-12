# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages


pkg_version = open("aws_lambda/_version.py").readlines()[-1].split()[-1].strip("\"'")
with open('README.rst') as readme_file:
    readme = readme_file.read()
with open('requirements.txt') as f:
    install_requirements = f.read().splitlines()
with open('dev-requirements.txt') as f:
    test_requirements = f.read().splitlines()


setup(
    name='python-lambda-4dn',
    version=pkg_version,
    description="FORKED for 4dn-dcic. Use to package and deploy lambda functions.",
    long_description=readme,
    long_description_content_type='text/x-rst',
    author="4DN Team at Harvard Medical School",
    author_email='william_ronchetti@hms.harvard.edu',
    url='https://github.com/4dn-dcic/python-lambda',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requirements,
    license="ISCL",
    zip_safe=False,
    keywords='python-lambda',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
