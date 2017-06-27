import glob, re, os, sys, datetime

directory = sys.argv[1]
os.chdir(directory)

for file in glob.glob('*'):
	filename, file_extension = os.path.splitext(file)
	stats = os.stat(file)
	date = datetime.datetime.fromtimestamp(stats[8])
	cleanDate = re.sub(':', '.', str(date))
	os.rename(file, cleanDate + filename + file_extension)