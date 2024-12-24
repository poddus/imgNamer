#!/usr/bin/env python3

import re
import os
from glob import glob
import sys
from datetime import datetime, timedelta
from threading import currentThread
import exifread
import subprocess
import logging
from dataclasses import dataclass
from argparse import ArgumentParser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def timestamp_from_name(currentFile) -> str:
    """attempt to regex a datetime from the fileStem
       TODO: extract any trailing str and pass it to description
    """

    # additional tests for common sources for debugging purposes
    if logger.isEnabledFor(logging.DEBUG):
        # sony cybershot
        if re.search(r'^DSC', currentFile.fileStem):
            logger.debug(f'file {currentFile.basename} is probably '
                          'from a Sony Cybershot and should have exif data')
        # Apple iPhone LivePhoto
        elif currentFile.fileType == 'mp4' and re.search(r'^IMG_\d{4}', currentFile.fileStem):
            logger.warning(f'file {currentFile.basename} is probably '
                          'from an iPhone with "Live Photo" function enabled.'
                          'these video files may have erroneous exif data!')

    # timestamp name without 3-letter prefix.
    # this is the default for most android distros
    if re.search(r'^\d{8}_\d{6}', currentFile.fileStem):
        logger.debug(f'found default timestamp for file {currentFile.basename}')
        return re.sub(
            r'^[a-zA-Z]{3}(\d{8})_(\d{6})',
            r'\1\2',
            currentFile.fileStem
            )
    # timestamp name with 3-letter prefix (i.e. 'IMG', 'VID', 'PXL')
    # also common in android distros
    elif re.search(r'^[a-zA-Z]{3}_\d{8}_\d{6}', currentFile.fileStem):
        logger.debug(f'found prefixed timestamp for file {currentFile.basename}')
        return re.sub(
            r'^[a-zA-Z]{3}_(\d{8})_(\d{6})',
            r'\1\2',
            currentFile.fileStem
            )
    # already processed by old script (periods in time)
    elif re.search(r'^\d{4}-\d{2}-\d{2} \d{2}.\d{2}.\d{2}', currentFile.fileStem):
        logger.debug(f'file {currentFile.basename} has probably '
                      'already been processed by this script previously.')
        return re.sub(
            r'^(\d{4})-(\d{2})-(\d{2}) (\d{2}).(\d{2}).(\d{2})',
            r'\1\2\3\4\5\6',
            currentFile.fileStem)
    # already processed by current script (hyphens in time)
    elif re.search(r'^\d{4}-\d{2}-\d{2} \d{2}-\d{2}-\d{2}', currentFile.fileStem):
        logger.debug(f'file {currentFile.basename} has probably '
                      'already been processed by this script previously.')
        return re.sub(
            r'^(\d{4})-(\d{2})-(\d{2}) (\d{2})-(\d{2})-(\d{2})',
            r'\1\2\3\4\5\6',
            currentFile.fileStem)
    # WhatsApp Image
    # this does not yield a complete YYYYMMDDHHMMSS time stamp
    # but it's the best we've got. returns time stamp in format
    # 'YYYY-MM-DD WA[INT]'
    elif re.search(r'IMG-\d{8}-WA\d{4}', currentFile.fileStem):
        logger.warning(f'time stamp for file {currentFile.basename} is incomplete!'
                        'perhaps it is a WhatsApp file? '
                        'returning incomplete timestamp from file name...')
        return re.sub(
            r'IMG-(\d{4})(\d{2})(\d{2})-(WA\d{4})',
            r'\1-\2-\3 \4',
            currentFile.fileStem
            )
    else:
        logger.info('no time stamp recoverable from file stem '
                      f'of file {currentFile.fileStem}')
        return ''

