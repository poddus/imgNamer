#!/usr/bin/env python3

from _typeshed import DataclassInstance
import re
import os
import sys
from datetime import datetime, timedelta
import exifread
import subprocess
import logging
from dataclasses import dataclass
from argparse import ArgumentParser

def timestamp_from_name(currentFile) -> str:
    """attempt to regex a datetime from the filename
       TODO: extract any trailing str and pass it to description
    """

    # additional tests for common sources for debugging purposes
    if logger.isEnabledFor(logging.DEBUG):
        # sony cybershot
        if re.search(r'^DSC', currentFile.fileNameOld):
            logger.debug(f'file {currentFile.filePath} is probably '
                          'from a Sony Cybershot and should have Exif data')
        # Apple iPhone LivePhoto
        elif currentFile.fileType == 'mp4' and re.search(r'^IMG_\d{4}', currentFile.fileNameOld):
            logger.warning(f'file {currentFile.filePath} is probably '
                          'from an iPhone with "Live Photo" function enabled.'
                          'these video files may have erroneous Exif data!')

    # timestamp name without 3-letter prefix.
    # this is the default for most android distros
    if re.search(r'^[a-zA-Z]{3}_\d{8}_\d{6}', currentFile.fileNameOld):
        return re.sub(
            r'^[a-zA-Z]{3}(\d{8})_(\d{6})',
            r'\1\2',
            currentFile.fileNameOld
            )
    # timestamp name with 3-letter prefix (i.e. 'IMG', 'VID', 'PXL')
    # also common in android distros
    elif re.search(r'^[a-zA-Z]{3}_\d{8}_\d{6}', currentFile.fileNameOld):
        return re.sub(
            r'^[a-zA-Z]{3}(\d{8})_(\d{6})',
            r'\1\2',
            currentFile.fileNameOld
            )
    # already processed
    elif re.search(r'^\d{4}-\d{2}-\d{2} \d{2}.\d{2}.\d{2}', currentFile.fileNameOld):
        logger.debug(f'file {currentFile.filePath} has probably '
                      'already been processed by this script previously.')
        return re.sub(
            r'^(\d{4})-(\d{2})-(\d{2}) (\d{2}).(\d{2}).(\d{2})',
            r'\1\2\3\4\5\6',
            currentFile.fileNameOld)
    # WhatsApp Image
    # this does not yield a complete YYYYMMDDHHMMSS time stamp
    # but it's the best we've got. returns time stamp in format
    # 'YYYY-MM-DD WA[INT]'
    elif re.search(r'IMG-\d{8}-WA\d{4}', currentFile.fileNameOld):
        return re.sub(
            r'IMG-(\d{4})(\d{2})(\d{2})-(WA\d{4})',
            r'\1-\2-\3 \4',
            currentFile.fileNameOld
            )
    else:
        logger.warning('no time stamp recoverable from file name '
                      f'of file {currentFile.fileNameOld}')
        return ''

def timestamp_from_exif(currentFile) -> str:
    try:
        match currentFile.fileType:
            case 'jpg':
                # read image (binary mode), get EXIF info
                binImage = open(currentFile.filePath, 'rb')

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
                        '-of', 'flat', os.path.abspath(currentFile.filePath)
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
                    '-of', 'flat', os.path.abspath(currentFile.filePath)
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
        logger.warning('no time stamp in Exif data '
                      f'for file {currentFile.filePath}!')
        return ''


################################################################################

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

@dataclass(kw_only=True, slots=True)
class MediaFile:
    filePath: str
    description: str

    fileNameOld: str = ''
    fileNameNew: str = ''
    fileExtension: str = ''
    fileType: str = ''
    timeStampExif: str = ''
    timeStampName: str = ''

    __JPG = ['.jpg', '.JPG', '.jpeg', '.JPEG']
    __AVI = ['.avi', '.AVI']
    __MP4 = ['.mp4', '.MP4', '.mov', '.MOV']

    def __post_init__(self) -> None:
        self.fileNameOld = os.path.splitext(self.filePath)[0]
        self.fileExtension = os.path.splitext(self.filePath)[1]

        if self.fileExtension in self.__JPG:
            self.fileType = 'jpg'
        elif self.fileExtension in self.__MP4:
            self.fileType = 'mp4'
        elif self.fileExtension in self.__AVI:
            self.fileType = 'avi'
        else:
            logger.critical(f'file type not recognized for {self.filePath}')
            exit(1)

    def timeStamp_to_datetime(self, chosenTimeStamp) -> datetime:
        """take str in the format 'YYYYMMDDHHMMSS'
        and convert to datetime instance
        """
        match = re.search(r'(^\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', chosenTimeStamp)
        return datetime.datetime(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4)),
            int(match.group(5)),
            int(match.group(6))
            )

    def return_timeStamp(self) -> datetime | str:
        """Verifies timeStamps from Name and Exif Data and
        (ideally) returns a single datetime.
        """
        if self.timeStampExif == self.timeStampName != '':
            logger.debug(f'timestamps for {self.filePath} are in agreement')
            return self.timeStamp_to_datetime(self.timeStampExif)
        elif self.timeStampExif == '' and self.timeStampName != '':
            logger.warning(f'no time stamp from Exif data for file {self.filePath}.'
                            'defaulting to time stamp from file name...')
            try:
                return self.timeStamp_to_datetime(self.timeStampName)
            except:
                logger.warning(f'time stamp for file {self.filePath} cannot be turned '
                                'into a datetime instance! '
                                'perhaps it is a WhatsApp file? '
                                'returning raw timestamp from file name...')
                return self.timeStampName
        elif self.timeStampExif != '' and self.timeStampName == '':
            logger.warning(f'no time stamp from Exif data for file {self.filePath}.'
                            'defaulting to time stamp from file name...')
            return self.timeStamp_to_datetime(self.timeStampExif)
        elif self.timeStampExif == self.timeStampName == '':
            logger.critical(f'no valid timestamp for {self.filePath}!')
            exit(1)
        else:
            logger.critical(f'critical error returning time stamp for file {self.filePath}')
            exit(70)

def parse_arguments():
    parser = ArgumentParser(description='rename images to the '
    'format YYYY-MM-DD hh.mm.ss Description.')
    parser.add_argument('folder', help='folder to parse')
    
    return parser.parse_args()

def main(directory):
    os.chdir(directory)

    description = input('Enter a description of the pictures '
    '(may be blank), then press Return: ')
    # we want a leading space, except when the description is blank
    if description != '':
        description = ' ' + description

    for path in os.listdir(directory):
        currentFile = MediaFile(filePath=path, description=description)
        currentFile.timeStampName = timestamp_from_name(currentFile)
        currentFile.timeStampExif = timestamp_from_exif(currentFile)

        os.rename(file, check_and_increment(fBundle))

if __name__ == '__main__':
    args = parse_arguments()
    main(args.folder)
