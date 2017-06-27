# Script accepts folders containing files with filename of structure "YYYY-MM-DD HH.MM.SS"

import glob, re, os, sys, datetime

directory = sys.argv[1]
os.chdir(directory)

print("input offset in hours, then minutes, then seconds. only input integers. input may also be zero or negative")
offByHours = int(raw_input("how many hours offset?\n"))
offByMin = int(raw_input("how many minutes offset?\n"))
offBySec = int(raw_input("how many seconds offset?\n"))


for file in glob.glob('*'):
	filename, file_extension = os.path.splitext(file)
	match = re.search('(\d{4})-(\d{2})-(\d{2}) (\d{2}).(\d{2}).(\d{2})', filename)
	
#	we could create new objects here, but we'll just pass the arguments directly to datetime
# 	year = int(match.group(1))
# 	month = int(match.group(2))
# 	day = int(match.group(3))
# 	hour = int(match.group(4))
# 	minute = int(match.group(5))
# 	second = int(match.group(6))
	
	oldTime = datetime.datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4)), int(match.group(5)), int(match.group(6)))
	newTime = oldTime + datetime.timedelta(seconds=offBySec, minutes=offByMin, hours=offByHours)
	
	new_name = newTime.strftime('%Y-%m-%d %H.%M.%S')
	os.rename(file, new_name + file_extension)