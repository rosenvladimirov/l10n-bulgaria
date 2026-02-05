from . import models
from . import report
from . import patches


def post_load():
    patches.post_load()
