"""
    The below function has dependencies from example_package.py
"""

# do same gymnastics as with function_with_package
try:
    import imp
    with open('tests.package/example_package.py', 'r') as f:
        example_package = imp.load_module('example_package', f,
                                          'tests.package/example_package.py', (
                                          '.py', 'r', imp.PY_SOURCE)
                                          )
except:
    from tests.package import example_package

config = {
    'function_name': 'my_req_package_test_function',
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
    magic = example_package.magic_function()
    return 'Imported pytest, magic_function: %s' % magic
