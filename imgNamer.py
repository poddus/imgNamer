#!/usr/bin/env python3

import re
import os
from glob import glob
import exifread
import subprocess
import logging
from dataclasses import dataclass
from argparse import ArgumentParser

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())


def get_timestamp_from_name(currentFile) -> str:
    """attempt to regex a datetime from the fileStem
    TODO: extract any trailing str and optinally pass it to description
    """

    # additional tests for common sources for debugging purposes
    if logger.isEnabledFor(logging.DEBUG):
        # sony cybershot
        if re.search(r'^DSC', currentFile.fileStem):
            logger.debug(f'{currentFile.basename} is probably '
                          'from a Sony Cybershot and should have exif data. '
                          'sometimes these cameras do not have their clocks set properly.')
        # Apple iPhone LivePhoto
        elif currentFile.fileType == 'mp4' and re.search(r'^IMG_\d{4}', currentFile.fileStem):
            logger.warning(f'{currentFile.basename} is probably '
                          'from an iPhone with "Live Photo" function enabled. '
                          'these video files may have erroneous metadata!')

    # timestamp name without 3-letter prefix.
    # this is the default for most android distros
    if re.search(r'^\d{8}_\d{6}', currentFile.fileStem):
        logger.debug(f'found default timestamp in file stem of {currentFile.basename}')
        return re.sub(
            r'(\d{8})_(\d{6})$',
            r'\1\2',
            currentFile.fileStem
            )
    # timestamp name with 3-letter prefix (i.e. 'IMG', 'VID', 'PXL')
    # also common in android distros
    elif re.search(r'^[a-zA-Z]{3}_\d{8}_\d{6}', currentFile.fileStem):
        logger.debug(f'found prefixed timestamp in file stem of {currentFile.basename}')
        return re.sub(
            r'^[a-zA-Z]{3}_(\d{8})_(\d{6})$',
            r'\1\2',
            currentFile.fileStem
            )
    # already processed by old script (periods in time)
    elif re.search(r'^\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}', currentFile.fileStem):
        logger.debug(f'{currentFile.basename} has probably '
                      'already been processed by an old version of '
                      'this script previously.')
        return re.sub(
            r'^(\d{4})-(\d{2})-(\d{2}) (\d{2}).(\d{2}).(\d{2})',
            r'\1\2\3\4\5\6',
            currentFile.fileStem)
    # already processed by current script (hyphens in time)
    elif re.search(r'^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}', currentFile.fileStem):
        logger.info(f'{currentFile.basename} has probably '
                      'already been processed by this script previously. '
                      'this file will not be processed further.\n')
        return 'DO_NOT_PROCESS'
    # WhatsApp Image
    # this does not yield a complete YYYYMMDDHHMMSS time stamp
    # but it's the best we've got. returns time stamp in format
    # 'YYYY-MM-DD WA[INT]'
    elif re.search(r'IMG-\d{8}-WA\d{4}', currentFile.fileStem):
        logger.warning(f'time stamp of {currentFile.basename} is incomplete!'
                        'perhaps it is a WhatsApp file? '
                        'returning incomplete timestamp from file name...')
        return re.sub(
            r'IMG-(\d{4})(\d{2})(\d{2})-(WA\d{4})',
            r'\1-\2-\3 \4',
            currentFile.fileStem
            )
    else:
        logger.info('no time stamp recoverable from file stem '
                      f'of {currentFile.basename}')
        return ''

def get_timestamp_from_metadata(currentFile) -> str:
    try:
        match currentFile.fileType:
            case 'jpg':
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
        logger.warning('no time stamp in metadata '
                       'of {}!'.format(currentFile.basename))
        return ''

