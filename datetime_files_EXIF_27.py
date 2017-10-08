# python 2.7

import glob, re, os, sys, datetime, exifread
from argparse import ArgumentParser

parser = ArgumentParser(description='rename images to the format YYYY-MM-DD hh.mm.ss Description. Uses on exifread module')
parser.add_argument("folder", help="folder to parse")
args = parser.parse_args()

directory = args.folder
os.chdir(directory)

description = raw_input("Enter a description of the pictures. otherwise, press Return ")

for file in glob.glob('*'):
	filename, file_extension = os.path.splitext(file)
	
	# read image (binary mode), get EXIF info
	binImage = open(file, 'rb')
	tags = exifread.process_file(binImage)
	
	date = tags['EXIF DateTimeOriginal']
	
	# replace special characters
	cleanDate = re.sub(':', '', str(date))
	cleanDate = re.sub('(^\d{4})(\d{2})(\d{2})(\s)(\d{2})(\d{2})(\d{2})', r'\1-\2-\3 \5.\6.\7', cleanDate)
	
	# if the description is blank, we don't want the leading space
	if(description == ""):
		if os.path.isfile(cleanDate + file_extension):
			print "file exists! skipping..."
		else:
			os.rename(file, cleanDate + file_extension)
	else:
		if os.path.isfile(cleanDate + " " + description + file_extension):
			print "file exists! skipping..."
		else:
			os.rename(file, cleanDate + " " + description + file_extension)