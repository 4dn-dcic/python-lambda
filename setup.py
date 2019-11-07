# -*- coding: utf-8 -*-
import sys

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

install_requirements = [
    'boto3>=1.10.7',
    'botocore>=1.13.7',
    'docutils>=0.14'
]

# Only install futures package if using a Python version <= 2.7
if sys.version_info < (3, 0):
    install_requirements.append('futures==3.0.5')

pkg_version = open("aws_lambda/_version.py").readlines()[-1].split()[-1].strip("\"'")

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='python-lambda-4dn',
    version=pkg_version,
    description="FORKED for 4dn-dcic. Use to package and deploy lambda functions.",
    long_description=readme,
    long_description_content_type='text/markdown',
    author="Carl Vitzthum, Soo Lee",
    author_email='carl_vitzthum@hms.harvard.edu',
    url='https://github.com/4dn-dcic/python-lambda',
    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requirements,
    license="ISCL",
    zip_safe=False,
    keywords='python-lambda',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: ISC License (ISCL)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=test_requirements
)
