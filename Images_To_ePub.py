''' Convert a folder with images to an ePub file. Great for comics and manga!
    Copyright (C) 2014  Antoine Veenstra

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
'''
import os
from optparse import OptionParser
from _ePubMaker import EPubMaker, CmdProgress

if __name__ == '__main__':
	parser = OptionParser(usage='usage: %prog [-c,-p] [-d,--dir] DIRECTORY [-f,--file] FILE [-n,--name] NAME\n'+        '   or: %prog [-p] DIRECTORY DIRECTORY ... (batchmode, implies -c)')
	parser.add_option('-c','--cmd',action='store_true',dest='cmd',default=False,
						help='Start without gui')
	parser.add_option('-p','--progress',action='store_true',dest='progress',
						default=False,help='Show a nice progressbar (no effect with when combined with the gui)')
	parser.add_option('-d','--dir',dest='dir', metavar='DIRECTORY',
						help='DIRECTORY with the images')
	parser.add_option('-f','--file',dest='file', metavar='FILE',
						help='FILE where the ePub is stored')
	parser.add_option('-n','--name',dest='name',default='',metavar='NAME',
						help='NAME of the book')
	(options, args) = parser.parse_args()
	
	if len(args) > 1 and not options.dir and not options.file and not options.name\
	and all(os.path.isdir(elem) for elem in args):
		for elem in args:
			head, tail = os.path.split(args)
			if not tail:
				dir = head
				tail = os.path.basename(head)
			else:
				dir = args
			creator = EPubMaker(None,dir,dir+'.epub',tail,progress=CmdProgress(options.progress))
			creator.run()
	else:
		if not options.dir and args:
			options.dir = args.pop(0)
		if not options.file and args:
			options.file = args.pop(0)
		if not options.name and args:
			options.name = args.pop(0)
			
		if options.cmd:
			if args or not options.dir or not options.file or not options.name:
				parser.print_help()
			else:
				creator = EPubMaker(None,options.dir,options.file,options.name,progress=CmdProgress(options.progress))
				creator.run()
		else:
			import _Gui
			_Gui.start_Gui(dir=options.dir,save_file=options.file,str_name=options.name)
			