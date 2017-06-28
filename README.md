# imgNamer
a set of scripts for batch-renaming images using EXIF Data and other sources

The aim of these scripts is to rename images to the format

`YYYY-MM-DD hh.mm.ss Description`

in order to facilitate sharing pictures with friends and having them all in chronological order!

All scripts in this suite accept folders as input. They are invoked using the syntax

`python [path to script] [path to folder containing images]`

They contain practically no exception handling.

Dependency of datetime_files_EXIF.py is the Python module [ExifRead](https://pypi.python.org/pypi/ExifRead)
