import glob
import re
import os
import sys
import datetime
import exifread
import subprocess
from argparse import ArgumentParser

parser = ArgumentParser(description='rename images to the format YYYY-MM-DD hh.mm.ss Description.')
parser.add_argument('folder', help='folder to parse')
args = parser.parse_args()

directory = args.folder
os.chdir(directory)

def alt():
	# perhaps its useful to simply increment the last value
	print('ERROR: ' + file + ' does not contain timestamp!')
	while True:
		answer = input('do you want to increment the last timestamp?\n' + str(lastStamp))
		if answer == 'y':
			exit()
		elif answer == 'n':
			print('tough luck.')
			exit()
		else:
			print('only "y" or "n"')

def convert_to_date(stamp):
	### take str in the format "YYYYMMDDHHMMSS" and convert to datetime instance
	match = re.search('(^\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', stamp)
	return datetime.datetime(
		int(match.group(1)),
		int(match.group(2)),
		int(match.group(3)),
		int(match.group(4)),
		int(match.group(5)),
		int(match.group(6))
		)

def fromEXIF(file):
	
	# read image (binary mode), get EXIF info
	binImage = open(file, 'rb')
	tags = exifread.process_file(binImage)
	
	date = tags['EXIF DateTimeOriginal']
	date = re.sub(':', '', str(date))
	date = re.sub(' ', '', str(date))

	return str(date)

def fromAVI(file):
	### use ffprobe to extract date and time values from a .avi file

	tags = subprocess.run(
	['ffprobe',
	'-show_entries', 'format_tags',
	'-v', '-8',
	'-of', 'flat',
	os.path.abspath(file)],
	check=True, stdout=subprocess.PIPE, encoding="utf-8"
	).stdout

	date = re.search('date="(.*)"', tags).group(1)
	date = re.sub('\D', '', date)

	time = re.search('ICRT="(.*)"', tags).group(1)
	time = re.sub('\D', '', time)

	return date + time

def fromMOV(file):
	tags = subprocess.run(
	['ffprobe',
	'-show_entries', 'format_tags',
	'-v', '-8',
	'-of', 'flat',
	os.path.abspath(file)],
	check=True, stdout=subprocess.PIPE, encoding="utf-8"
	).stdout

	stamp = re.search('creation_time=(.*)', tags).group(1)
	# remove trailing timezome information
	stamp = re.sub('\..*', '', stamp)
	# convert to YYYYMMDDHHMMSS format
	stamp = re.sub('\D', '', stamp)

	return stamp

def get_stamp(file, filename, ext):
	# return a datetime instance

	# define valid extensions
	EXIFfiles = ['.jpg', '.JPG', '.jpeg', '.JPEG']
	interleaved = ['.avi', '.AVI']
	QTFF = ['.mov', '.MOV']

	if ext in EXIFfiles:
		try:
			stamp = fromEXIF(file)
		except KeyError:
			alt()

	elif ext in interleaved:
		try:
			stamp = fromAVI(file)
		except KeyError:
			alt()

	elif ext in QTFF:
		try:
			stamp = fromMOV(file)
		except KeyError:
			alt()

	elif ext == '.MTS':
		alt()

	else:
		print('file type not recognized! skipping...')

	return convert_to_date(stamp)

def check_exists(stamp, descr, ext):
	if os.path.isfile(str(stamp) + descr + ext):
		pass
		# increment stamp

####################################################################################################
descr = input('Enter a description of the pictures. otherwise, press Return ')
# unless the description is blank, we want a leading space
if descr != '':
	descr = ' ' + descr

lastStamp = ''
for file in glob.glob('*'):
	filename, ext = os.path.splitext(file)

	stamp = get_stamp(file, filename, ext)
	lastStamp = stamp
	# while True:
	# 	if check_exists(stamp, descr, ext) == True:
	# 		# if a file already exists which has the same timestamp, increment
	# 		# if this is also taken, maybe append counter?
	# 		pass
	# else:
	os.rename(file, stamp.strftime('%Y-%m-%d %H.%M.%S') + descr + ext)