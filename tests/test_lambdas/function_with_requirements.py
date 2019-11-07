"""
    The below function has dependencies specified in requirements.txt
"""

config = {
    'function_name': 'my_requirements_test_function',
    'function_module': 'service',
    'function_handler': 'handler',
    'handler': 'service.handler',
    'region': 'us-east-1',
    'runtime': 'python3.6',
    'role': 'helloworld',
    'description': 'Test lambda'
}


def handler(event, context):
    import pytest
    magic = event['magic']
    return 'I successfully imported pytest! Magic: %s' % magic
