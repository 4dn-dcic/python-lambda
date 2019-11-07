# -*- coding: utf-8 -*-
from .aws_lambda import deploy_function
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
