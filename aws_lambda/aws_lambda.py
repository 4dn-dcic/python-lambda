# -*- coding: utf-8 -*-
from __future__ import print_function
import logging
import os
import tempfile
import zipfile
from shutil import copyfile, copytree
import boto3
import pip
import subprocess
import sys


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


def read_file(path, loader=None, binary_file=False):
    open_mode = 'rb' if binary_file else 'r'
    with open(path, mode=open_mode) as fh:
        if not loader:
            return fh.read()
        return loader(fh.read())


def deploy_function(function_module, function_name_suffix='', package_objects=None,
                    requirements_fpath=None, extra_config=None, local_package=None):
    # check provided function module and packages
    cfg = function_module.config
    function_fpath = function_module.__file__
    try:
        function_name = cfg.get('function_name')
    except KeyError:
        raise KeyError('Must specify "function_name" for deployment of %s'
                        % function_fpath)
    if package_objects is not None and not isinstance(package_objects, list):
        raise TypeError('If provided, "package_objects" must be a list. Found %s'
                        % package_objects)
    if function_name_suffix:
        if not function_name_suffix.startswith('_'):
            function_name_suffix = '_' + function_name_suffix
        function_name += function_name_suffix
        cfg['function_name'] = function_name
    function_module = cfg.get('function_module', 'service')
    function_handler = cfg.get('function_handler', 'handler')
    function_filename = '.'.join([function_module, 'py'])
    if not cfg.get('handler'):
        cfg['handler'] = '.'.join([function_module, function_handler])

    # create a temporary file (zipfile) and temporary dir (items to zip)
    with tempfile.NamedTemporaryFile(suffix='.zip') as tmp_zip:
        with tempfile.TemporaryDirectory() as tmp_dir:
            # copy service file
            copyfile(function_fpath, os.path.join(tmp_dir, function_filename))

            # copy other directly provided python packages
            for package_obj in package_objects:
                package_name = package_obj.__package__
                package_path = package_obj.__path__[0]
                dest_path = os.path.join(tmp_dir, package_name)
                copytree(package_path, dest_path)

            # install packages from requirements file or `pip freeze` output if
            # file not specified. `local_package` can be used to pip install
            # something from local filesystem
            pip_install_to_target(tmp_dir, requirements=requirements_fpath,
                                  local_package=local_package)

            # zip the files in temporary directory
            with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
                for root, _, files in os.walk(tmp_dir):
                    for file in files:
                        # format the filepaths in the archive
                        arcname = os.path.join(root.replace(tmp_dir, ''), file)
                        archive.write(os.path.join(root, file), arcname=arcname)

        # create or update the function
        if function_exists(cfg, function_name):
            update_function(cfg, tmp_zip.name, extra_config)
        else:
            create_function(cfg, tmp_zip.name, extra_config)


def _install_packages(path, packages):
    """
    Install all packages listed to the target directory.

    Ignores any package that includes Python itself and python-lambda as well
    since its only needed for deploying and not running the code

    Args:
        path (str): Path to copy installed pip packages to.
        packages (list): A list of packages to be installed via pip

    Returns:
        None
    """
    def _filter_blacklist(package):
        blacklist = ["-i", "#", "Python==", "python-lambda==", "python-lambda-4dn=="]
        return all(package.startswith(entry) is False for entry in blacklist)
    filtered_packages = filter(_filter_blacklist, packages)
    for package in filtered_packages:
        if package.startswith('-e '):
            package = package.replace('-e ', '')
        log.info('______ INSTALLING: %s' % package)
        pip_major_version = [int(v) for v in pip.__version__.split('.')][0]
        if pip_major_version >= 10:
            # use subprocess because pip internals should not be used above version 10
            subprocess.call([sys.executable, '-m', 'pip', 'install', package, '-t', path, '--ignore-installed', '--no-cache-dir'])
            # from pip._internal import main
            # main(['install', package, '-t', path, '--ignore-installed'])
        else:
            pip.main(['install', package, '-t', path, '--ignore-installed', '--no-cache-dir'])