def set_new_name(currentFile) -> str:
    """checks for files with the same basename (i.e. same creation time)
    and generates a new basename accordingly.
    will append a 2 digit counter to timestamp if a file of the
    same name already exists.
    """

    # we only need to evaluate the time stamps once
    finalTimeStamp = currentFile.return_timeStamp()

    candidateBasename = '{}{}{}'.format(
                        finalTimeStamp,
                        currentFile.description,
                        currentFile.fileExtension
                        )

    candidateBasename00 = '{}_00{}{}'.format(
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
            return '{}_{}{}{}'.format(
                finalTimeStamp,
                str(index).zfill(2),
                currentFile.description,
                currentFile.fileExtension
                )

        # special case for first collision where we append 
        # 00 to the existing file and 
        # 01 to the current file
        if not os.path.exists(candidateBasename00):
            logger.info('renaming existing file {} -> {}'.format(
                         candidateBasename,
                         candidateBasename00))
            os.rename(candidateBasename, candidateBasename00)
            candidateBasename = increment_candidate()
            # returns "candidateBasename 01"
            return candidateBasename

        # for all other cases where the counter will be greater than 01
        candidateBasename = increment_candidate()
        while candidateBasename in ls:
            logger.info(f'{candidateBasename} already exists. incrementing counter...')
            candidateBasename = increment_candidate()
            index += 1
        return candidateBasename

####################################################################################################

@dataclass(kw_only=True, slots=True)
class MediaFile:
    """Represents a jpeg, avi, or mp4 file with its time stamp and description.
    a word on terminology as used here:
    the 'basename' is the file name including extension
    the 'fileStem' is the file name without the extension
    """
    basename: str
    description: str

    fileStem: str = ''
    fileExtension: str = ''
    fileType: str = ''
    timeStampMetadata: str = ''
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
        """Verifies timeStamps from Name and Metadata and
        (ideally) returns a single formatted time stamp.
        """
        def _format_timeStamp(timeStamp: str) -> str:
            return re.sub(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})',
                          r'\1-\2-\3_\4-\5-\6',
                          timeStamp)

        if self.timeStampName == 'DO_NOT_PROCESS':
            return self.timeStampName
        elif self.timeStampMetadata == self.timeStampName != '':
            logger.debug(f'timestamps for {self.basename} are in agreement')
            return _format_timeStamp(self.timeStampMetadata)
        elif self.timeStampMetadata == '' and self.timeStampName != '':
            logger.warning(f'no time stamp from metadata for file {self.basename}. '
                            'defaulting to time stamp from basename...')
            return _format_timeStamp(self.timeStampName)
        elif self.timeStampMetadata != '' and self.timeStampName == '':
            logger.warning(f'no time stamp from basename for file {self.basename}. '
                            'defaulting to time stamp from metadata...')
            return _format_timeStamp(self.timeStampMetadata)
        elif self.timeStampMetadata == self.timeStampName == '':
            logger.critical('no valid timestamp for {}!\n'
                            'timeStampName: {}\n'
                            'timeStampMetadata {}'.format(
                            self.basename,
                            self.timeStampName,
                            self.timeStampMetadata))
            exit(1)
        else:
            logger.warning('time stamps from basename and metadata do not match '
                           'for file {}. it has the following timestamps:\n'
                           'timeStampMetadata: {}\n'
                           'timeStampName: {}'.format(
                            self.basename,
                            self.timeStampMetadata,
                            self.timeStampName))

            if args.i:
                while True:
                    choice = input('select timeStampMetadata with 1, timeStampName with 2: ')
                    if choice == '1':
                        return _format_timeStamp(self.timeStampMetadata)
                    if choice == '2':
                        return _format_timeStamp(self.timeStampName)
            else:
                if args.n:
                    logger.debug('using timeStampName: {}'.format(
                        self.timeStampName))
                    return _format_timeStamp(self.timeStampName)
                else:
                    logger.debug('using timeStampMetadata: {}'.format(
                        self.timeStampMetadata))
                    return _format_timeStamp(self.timeStampMetadata)

def parse_arguments():
    parser = ArgumentParser(description='This program renames media files to the '
        'format "YYYY-MM-DD_hh-mm-ss[_00] Description" based on timestamps gleaned '
        'from name and metadata. The ISO 8601 format is not particularly human-readable without '
        'delimiters and the standard time delimiter ":" is not allowed in file names. '
        'This format is a compromise. There is also a strict mode which '
        'enforces "web-friendly" filenames.')
    parser.add_argument('folder', help='folder to parse, for example the current directory: ./')
    parser.add_argument('-s', action='store_true', help='strict mode, only accepts '
        'characters unreserved for URIs, i.e. '
        'ALPHA / DIGIT / "-" / "." / "_" / "~". (see RFC 3986 Section 2.3)')
    parser.add_argument('--rename', action='store_true', help='actually rename files. '
        'without this flag the program does a dry run but leaves out the actual write operation')
    timeStampChoice = parser.add_mutually_exclusive_group()
    timeStampChoice.add_argument('-i', action='store_true', help='manually choose '
                        'timestamp when the choice is ambiguous')
    timeStampChoice.add_argument('-n', action='store_true', help='prefer timestamp derived '
                        'from name when the choice is ambiguous. '
                        'by default the metadata will be used. '
                        'only works in standard (non-interactive) mode.')
    
    return parser.parse_args()

def _get_description(strictMode: bool) -> str:
    while True:
        description = input('Enter a description of the pictures '
        '(may be blank), then press Return: ')
        if strictMode:
            if re.fullmatch(r'[a-zA-Z0-9\-._~]+', description) or description == '':
                print('')
                break
            else:
                print('only ALPHA / DIGIT / "-" / "." / "_" / "~" are allowed in strict mode!')
        else:
            # it appears as though we don't need to worry about null chars \0 when using input()
            if not re.search(r'[/:\'"]+', description):
                print('')
                break
            else:
                print('do not use these characters because they tend to break stuff ->  / : \' "')

    # we want a leading underscore or space, except when the description is blank
    if description == '':
        return description
    else:
        if strictMode:
            return '_' + description
        else:
            return ' ' + description

def main(args):
    os.chdir(args.folder)

    if not args.rename:
        logger.info('dry-run mode, files will not be renamed.')
    else:
        logger.warning('renaming mode, FILES WILL BE RENAMED!')

    description = _get_description(args.s)

    # glob returns only regular files, not dot files
    for path in glob('*'):
        currentFile = MediaFile(basename=path, description=description)
        currentFile.timeStampName = get_timestamp_from_name(currentFile)
        if currentFile.timeStampName == 'DO_NOT_PROCESS':
            continue
        currentFile.timeStampMetadata = get_timestamp_from_metadata(currentFile)

        basenameNew = set_new_name(currentFile)

        if args.rename:
            logger.debug('renaming {} -> {}\n'.format(currentFile.basename, basenameNew))
            os.rename(path, basenameNew)
        else:
            logger.info('suggested name change {} -> {}\n'.format(
                currentFile.basename, basenameNew))

if __name__ == '__main__':
    args = parse_arguments()
    main(args)
