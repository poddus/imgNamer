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

def alt(fName, WA=False):
	# perhaps its useful to simply increment the last value

	stamp = ''
	if WA is True:
		fName = re.sub(r'IMG-(\d{4})(\d{2})(\d{2})-(WA\d{4})', r'\1-\2-\3 \4', fName)
	else:
		print('ERROR: ' + file + ' does not contain timestamp!')
		if lastStamp == '':
			print('oh no!')
			exit()
		else:
			while True:
				answer = input('do you want to increment the last timestamp:\n' + lastStamp.strftime('%Y-%m-%d %H.%M.%S') + ' ?  ')
				if answer == 'y':
					stamp = lastStamp + datetime.timedelta(seconds=1)
					fName = ''
					break
				elif answer == 'n':
					print('sorry, bro. can\'t help you')
					exit()
				else:
					print('only "y" or "n"')

	return stamp, fName

def convert_to_date(stamp):
	"""take str in the format "YYYYMMDDHHMMSS" and convert to datetime instance"""
	match = re.search(r'(^\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', stamp)
	return datetime.datetime(
		int(match.group(1)),
		int(match.group(2)),
		int(match.group(3)),
		int(match.group(4)),
		int(match.group(5)),
		int(match.group(6))
		)

def fromEXIF(f):
	
	# read image (binary mode), get EXIF info
	binImage = open(f, 'rb')
	tags = exifread.process_file(binImage)
	
	stamp = tags['EXIF DateTimeOriginal']
	stamp = re.sub(':', '', str(stamp))
	stamp = re.sub(' ', '', str(stamp))

	return str(stamp)

def fromAVI(f):
	"""use ffprobe to extract date and time values from a .avi file"""

	tags = subprocess.run(
	['ffprobe',
	'-show_entries', 'format_tags',
	'-v', '-8',
	'-of', 'flat',
	os.path.abspath(f)],
	check=True, stdout=subprocess.PIPE, encoding="utf-8"
	).stdout

	date = re.search('date="(.*)"', tags).group(1)
	date = re.sub(r'\D', '', date)

	time = re.search('ICRT="(.*)"', tags).group(1)
	time = re.sub(r'\D', '', time)

	return date + time

def fromMOV(f):
	tags = subprocess.run(
	['ffprobe',
	'-show_entries', 'format_tags',
	'-v', '-8',
	'-of', 'flat',
	os.path.abspath(f)],
	check=True, stdout=subprocess.PIPE, encoding="utf-8"
	).stdout

	stamp = re.search('creation_time=(.*)', tags).group(1)
	# remove trailing timezome information
	stamp = re.sub(r'\..*', '', stamp)
	# convert to YYYYMMDDHHMMSS format
	stamp = re.sub(r'\D', '', stamp)

	return stamp

def get_stamp(f, fName, ext):
	"""create timestamp and clear filename if possible, else change filename

	setting the filename to empty string acts as a signal that a valid timestamp exists
	"""

	success = False

	# define valid extensions
	EXIFfiles = ['.jpg', '.JPG', '.jpeg', '.JPEG']
	AVIfiles = ['.avi', '.AVI']
	QTFF = ['.mov', '.MOV']

	if ext in EXIFfiles:
		if re.search(r'IMG-\d{8}-WA\d{4}', fName):
			stamp, fName = alt(fName, True)
			success = False
		else:
			try:
				stamp = fromEXIF(f)
				success = True
			except KeyError:
				stamp, fName = alt(fName)

	elif ext in AVIfiles:
		try:
			stamp = fromAVI(f)
			success = True
		except KeyError:
			stamp, fName = alt(fName)

	elif ext in QTFF:
		try:
			stamp = fromMOV(f)
			success = True
		except KeyError:
			stamp, fName = alt(fName)

	elif ext == '.MTS':
		pass

	else:
		print('file type not recognized!')
		exit(1)

	if success == False:
		# in this situation, stamp is either already a valid datetime instance, or empty string
		return stamp, fName
	else:
		fName = ''
		return convert_to_date(stamp), fName

def check_exists(stamp, descr, ext):
	if os.path.isfile(str(stamp) + descr + ext):
		pass
		# increment stamp

########################################################################################################
description = input('Enter a description of the pictures (may be blank), then press Return  ')
# unless the description is blank, we want a leading space
if description != '':
	description = ' ' + description

# keep the last valid stamp as a buffer in order to be able to increment for a file with no valid timestamp
lastStamp = ''

for file in glob.glob('*'):
	filename, extension = os.path.splitext(file)

	timeStamp, filename = get_stamp(file, filename, extension)

	if filename == '':
		lastStamp = timeStamp
		os.rename(file, timeStamp.strftime('%Y-%m-%d %H.%M.%S') + description + extension)
	else:
		os.rename(file, filename + description + extension)

	# while True:
	# 	if check_exists(stamp, descr, ext) == True:
	# 		# if a file already exists which has the same timestamp, increment
	# 		# if this is also taken, maybe append counter?
	# 		pass
	# else:
