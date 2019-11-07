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


def read_file(path, loader=None, binary_file=False):
    open_mode = 'rb' if binary_file else 'r'
    with open(path, mode=open_mode) as fh:
        if not loader:
            return fh.read()
        return loader(fh.read())


def deploy_function(function_module, function_name_suffix='', package_objects=None,
                    requirements_fpath=None, extra_config=None, local_package=None):
    """
    Creates or updates a lambda function given a `function_module` that is a
    python module containing a dictionary config and correct handler function.
    The name of the handler function must match the `function_handler` value
    in the config.

    Overall, this function creates a temporary directory and installs the lambda
    service function, as well as supplied python modules and pip packages. This
    directory is compressed as a temporary zip file and used to create/update
    the lambda function.

    Args:
        function_module (types.ModuleType):
            Python module containing the `config` dictionary and handler
            function necessary to deploy the lambda function. See an examples
            in aws_lambda.examples.
        function_name_suffix (str):
            If provided, will append the given string (with prepended "_" if
            not present) to the deployed lambda function name.
        package_objects (list):
            Optional list of Python packages (types.ModuleType) that will be
            explicitly added to the zipfile for lambda code. Use this argument
            as an alternative to pip installing packages.
        requirements_fpath (str): path to requirements.txt file to pip install.
        extra_config (dict):
            additional kwargs that will be passed to boto3 create_function
            or update_function_configuration for lambda client. Optionally use
            to override `Environment` or any other arguments.
        local_package (str): optional path to a Python repo to pip install.

    Returns:
        None
    """
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
    if not package_objects:
        package_objects = [] # don't crash trying to iterate on None below

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
        if function_exists(cfg):
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


def pip_install_to_target(path, requirements=None, local_package=None):
    """
    For a given active virtualenv, gather all installed pip packages then
    copy (re-install) them to the path provided.

    Args:
        path (str): Path to copy installed pip packages to.
        requirements (str):
            If set, only the packages in the requirements.txt
            file are installed.
            The requirements.txt file needs to be in the same directory as the
            project which shall be deployed.
            Defaults to false and installs all pacakges found via pip freeze if
            not set.
        local_package (str):
            The path to a local package with should be included in the deploy as
            well

    Returns:
        None
    """
    packages = []
    if requirements:
        if os.path.exists(requirements):
            log.info('Gathering requirement from %s' % requirements)
            data = read_file(requirements)
            packages.extend(data.splitlines())
        else:
            log.error('Could not load requirements from: %s (does it exist?)'
                      % requirements)

    if local_package is not None:
        packages.append(local_package)
    if packages:
        _install_packages(path, packages)
    else:
        log.info('No dependency packages installed!')


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
    account_id = get_account_id(cfg.get('aws_access_key_id'), cfg.get('aws_secret_access_key'))
    role = get_role_name(account_id, cfg.get('role', 'lambda_basic_execution'))
    client = _client_from_cfg(cfg)

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
    account_id = get_account_id(cfg.get('aws_access_key_id'), cfg.get('aws_secret_access_key'))
    role = get_role_name(account_id, cfg.get('role', 'lambda_basic_execution'))
    client = _client_from_cfg(cfg)

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


def _client_from_cfg(cfg):
    """
    Helper method for several other methods that sets up a lambda client given
    a config dictionary containing the relevant AWS keys. If the keys aren't found
    and there are keys in the environment boto3 will locate them and proceed.
    """
    aws_access_key_id = cfg.get('aws_access_key_id')
    aws_secret_access_key = cfg.get('aws_secret_access_key')
    region = cfg.get('region', 'us-east-1')
    if not aws_secret_access_key or not aws_access_key_id:
        log.warning('AWS Credentials not found in cfg! Falling back to env...')
    return get_client('lambda', aws_access_key_id, aws_secret_access_key,
                        region)


def function_exists(cfg):
    """
    Check whether the given function in cfg exists or not
    """
    client = _client_from_cfg(cfg)
    try:
        client.get_function(FunctionName=cfg.get('function_name'))
    except:
        return False
    return True


def delete_function(cfg):
    """
    Deletes the given function name found in cfg.
    Returns True in success, False otherwise
    """
    client = _client_from_cfg(cfg)
    try:
        client.get_function(FunctionName=cfg.get('function_name'))
        client.delete_function(FunctionName=cfg.get('function_name'))
    except:
        return False
    return True

def invoke_function(cfg, invocation_type='Event', event={}):
    """
    Invokes the given lambda function using the given config cfg.

    invocation_type is one of 'Event'|'RequestResponse'|'DryRun'. The default
    is Event, which will cause this function to execute asynchronously.
    'RequestResponse' triggers the lambda serially. 'DryRun' just
    validates parameters/permissions. Note that if you use 'Event' you will likely
    get no response from this function.

    event is a dictionary containing the arguments needed for this lambda. For
    example if your lambda is expecting fields 'a' and 'b' in the 'event' that is
    passed to it from AWS, you would pass in:

        event = {'a': 5, 'b': 13}

    to this function. This information is serialized into JSON and passed to Boto3

    Returns decoded response in success, None otherwise
    """
    import json
    client = _client_from_cfg(cfg)
    try:
        resp = client.invoke(FunctionName=cfg.get('function_name'),
                             InvocationType=invocation_type,
                             Payload=json.dumps(event))
    except:
        log.error('Failed to execute lambda fxn: %s with arguments: \n %s \n %s'
                    % (cfg.get('function_name'), invocation_type, event))
        return None
    return resp['Payload'].read().decode('utf-8')
