import time
from conftest import *
from tests.test_lambdas import (
    example_function,
    example_function_update
)


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
    return conf


@pytest.fixture
def lambda_client(aws_keys):
    key_id, secret = aws_keys
    return get_client('lambda', key_id, secret)


class TestPythonLambdaUnit():
    """ Class containing unit (non-integration) tests for Python-Lambda """

    pytestmark = [pytest.mark.unit]

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
        cli = get_client(client, key_id, secret)
        assert cli._request_signer._credentials.access_key == key_id
        assert cli._request_signer._credentials.secret_key == secret


class TestPythonLambdaIntegration():
    """ Class containing integration tests for Python-Lambda """

    pytestmark = [pytest.mark.integration]

    def test_deploy_lambda(self, cfg, lambda_client):
        """
        Deploys a lambda function, tests that we can see/use it
        Updates that same function with different config, invokes to verify the
        update went through
        """
        full_name = 'my_test_function_integration_test'
        suff = 'integration_test'
        deploy_function(example_function, function_name_suffix=suff)
        assert function_exists(cfg, full_name)
        resp = lambda_client.invoke(FunctionName=full_name, InvocationType='RequestResponse')
        assert resp['Payload'].read().decode('utf-8') == '"Hello! My input event is {}"'
        deploy_function(example_function_update, function_name_suffix=suff)
        resp = lambda_client.invoke(FunctionName=full_name, InvocationType='RequestResponse')
        assert resp['Payload'].read().decode('utf-8') == '"Hello! I have been updated! My input event is {}"'
        assert delete_function(cfg, full_name)

    def test_deploy_lambda_with_requirements(self, cfg, lambda_client):
        """
        Deploys and invokes a lambda that has requirements
        """
        pass
