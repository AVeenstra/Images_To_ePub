""" Convert a folder with images to an ePub file. Great for comics and manga!
    Copyright (C) 2021  Antoine Veenstra

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see [http://www.gnu.org/licenses/]
"""
import os
from optparse import OptionParser
from pathlib import Path

from _ePubMaker import EPubMaker, CmdProgress

if __name__ == '__main__':
    parser = OptionParser(
        usage='usage: %prog [--cmd] [--progress] --dir DIRECTORY --file FILE --name NAME\n'
              '   or: %prog [--progress] DIRECTORY DIRECTORY ... (batchmode, implies -c)'
    )
    parser.add_option(
        '-c', '--cmd', action='store_true', dest='cmd', default=False, help='Start without gui'
    )
    parser.add_option(
        '-p', '--progress', action='store_true', dest='progress', default=False,
        help='Show a nice progressbar (cmd only)'
    )
    parser.add_option(
        '-d', '--dir', dest='input_dir', metavar='DIRECTORY', help='DIRECTORY with the images'
    )
    parser.add_option(
        '-f', '--file', dest='file', metavar='FILE', help='FILE where the ePub is stored'
    )
    parser.add_option(
        '-n', '--name', dest='name', default='', metavar='NAME', help='NAME of the book'
    )
    parser.add_option(
        '-g', '--grayscale', dest='grayscale', default=False, action='store_true',
        help="Convert all images to black and white before adding them to the ePub.",
    )
    parser.add_option(
        '-W', '--max-width', dest='max_width', default=None, type="int",
        help="Resize all images to have the given maximum width in pixels."
    )
    parser.add_option(
        '-H', '--max-height', dest='max_height', default=None, type="int",
        help="Resize all images to have the given maximum height in pixels."
    )
    parser.add_option(
        '--wrap-pages', dest='wrap_pages', action='store_true',
        help="Wrap the pages in a separate file. Results will vary for each reader. (Default)"
    )
    parser.add_option(
        '--no-wrap-pages', dest='no_wrap_pages', action='store_true',
        help="Do not wrap the pages in a separate file. Results will vary for each reader."
    )
    (options, args) = parser.parse_args()

    if options.wrap_pages and options.no_wrap_pages:
        parser.error("options --wrap-pages and --no-wrap-pages are mutually exclusive")

    if not options.input_dir and not options.file and not options.name:
        if not all(os.path.isdir(elem) for elem in args):
            parser.error("Not all given arguments are directories!")

        directories = []
        for elem in args:
            path = Path(args)
            if not path.is_dir():
                parser.error(f"The following path is not a directory: {path}")
            if not path.name:
                parser.error(f"Could not get the name of the directory: {path}")
            directories.append(path)

        for path in directories:
            EPubMaker(
                master=None, input_dir=path, file=path.parent.joinpath(path.name + '.epub'), name=path.name or "Output",
                grayscale=options.grayscale, max_width=options.max_width, max_height=options.max_height,
                progress=CmdProgress(options.progress), wrap_pages=not options.no_wrap_pages
            ).run()
    elif options.input_dir and options.file and options.name:
        if options.cmd:
            if args or not options.input_dir or not options.file or not options.name:
                parser.error("The '--dir', '--file', and '--name' arguments are required.")

            EPubMaker(
                master=None, input_dir=options.input_dir, file=options.file, name=options.name,
                grayscale=options.grayscale, max_width=options.max_width,
                max_height=options.max_height, progress=CmdProgress(options.progress),
                wrap_pages=not options.no_wrap_pages
            ).run()
        else:
            import _Gui

            _Gui.start_gui(input_dir=options.input_dir, file=options.file, name=options.name,
                           grayscale=options.grayscale, max_width=options.max_width, max_height=options.max_height,
                           wrap_pages=not options.no_wrap_pages)
    else:
        parser.print_help()
