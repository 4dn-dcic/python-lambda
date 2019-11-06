"""
Example lambda configuation file, including `config` dictionary and
an example handler function.

Would deploy with:
```
from aws_lambda import deploy_function
from aws_lambda.examples import example_function
deploy_function(example_function,
                function_name_suffix=<optional str suffix>,
                package_objects=<optional list of Python modules>,
                requirements_fpath=<optional path to requirements file>,
                extra_config=<optional dict for extra boto3 lambda kwargs>)
```
"""


config = {
    'function_name': 'my_test_function',
    'function_module': 'service',
    'function_handler': 'handler',
    'handler': 'service.handler',
    'region': 'us-east-1',
    'runtime': 'python3.6',
    'role': 'helloworld',
    'description': 'Test lambda'
}


def handler(event, context):
    return 'Hello! My input event is %s' % event
