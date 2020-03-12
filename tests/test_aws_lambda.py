from conftest import *
from tests.test_lambdas import (
    example_function,
    example_function_update,
    function_with_requirements,
    function_with_package,
    function_with_req_pack
)
from tests import package


@pytest.fixture
def aws_keys():
    import os
    key_id = os.environ.get('AWS_ACCESS_KEY_ID', None)
    secret = os.environ.get('AWS_SECRET_ACCESS_KEY', None)
    assert key_id is not None # we want to bail in setup if keys are not present
    assert secret is not None
    return key_id, secret


@pytest.fixture
def cfg(aws_keys):
    key_id, secret = aws_keys
    conf = {}
    conf['aws_access_key_id'] = key_id
    conf['aws_secret_access_key'] = secret
    conf['region'] = 'us-east-1'
    return conf


class TestPythonLambdaUnit():
    """ Class containing unit (non-integration) tests for Python-Lambda """

    pytestmark = [pytest.mark.unit]

    def test_get_version(self):
        """ Because coverage, thats why! """
        from aws_lambda._version import __version__
        assert len(__version__.split('.')) == 3 # should be x.x.x

    def test_get_role_name(self):
        """ Basic test that validates our role_name format """
        _id, role = 'abcdefg', 'ADMIN'
        role_name = get_role_name(_id, role)
        assert 'arn:aws:iam' in role_name
        assert _id in role_name
        assert role in role_name

    def test_get_account_id(self, aws_keys):
        """ Tests we can get a user account_id, must have aws keys in env """
        key_id, secret = aws_keys
        get_account_id(key_id, secret) # will throw exception if not found

    @pytest.mark.parametrize('client', ['s3', 'lambda'])
    def test_get_client(self, aws_keys, client):
        """
        Tests that we're able to get a handle to a boto3 client using the AWS
        credentials we located in env
        """
        key_id, secret = aws_keys
        cli = get_client(client, key_id, secret, region='use-east-1')
        assert cli._request_signer._credentials.access_key == key_id
        assert cli._request_signer._credentials.secret_key == secret


class TestPythonLambdaIntegration():
    """ Class containing integration tests for Python-Lambda """

    pytestmark = [pytest.mark.integration]

    def test_deploy_lambda(self, cfg):
        """
        Deploys a lambda function, tests that we can see/use it
        Updates that same function with different config, invokes to verify the
        update went through
        """
        suff = 'integration_test'
        full_name = example_function.config['function_name'] + '_' + suff
        cfg['function_name'] = full_name
        deploy_function(example_function, function_name_suffix=suff)
        assert function_exists(cfg)
        resp = invoke_function(cfg, invocation_type='RequestResponse')
        assert resp == '"Hello! My input event is {}"'
        deploy_function(example_function_update, function_name_suffix=suff)
        resp = invoke_function(cfg, invocation_type='RequestResponse')
        assert resp == '"Hello! I have been updated! My input event is {}"'
        assert delete_function(cfg)
        assert not delete_function(cfg)

    def test_deploy_lambda_with_requirements(self, cfg):
        """
        Deploys and invokes a lambda that has requirements, this time with no suffix
        Also passes an argument that is checked
        """
        import json
        full_name = function_with_requirements.config['function_name']
        cfg['function_name'] = full_name
        req_fpath = './tests/test_lambdas/requirements.txt'
        deploy_function(function_with_requirements, requirements_fpath=req_fpath)
        assert function_exists(cfg)
        resp = invoke_function(cfg, invocation_type='RequestResponse', event={'magic': 17})
        assert resp == '"I successfully imported pytest! Magic: 17"'
        assert delete_function(cfg)

    def test_deploy_lambda_with_package(self, cfg):
        """
        Deploys and invokes a lambda that has package based dependencies
        """
        full_name = function_with_package.config['function_name']
        cfg['function_name'] = full_name
        deploy_function(function_with_package, package_objects=[package])
        assert function_exists(cfg)
        resp = invoke_function(cfg, invocation_type='RequestResponse')
        assert resp == '"I successfully called magic_function: 21"'
        assert delete_function(cfg)

    def test_deploy_lambda_with_package_and_requirements(self, cfg):
        """
        Deploys and invokes a lambda that uses both an independently packaged
        dependency and one given from requirements.
        """
        full_name = function_with_req_pack.config['function_name']
        cfg['function_name'] = full_name
        req_fpath = './tests/test_lambdas/requirements.txt'
        deploy_function(function_with_req_pack, requirements_fpath=req_fpath,
                        package_objects=[package])
        assert function_exists(cfg)
        resp = invoke_function(cfg, invocation_type='RequestResponse')
        assert resp == '"Imported pytest, magic_function: 21"'
        assert delete_function(cfg)

    def test_invoke_invalid_lambda(self, cfg):
        """
        Tries to execute an invalid lambda. Should fail
        """
        full_name = 'not_a_lambda_name'
        cfg['function_name'] = full_name
        resp = invoke_function(cfg, invocation_type='RequestResponse')
        assert resp is None
