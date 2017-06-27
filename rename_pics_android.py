import glob, re, os, sys

directory = sys.argv[1]
os.chdir(directory)

description = raw_input("Enter a description of the pictures. otherwise, press Return ")

for file in glob.glob('*'):
	filename, file_extension = os.path.splitext(file)
	new_name = re.sub('(^\d{4})(\d{2})(\d{2})([_])(\d{2})(\d{2})(\d{2})', r'\1-\2-\3 \5.\6.\7', filename)
	
	# if the description is blank, we don't want the leading space
	if(description == ""):
		os.rename(file, new_name + file_extension)
	else:
		os.rename(file, new_name + " " + description + file_extension)