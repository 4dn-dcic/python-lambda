=================
python-lambda-4dn
=================

(python-λ forked for 4DN-DCIC projects)
---------------------------------------


.. image:: https://img.shields.io/pypi/v/python-lambda-4dn.svg
  :alt: Pypi
  :target: https://pypi.python.org/pypi/python-lambda-4dn/

.. image:: https://travis-ci.org/4dn-dcic/python-lambda.svg?branch=master
  :alt: Build Status
  :target: https://travis-ci.org/4dn-dcic/python-lambda

.. image:: https://coveralls.io/repos/github/4dn-dcic/python-lambda/badge.svg?branch=master
  :alt: Coverage
  :target: https://coveralls.io/github/4dn-dcic/python-lambda?branch=master

This is a toolset for developing and deploying *serverless* Python code in AWS Lambda.

Important
=========
This is a FORK of Nick Ficano's `Python-lambda <https://pypi.python.org/pypi/python-lambda>`_
package. It will NOT be updated regularly and is frozen for the needs of projects at the
`4D Nucleome Data Coordination and Integration Center (4DN-DCIC)
<https://github.com/4dn-dcic>`_.

Description
===========

AWS Lambda is a service that allows you to write Python, Java, or Node.js code that
gets executed in response to events like http requests or files uploaded to S3.

Working with Lambda is relatively easy, but the process of bundling and deploying your code
is not as simple as it could be.

The *Python-Lambda* library takes away the guess work of developing your Python-Lambda
services by providing you a toolset to streamline the annoying parts.

Requirements
============

* Python 3.6
* Pip (Any should work)
* Virtualenv (>=15.0.0)
* Virtualenvwrapper (>=4.7.1) [optional]

Setting Up a Virtual Environment
================================

Make sure you're working in a virtual environment. Here are three ways to do that:

* If you have virtualenvwrapper that knows to use Python 3.6::

    mkvirtualenv myenv

* If you have virtualenv but not virtualenvwrapper, and you have python3.6 in your ``PATH``::

    virtualenv myenv -p python3.6

* If you are using ``pyenv`` to control what environment you use::

    pyenv exec python -m venv myenv

Once you have created a virtual environment, install requirements::

    pip install -r requirements.txt dev-requirements.txt

Install additional support for development::

    python setup.py install

Getting Started
===============

Using this library is intended to be as straightforward as possible.
Code for a very simple lambda used in the tests is reproduced below.

.. code:: python

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

This code illustrates the two things required to create a lambda. The first is ``config``,
which specifies metadata for AWS. One important thing to note in here is the ``role`` field.
This must be a IAM role with Lambda permissions - the one in this example is ours.
The second is the ``handler`` function. This is the actual code that is executed.

Given this code in ``example_function.py`` you would deploy this function like so:

.. code:: python

  from aws_lambda import deploy_function
  import example_function
  deploy_function(example_function,
                  function_name_suffix='<suffix>',
                  package_objects=['list', 'of', 'local', 'modules'],
                  requirements_fpath='path/to/requirements',
                  extra_config={'optional_arguments_for': 'boto3'})

And that's it! You've deployed a simple lambda function. You can navigate to the AWS
console to create a test event to trigger it or you can invoke it directly using Boto3.

Advanced Usage
==============

Many of the options specified in the above code block when it came to actually
deploying the function are not used. These become more useful as you want to make more
complicated lambda functions. The ideal way to incorporate dependencies into lambda functions
is by providing a ``requirements.txt`` file. We rely on ``pip`` to install these packages
and have found it to be very reliable. While it is also possible to specify local modules
as well through ``package_objects``, doing so is not recommended because those modules
must be specified at the top level of the repository in order to work out of the box.
There is a comment on this topic in ``example_function_package.py``
with code on how to handle it.

Tests
========

Tests can be found in the ``test_aws_lambda.py``. Using the tests as a guide to develop
your lambdas is probably a good idea. You can also see how to invoke the lambdas directly
from Python (and interpret the response).  You can invoke all of this by just doing::

    pytest

The usual ``pytest`` arguments are permited. For example, to invoke an individual test,
mention its name. To see verbose output, use ``-v``; or use ``-vv`` for extra-verbose output,
as in::

    pytest -vv -k test_deploy_lambda_with_package_and_requirements
