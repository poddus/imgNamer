# imgNamer
imgNamer is a script for batch-renaming images using timestamp data from metadata and file names 
in order to have them all in chronological order.

It uses the format `YYYY-MM-DD hh-mm-ss Description`.

The [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format is not particularly human readable without delimiters and 
the standard time delimiter `:` is not allowed in file names. This format is a compromise. 

imgNamer accepts a folder as input and is invoked using the syntax

```shell
python [path to script] [path to folder containing images]
```

Alternatively the script can be made executable (`chmod u+x`) and installed in your path 
(for example `/usr/local/bin`), in which case it may be invoked in the current directory using

```shell
imgNamer.py ./
```

External dependencies are the Python module [ExifRead](https://pypi.python.org/pypi/ExifRead) and [ffmpeg](https://www.ffmpeg.org/).
