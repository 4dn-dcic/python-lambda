"""
    The below function has dependencies from example_package.py
"""

# This is a craaaazy stupid thing to do, but is necessary because we don't want to
# put this 'package' at the top level. What happens is when AWS packages this
# lambda instead of doing the reasonable thing (creating tests/package) it gives
# a directory the import name (tests.package). This is an illegal import thus the
# need for 'imp' :(
try:
    import imp
    with open('tests.package/example_package.py', 'r') as f:
        example_package = imp.load_module('example_package', f,
                                          'tests.package/example_package.py', (
                                          '.py', 'r', imp.PY_SOURCE)
                                          )
except: # because this code is validated locally as well
    from tests.package import example_package

config = {
    'function_name': 'my_package_test_function',
    'function_module': 'service',
    'function_handler': 'handler',
    'handler': 'service.handler',
    'region': 'us-east-1',
    'runtime': 'python3.6',
    'role': 'helloworld',
    'description': 'Test lambda'
}


def handler(event, context):
    magic = example_package.magic_function()
    return 'I successfully called magic_function: %s' % magic
