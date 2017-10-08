# python 3

import subprocess, glob, re, os, sys
from argparse import ArgumentParser

parser = ArgumentParser(description='rename images to the format YYYY-MM-DD hh.mm.ss Description. Uses on exifread module')
parser.add_argument("folder", help="folder to parse")
args = parser.parse_args()

directory = args.folder
os.chdir(directory)

description = input("Enter a description of the pictures. otherwise, press Return ")

for file in glob.glob('*'):
	filename, file_extension = os.path.splitext(file)

	tags = subprocess.run(
	['ffprobe',
	'-show_entries', 'format_tags',
	'-v', '-8',
	'-of', 'flat',
	os.path.abspath(file)],
	check=True, stdout=subprocess.PIPE, encoding="utf-8"
	).stdout
	
	date = re.search('date="(.*)"', tags).group(1)
	time = re.search('ICRT="(.*)"', tags).group(1)

	date = date + ' ' + time

	# replace special characters
	cleanDate = re.sub(':', '.', str(date))
	
	# if the description is blank, we don't want the leading space
	if(description == ""):
		if os.path.isfile(cleanDate + file_extension):
			print("file exists! skipping...")
		else:
			os.rename(file, cleanDate + file_extension)
	else:
		if os.path.isfile(cleanDate + " " + description + file_extension):
			print("file exists! skipping...")
		else:
			os.rename(file, cleanDate + " " + description + file_extension)