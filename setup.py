from distutils.core import setup
import sys
sys.path.insert(1, "lib")
from maxicom.strings import *

files = ["glade/*"]

setup(name = PACKAGE,
    version = VERSION,
    description = DESCRIPTION,
    author = AUTHOR,
    author_email = AUTHOR_EMAIL,
    url = URL,
    license = LICENSE,
    package_dir = {'': 'lib'},
    packages = ['maxicom'],
    package_data = {'maxicom' : files },
    scripts = ["maxicom"],
) 
