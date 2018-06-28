#!/usr/bin/env python3

import glob
import re
import os
import sys
import datetime
import exifread
import subprocess
import logging
from argparse import ArgumentParser

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler())

def convert_to_date(stamp):
    """take str in the format "YYYYMMDDHHMMSS"
    and convert to datetime instance
    """
    match = re.search(r'(^\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', stamp)
    return datetime.datetime(
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        int(match.group(4)),
        int(match.group(5)),
        int(match.group(6))
        )

def increment_stamp(fBundle, lastStamp):
    if not lastStamp:
        exit('we have no timestamp to increment. '
             'unable to recover. exiting...')
    
    newStamp = lastStamp + datetime.timedelta(seconds=1)
    print('new timestamp:',
          newStamp.strftime('%Y-%m-%d %H.%M.%S'),
          '\n'
          )

    fBundle['tStamp'] = newStamp

    return fBundle

def from_IMG(fBundle):
    # WhatsApp Image?
    if re.search(r'IMG-\d{8}-WA\d{4}', fBundle['fName']):
        fBundle['fName'] = re.sub(
            r'IMG-(\d{4})(\d{2})(\d{2})-(WA\d{4})',
            r'\1-\2-\3 \4',
            fBundle['fName']
            )
    else:
        try:
            # read image (binary mode), get EXIF info
            binImage = open(fBundle['f'], 'rb')

            tags = exifread.process_file(binImage)
            stamp = tags['EXIF DateTimeOriginal']
            stamp = re.sub(':', '', str(stamp))
            stamp = re.sub(' ', '', str(stamp))

            fBundle['tStamp'] = convert_to_date(stamp)
            fBundle['fName'] = ''
        except KeyError:
            fBundle['alt'] = True

    return fBundle

def from_AVI(fBundle):
    try:
        tags = subprocess.run(
            [
                'ffprobe',
                '-show_entries', 'format_tags',
                '-v', '-8',
                '-of', 'flat', os.path.abspath(fBundle['f'])
            ],
            check=True,
            stdout=subprocess.PIPE,
            encoding="utf-8"
            ).stdout

        date = re.search('date="(.*)"', tags).group(1)
        date = re.sub(r'\D', '', date)

        time = re.search('ICRT="(.*)"', tags).group(1)
        time = re.sub(r'\D', '', time)

        fBundle['tStamp'] = convert_to_date(date + time)
        fBundle['fName'] = ''
    except KeyError:
        fBundle['alt'] = True

    return fBundle

def from_MP4(fBundle):
    try:
        tags = subprocess.run(
            [
                'ffprobe',
                '-show_entries', 'format_tags',
                '-v', '-8',
                '-of', 'flat', os.path.abspath(fBundle['f'])
            ],
            check=True,
            stdout=subprocess.PIPE,
            encoding="utf-8"
            ).stdout

        stamp = re.search('creation_time=(.*)', tags).group(1)
        # remove trailing timezone information
        stamp = re.sub(r'\..*', '', stamp)
        # convert to YYYYMMDDHHMMSS format
        stamp = re.sub(r'\D', '', stamp)

        fBundle['tStamp'] = convert_to_date(stamp)
        fBundle['fName'] = ''
    except KeyError:
        fBundle['alt'] = True

    return fBundle

def get_timestamp(fBundle, lastStamp):
    # define valid extensions
    IMGfiles = ['.jpg', '.JPG', '.jpeg', '.JPEG']
    AVIfiles = ['.avi', '.AVI']
    MP4files = ['.mp4', '.MP4', '.mov', '.MOV']

    if fBundle['ext'] in IMGfiles:
        fBundle = from_IMG(fBundle)
    elif fBundle['ext'] in AVIfiles:
        fBundle = from_AVI(fBundle)
    elif fBundle['ext'] in MP4files:
        fBundle = from_MP4(fBundle)
    else:
        print('file type not recognized!')
        exit(1)

    if fBundle['alt']:
        print('ERROR: ' + fBundle['f'] + ' does not contain timestamp!')
        increment_stamp(fBundle, lastStamp)
        # keep filename, denote incrementation with 'i'
        fBundle['fName'] = ' i '

    return fBundle

def check_and_increment(fBundle):
    newFile = '{}{}{}'.format(
        fBundle['tStamp'].strftime('%Y-%m-%d %H.%M.%S'),
        fBundle['descr'],
        fBundle['ext']
        )

    firstFile = '{} 00{}{}'.format(
        fBundle['tStamp'].strftime('%Y-%m-%d %H.%M.%S'),
        fBundle['descr'],
        fBundle['ext']
        )

    if not os.path.exists(newFile) and not os.path.exists(firstFile):
        logger.debug('new file: {}\n'.format(newFile))
        return newFile

    cwd = os.getcwd()
    ls = set(os.listdir(cwd))
    index = 1

    def gen_cand():
        return '{} {}{}{}'.format(
            fBundle['tStamp'].strftime('%Y-%m-%d %H.%M.%S'),
            str(index).zfill(2),
            fBundle['descr'],
            fBundle['ext']
            )
    if not os.path.exists(firstFile):
        logger.debug('previous file to: {}'.format(firstFile))
        os.rename(newFile, firstFile)
        newFile = gen_cand()
        logger.debug('current file to:  {}\n'.format(newFile))
        return newFile

    newFile = gen_cand()
    logger.debug('--------------\ngenerating candidates')
    while newFile in ls:
        logger.debug('candidate: {}'.format(newFile))
        newFile = gen_cand()
        index += 1
    logger.debug('chosen:    {}\n'.format(newFile))
    return newFile

################################################################################
def parse_arguments():
    parser = ArgumentParser(description='rename images to the '
    'format YYYY-MM-DD hh.mm.ss Description.')
    parser.add_argument('folder', help='folder to parse')
    
    return parser.parse_args()

def main(directory):
    os.chdir(directory)

    description = input('Enter a description of the pictures '
    '(may be blank), then press Return  ')
    # we want a leading space, except when the description is blank
    if description != '':
        description = ' ' + description

    lastStamp = ''
    for file in glob.glob('*'):
        fBundle = {'f': file,
                   'tStamp': '',
                   'fName': os.path.splitext(file)[0],
                   'ext': os.path.splitext(file)[1],
                   'descr': description,
                   'alt': False
                   }
        fBundle = get_timestamp(fBundle, lastStamp)
        lastStamp = fBundle['tStamp']

        if not fBundle['tStamp']:
            increment_stamp(fBundle, lastStamp)
        
        os.rename(file, check_and_increment(fBundle))

if __name__ == '__main__':
    args = parse_arguments()
    main(args.folder)