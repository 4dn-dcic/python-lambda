"""Version information."""
import pkg_resources

# Information in this file is now superseded by the pyproject.toml file.

# The following line *must* be the last in the module, exactly as formatted:
__version__ = pkg_resources.get_distribution('python-lambda-4dn').version
