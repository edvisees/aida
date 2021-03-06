"""
Script for generating AIF from LDCs annotations
"""

__author__  = "Shahzad Rajput <shahzad.rajput@nist.gov>"
__status__  = "production"
__version__ = "2019.0.1"
__date__    = "7 February 2020"

from aida.annotations import Annotations
from aida.container import Container
from aida.core_documents import CoreDocuments
from aida.document_mappings import DocumentMappings
from aida.encodings import Encodings
from aida.file_handler import FileHandler
from aida.image_boundaries import ImageBoundaries
from aida.video_boundaries import VideoBoundaries
from aida.keyframe_boundaries import KeyFrameBoundaries
from aida.logger import Logger
from aida.text_boundaries import TextBoundaries
from aida.aif_generator import AIFGenerator
from aida.slot_mappings import SlotMappings

import argparse
import os
import sys

ALLOK_EXIT_CODE = 0
ERROR_EXIT_CODE = 255

def check_paths(args):
    check_for_paths_existance([args.encodings_filename,
                 args.log_specifications_filename, 
                 args.core_documents_filename,
                 args.parent_children_filename,
                 args.sentence_boundaries_filename,
                 args.image_boundaries_filename,
                 args.video_boundaries_filename,
                 args.keyframe_boundaries_filename,
                 args.slot_mappings_filename,
                 args.type_mappings_filename,
                 args.annotations
                 ])
    check_for_paths_non_existance([args.output])

def check_for_paths_existance(paths):
    """
    Checks if the required files and directories were present,
    exit with an error code if any of the required file or directories
    were not found.
    """
    for path in paths:
        if not os.path.exists(path):
            print('Error: Path {} does not exist'.format(path))
            exit(ERROR_EXIT_CODE)

def check_for_paths_non_existance(paths):
    """
    Checks if the required files and directories were not present,
    exit with an error code if any of the required file or directories
    were not found.
    """
    for path in paths:
        if os.path.exists(path):
            print('Error: Path {} exists'.format(path))
            exit(ERROR_EXIT_CODE)

def main(args):
    """
    The main program for generating AIF
    """
    check_paths(args)
    logger = Logger(args.log, args.log_specifications_filename, sys.argv)
    core_documents = CoreDocuments(logger, args.core_documents_filename)
    encodings = Encodings(logger, args.encodings_filename)
    document_mappings = DocumentMappings(logger, args.parent_children_filename, encodings, core_documents)
    text_boundaries = TextBoundaries(logger, args.sentence_boundaries_filename)
    image_boundaries = ImageBoundaries(logger, args.image_boundaries_filename)
    video_boundaries = VideoBoundaries(logger, args.video_boundaries_filename)
    keyframe_boundaries = KeyFrameBoundaries(logger, args.keyframe_boundaries_filename)
    type_mappings = Container(logger)
    for entry in FileHandler(logger, args.type_mappings_filename):
        type_mappings.add(key=entry.get('full_type_ov'), value=entry.get('full_type'))
    slot_mappings = SlotMappings(logger, args.slot_mappings_filename)
    annotations = Annotations(logger, slot_mappings, document_mappings, text_boundaries, image_boundaries, video_boundaries, keyframe_boundaries, type_mappings, args.annotations, load_video_time_offsets_flag=args.notime)
    generator = AIFGenerator(logger, annotations, args.nochannel, args.reference_kb_id)
    generator.write_output(args.output)
    exit(ALLOK_EXIT_CODE)

if __name__ == '__main__':
    # create a parse and add command line arguments
    parser = argparse.ArgumentParser(description="Generate AIF")
    parser.add_argument('-l', '--log', default='log.txt', 
                        help='Specify a file to which log output should be redirected (default: %(default)s)')
    parser.add_argument('-v', '--version', action='version', version='%(prog)s ' + __version__, 
                        help='Print version number and exit')
    parser.add_argument('-r', '--reference_kb_id', default='REFKB',
                        help='Specify the reference KB ID (default: %(default)s)')
    parser.add_argument('-t', '--notime', action='store_false', default=True,
                        help='Do not read time-offset based spans from video annotations (default: %(default)s)')
    parser.add_argument('-n', '--nochannel', action='store_false', default=True,
                        help='Omit generating optional channel attribute in video justification? (default: %(default)s)')
    parser.add_argument('log_specifications_filename', type=str,
                        help='File containing error specifications')
    parser.add_argument('encodings_filename', type=str,
                        help='File containing list of encoding to modality mappings')
    parser.add_argument('core_documents_filename', type=str,
                        help='File containing list of core documents to be included in the pool')
    parser.add_argument('parent_children_filename', type=str,
                        help='DocumentID to DocumentElementID mappings file')
    parser.add_argument('sentence_boundaries_filename', type=str,
                        help='File containing sentence boundaries')
    parser.add_argument('image_boundaries_filename', type=str,
                        help='File containing image bounding boxes')
    parser.add_argument('video_boundaries_filename', type=str,
                        help='File containing length of videos')
    parser.add_argument('keyframe_boundaries_filename', type=str,
                        help='File containing keyframe bounding boxes')
    parser.add_argument('type_mappings_filename', type=str,
                        help='File containing type mappings')
    parser.add_argument('slot_mappings_filename', type=str,
                        help='File containing slot mappings')
    parser.add_argument('annotations', type=str,
                        help='Directory containing annotations package as received from LDC')
    parser.add_argument('output', type=str,
                        help='Specify a directory to which output should be written')
    # parse the argument and call main
    args = parser.parse_args()
    main(args)