def timestamp_from_exif(currentFile) -> str:
    try:
        match currentFile.fileType:
            case 'jpg':
                # read image (binary mode), get EXIF info
                binImage = open(currentFile.basename, 'rb')

                tags = exifread.process_file(binImage)
                stamp = tags['EXIF DateTimeOriginal']
                stamp = re.sub(':', '', str(stamp))
                stamp = re.sub(' ', '', str(stamp))

                return stamp
            case 'avi':
                tags = subprocess.run(
                    [
                        'ffprobe',
                        '-show_entries', 'format_tags',
                        '-v', '-8',
                        '-of', 'flat', os.path.abspath(currentFile.basename)
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    encoding="utf-8"
                    ).stdout
                date = re.search('date="(.*)"', tags).group(1)
                date = re.sub(r'\D', '', date)

                time = re.search('ICRT="(.*)"', tags).group(1)
                time = re.sub(r'\D', '', time)

                return date + time
            case 'mp4':
                tags = subprocess.run(
                [
                    'ffprobe',
                    '-show_entries', 'format_tags',
                    '-v', '-8',
                    '-of', 'flat', os.path.abspath(currentFile.basename)
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

                return stamp
    except KeyError:
        logger.warning('no time stamp in exif data '
                       'for file {}!').format(currentFile.basename)
        return ''

def set_new_name(currentFile) -> str:
    """checks for files with the same basename (i.e. same creation time)
       and generates a new basename accordingly.
       will append a 2 digit counter to timestamp
    """

    # we only need to evaluate the time stamps once
    finalTimeStamp = currentFile.return_timeStamp()

    candidateBasename = '{}{}{}'.format(
                        finalTimeStamp,
                        currentFile.description,
                        currentFile.fileExtension
                        )

    candidateBasename00 = '{} 00{}{}'.format(
                          finalTimeStamp,
                          currentFile.description,
                          currentFile.fileExtension
                          )

    if not os.path.exists(candidateBasename) and not os.path.exists(candidateBasename00):
        return candidateBasename
    else:
        logger.info(f'{candidateBasename} already exists. appending counter...')

        # get list of files in current working directory
        # increment counter until a candidate is generated that
        # doesn't yet exist
        cwd = os.getcwd()
        ls = set(os.listdir(cwd))
        index = 1
        def increment_candidate() -> str:
            return '{} {}{}{}'.format(
                finalTimeStamp,
                str(index).zfill(2),
                currentFile.description,
                currentFile.fileExtension
                )

        # special case where we append 00 to the existing file
        # and 01 to the current file
        if not os.path.exists(candidateBasename00):
            logger.info('renaming existing file {} -> {}'.format(
                         candidateBasename,
                         candidateBasename00))
            os.rename(candidateBasename, candidateBasename00)
            candidateBasename = increment_candidate()
            # returns candidateBasename 01
            return candidateBasename

        # for all other cases where the counter will be greater than 01
        candidateBasename = increment_candidate()
        while candidateBasename in ls:
            logger.info(f'{candidateBasename} already exists. incrementing counter...')
            candidateBasename = increment_candidate()
            index += 1
        return candidateBasename

################################################################################

@dataclass(kw_only=True, slots=True)
class MediaFile:
    # a word on terminology as used here:
    # the 'basename' is the file name including extension
    # the 'fileStem' is the file name without the extension
    # the 'fileRelativePath' is the path from the current dir
    # the 'fileAbsolutePath' is the path from the filesystem root
    basename: str
    description: str

    fileStem: str = ''
    fileExtension: str = ''
    fileType: str = ''
    timeStampExif: str = ''
    timeStampName: str = ''

    __JPG = ['.jpg', '.JPG', '.jpeg', '.JPEG']
    __AVI = ['.avi', '.AVI']
    __MP4 = ['.mp4', '.MP4', '.mov', '.MOV']

    def __post_init__(self) -> None:
        self.fileStem = os.path.splitext(self.basename)[0]
        self.fileExtension = os.path.splitext(self.basename)[1]

        if self.fileExtension in self.__JPG:
            self.fileType = 'jpg'
        elif self.fileExtension in self.__MP4:
            self.fileType = 'mp4'
        elif self.fileExtension in self.__AVI:
            self.fileType = 'avi'
        else:
            logger.critical(f'file type not recognized for {self.basename}')
            exit(1)

    def return_timeStamp(self) -> str:
        """Verifies timeStamps from Name and Exif Data and
        (ideally) returns a single formatted time stamp.
        """
        def format_timeStamp(timeStamp: str) -> str:
            return re.sub(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})',
                          r'\1-\2-\3 \4-\5-\6',
                          timeStamp)

        if self.timeStampExif == self.timeStampName != '':
            logger.debug(f'timestamps for {self.basename} are in agreement')
            return format_timeStamp(self.timeStampExif)
        elif self.timeStampExif == '' and self.timeStampName != '':
            logger.warning(f'no time stamp from Exif data for file {self.basename}. '
                            'defaulting to time stamp from basename...')
            return format_timeStamp(self.timeStampName)
        elif self.timeStampExif != '' and self.timeStampName == '':
            logger.warning(f'no time stamp from basename for file {self.basename}. '
                            'defaulting to time stamp from exif data...')
            return format_timeStamp(self.timeStampExif)
        elif self.timeStampExif == self.timeStampName == '':
            logger.critical('no valid timestamp for {}!\n'
                            'timeStampName: {}\n'
                            'timeStampExif: {}'.format(
                            self.basename,
                            self.timeStampName,
                            self.timeStampExif))
            exit(1)
        else:
            logger.warning('time stamps from basename and exif data do not match '
                           'for file {}. it has the following timestamps:\n'
                           'timeStampExif: {}\n'
                           'timeStampName: {}'.format(
                            self.basename,
                            self.timeStampExif,
                            self.timeStampName))
            match args.i:
                case True:
                    while True:
                        choice = input('select timeStampExif with 1, timeStampName with 2: ')
                        if choice in ['1', '2']:
                            break
                    if choice == '1':
                        return format_timeStamp(self.timeStampExif)
                    if choice == '2':
                        return format_timeStamp(self.timeStampName)
                case False:
                    if args.n:
                        logger.debug('using timeStampName: {}'.format(
                            self.timeStampName))
                        return format_timeStamp(self.timeStampName)
                    else:
                        logger.debug('using timeStampExif: {}'.format(
                            self.timeStampExif))
                        return format_timeStamp(self.timeStampExif)
            exit(70)

def parse_arguments():
    parser = ArgumentParser(description='rename images to the '
    'format YYYY-MM-DD hh-mm-ss Description.')
    parser.add_argument('folder', help='folder to parse')
    timeStampChoice = parser.add_mutually_exclusive_group()
    timeStampChoice.add_argument('-i', action='store_true', help='manually choose datetime '
                        'when the choice is ambiguous')
    timeStampChoice.add_argument('-n', action='store_true', help='prefer time stamp '
                        'derived from name when the choice is ambiguous. '
                        'by default the exif data will be used. '
                        'only works in standard (non-interactive) mode.')
    
    return parser.parse_args()

def main(args):
    os.chdir(args.folder)

    description = input('Enter a description of the pictures '
    '(may be blank), then press Return: ')
    print('')

    # we want a leading space, except when the description is blank
    if description != '':
        description = ' ' + description

    # glob returns only regular files, not dot files
    for path in glob('*'):
        currentFile = MediaFile(basename=path, description=description)
        currentFile.timeStampName = timestamp_from_name(currentFile)
        currentFile.timeStampExif = timestamp_from_exif(currentFile)

        basenameNew = set_new_name(currentFile)

        logger.debug('renaming {} -> {}\n'.format(currentFile.basename, basenameNew))
        os.rename(path, basenameNew)

if __name__ == '__main__':
    args = parse_arguments()
    main(args)