def pip_install_to_target(path, requirements=False, local_package=None):
    """
    For a given active virtualenv, gather all installed pip packages then
    copy (re-install) them to the path provided.

    Args:
        path (str): Path to copy installed pip packages to.
        requirements (bool):
            If set, only the packages in the requirements.txt
            file are installed.
            The requirements.txt file needs to be in the same directory as the
            project which shall be deployed.
            Defaults to false and installs all pacakges found via pip freeze if
            not set.
        local_package (str):
            The path to a local package with should be included in the deploy as
            well (and/or is not available on PyPi)

    Returns:
        None
    """
    packages = []
    if not requirements:
        log.info('Gathering pip packages')
        pip_major_version = [int(v) for v in pip.__version__.split('.')][0]
        if pip_major_version >= 10:
            from pip._internal import operations
            packages.extend(operations.freeze.freeze())
        else:
            packages.extend(pip.operations.freeze.freeze())
    else:
        if os.path.exists(requirements):
            log.info('Gathering requirement from %s' % requirements)
            data = read_file(requirements)
            packages.extend(data.splitlines())
        elif os.path.exists("requirements.txt"):
            log.info('Gathering requirement packages')
            data = read_file("requirements.txt")
            packages.extend(data.splitlines())

    if not packages:
        log.info('No dependency packages installed!')

    if local_package is not None:
        # TODO: actually sdist is probably bettter here...
        packages.append(local_package)
    _install_packages(path, packages)


def get_role_name(account_id, role):
    """Shortcut to insert the `account_id` and `role` into the iam string."""
    return "arn:aws:iam::{0}:role/{1}".format(account_id, role)


def get_account_id(aws_access_key_id, aws_secret_access_key):
    """Query STS for a users' account_id"""
    client = get_client('sts', aws_access_key_id, aws_secret_access_key)
    return client.get_caller_identity().get('Account')


def get_client(client, aws_access_key_id, aws_secret_access_key, region=None):
    """Shortcut for getting an initialized instance of the boto3 client."""

    return boto3.client(
        client,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region
    )


def create_function(cfg, path_to_zip_file, extra_config=None):
    """Register and upload a function to AWS Lambda."""

    byte_stream = read_file(path_to_zip_file, binary_file=True)
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    account_id = get_account_id(aws_access_key_id, aws_secret_access_key)
    role = get_role_name(account_id, cfg.get('role', 'lambda_basic_execution'))

    client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        cfg.get('region'))

    func_name = (
        os.environ.get('LAMBDA_FUNCTION_NAME') or cfg.get('function_name')
    )

    lambda_create_config = {
        'FunctionName': func_name,
        'Runtime': cfg.get('runtime', 'python3.6'),
        'Role': role,
        'Handler': cfg.get('handler'),
        'Code': {'ZipFile': byte_stream},
        'Description': cfg.get('description'),
        'Timeout': cfg.get('timeout', 15),
        'MemorySize': cfg.get('memory_size', 512),
        'Environment': {
            'Variables': {
                key.strip('LAMBDA_'): value
                for key, value in os.environ.items()
                if key.startswith('LAMBDA_')
            }
        },
        'Publish': True
    }
    if extra_config and isinstance(extra_config, dict):
        lambda_create_config.update(extra_config)

    log.info('Creating lambda function with name: {}'.format(func_name))
    client.create_function(**lambda_create_config)


def update_function(cfg, path_to_zip_file, extra_config=None):
    """Updates the code of an existing Lambda function"""

    byte_stream = read_file(path_to_zip_file, binary_file=True)
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')

    account_id = get_account_id(aws_access_key_id, aws_secret_access_key)
    role = get_role_name(account_id, cfg.get('role', 'lambda_basic_execution'))

    client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        cfg.get('region'))

    log.info('Updating lambda function with name: {}'.format(cfg.get('function_name')))
    client.update_function_code(
        FunctionName=cfg.get('function_name'),
        ZipFile=byte_stream,
        Publish=True
    )

    lambda_update_config = {
        'FunctionName': cfg.get('function_name'),
        'Role': role,
        'Handler': cfg.get('handler'),
        'Description': cfg.get('description'),
        'Timeout': cfg.get('timeout', 15),
        'MemorySize': cfg.get('memory_size', 512),
        'Runtime': cfg.get('runtime', 'python3.6'),
        'VpcConfig': {
            'SubnetIds': cfg.get('subnet_ids', []),
            'SecurityGroupIds': cfg.get('security_group_ids', [])
        }
    }
    if extra_config and isinstance(extra_config, dict):
        lambda_update_config.update(extra_config)

    client.update_function_configuration(**lambda_update_config)


def function_exists(cfg, function_name):
    """Check whether a function exists or not"""

    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')
    client = get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        cfg.get('region'))
    try:
        client.get_function(FunctionName=function_name)
    except:
        return False
    return True
