# coding=utf-8
import tempfile, os, threading, zipfile, datetime, traceback, struct, imghdr, math
import tkinter as tk, tkinter.ttk as ttk, tkinter.messagebox as mbox
from tkinter.filedialog import askdirectory, asksaveasfilename
from optparse import OptionParser

media_types = {'.png':'image/png','.jpg':'image/jpeg','.gif':'image/gif'}

class main_frame(tk.Frame):
	def __init__(self,_master,dir=None,save_file=None,str_name=""):
		tk.Frame.__init__(self,master=_master,width=500,height=150)
		
		if dir and os.path.isdir(dir):
			self.input_dir = dir
			self.dir_entry = tk.StringVar(value=self.input_dir)
		else:
			self.input_dir = None
			self.dir_entry = tk.StringVar(value="No directory given")
		self.save_file = save_file
		self.working = False
		self.thread = None
		
		self.master.title("EPUB maker")
		
		panel = tk.Frame()
		panel.place(in_=self,anchor="c",relx= .5, rely=.5)
		
		# directory
		
		temp = tk.Entry(panel,state='readonly',textvariable=self.dir_entry)
		temp.grid(row=0,column=0,padx=5)
		temp.config(width=50)
		
		self.button_dir = tk.Button(panel,text="Change directory",command=self.getDir)
		self.button_dir.config(width=15)
		self.button_dir.grid(row=0,column=1,padx=5,pady=3)
		
		# file
		if self.save_file:
			self.file_entry = tk.StringVar(value=self.save_file)
		else:
			self.file_entry = tk.StringVar(value="No output file given")
		
		temp = tk.Entry(panel,state='readonly',textvariable=self.file_entry)
		temp.grid(row=1,column=0,padx=5)
		temp.config(width=50)
		
		self.button_file = tk.Button(panel,text="Change file",command=self.save_as)
		self.button_file.config(width=15)
		self.button_file.grid(row=1,column=1,padx=5,pady=3)
		
		# name
		name = tk.Frame(panel)
		name.grid(row=2,column=0,columnspan=2,pady=3)
		tk.Label(name,text="Name:").grid(row=0,column=0)
		self.name = tk.StringVar(value='')
		self.name_entry = tk.Entry(name,textvariable=self.name,validate="key",validatecommand=(self.master.register(self.set_state),'%P'))
		self.name_entry.config(width=30)
		self.name_entry.grid(row=0,column=1)
		
		# progress
		progress = tk.Frame(panel)
		progress.grid(row=3,column=0,columnspan=2,pady=3)
		self.button_start = tk.Button(progress,text="Start",command=self.start)
		self.button_start.config(width=10)
		self.button_start.grid(row=0,column=0,padx=5,pady=3)
		
		self.progress = ttk.Progressbar(progress,length=200, mode='determinate',name='progress of making the ePub')
		self.progress.grid(row=0,column=1,padx=5,pady=3)
		
		self.button_stop = tk.Button(progress,text="Stop",command=self.stop)
		self.button_stop.config(width=10)
		self.button_stop.grid(row=0,column=2,padx=5,pady=3)
		
		self.name.set(str_name)
		
		self.set_state()
		
		self.pack(expand=True)
		
	def getDir(self):
		self.input_dir = askdirectory(master=self)
		if self.input_dir:
			self.dir_entry.set(self.input_dir)
		else:
			self.dir_entry.set("No directory given")
		self.set_state()
		
	def save_as(self):
		self.save_file = asksaveasfilename(defaultextension='.epub')
		if self.save_file:
			self.file_entry.set(self.save_file)
		else:
			self.file_entry.set("No output file given")
		self.set_state()
		
	def createEpub(self):
		tempDir = tempfile.TemporaryDirectory(prefix="EPUB_")
		os.path.join(tempDir.name,nameofoutputfile)
		tempDir.cleanup()
		
	def set_state(self,value=0):
		if value == 0:
			value = self.name.get()
			
		if self.working:
			self.button_dir.config(state=tk.DISABLED)
			self.button_file.config(state=tk.DISABLED)
			self.name_entry.config(state=tk.DISABLED)
			self.button_start.config(state=tk.DISABLED)
			self.button_stop.config(state=tk.ACTIVE)
			
		else:
			self.button_dir.config(state=tk.ACTIVE)
			self.button_file.config(state=tk.ACTIVE)
			self.name_entry.config(state=tk.NORMAL)
			self.button_stop.config(state=tk.DISABLED)
			
			if not self.input_dir or not self.save_file or not value:
				self.button_start.config(state=tk.DISABLED)
			else:
				self.button_start.config(state=tk.ACTIVE)
			
		return True
			
	def start(self):
		if self.input_dir and self.save_file and self.name.get():
			self.working = True
			self.thread = EpubMaker(self,self.input_dir,self.save_file,self.name.get())
			self.thread.start()
		else:
			mbox.showerror("Missing values", "Enter all values")
		self.set_state()
		
	def stop(self):
		if self.thread:
			self.thread.stop()
		self.set_state()
		
class EpubMaker(threading.Thread):
	def __init__(self,master,dir,file,name,progress=None):
		threading.Thread.__init__(self)
		self.master = master
		if self.master:
			self.progress = master.progress
		elif progress:
			self.progress = progress
		else:
			self.progress = None
		self.dir = dir
		self.file = file
		self.name = name
		self.picture_at = 1
		self.stop_event = threading.Event()
		
	def run(self):
		try:
			if not os.path.isdir(self.dir):
				raise Exception("The given directory does not exist!")
			if not self.name:
				raise Exception("No name given!")
			self.make_epub()
			if not self.master:
				print("ePub created")
				
		except Exception as e:
			if not isinstance(e,StopException):
				if self.master:
					mbox.showerror("Error encountered", "The following error was thrown:\n%s\nDon't forget to delete the incomplete file!"%str(e))
				else:
					print("Error encountered:")
					traceback.print_exc()
					print("Don't forget to delete the incomplete file! (if it was created)")
					
		if self.master:
			self.master.working = False
			self.master.thread = None
			self.master.set_state()
			
	def make_epub(self):
		with zipfile.ZipFile(self.file,mode='w') as self.zip,\
		tempfile.TemporaryDirectory(prefix='ePub_') as self.tdir:
			with open(os.path.join(self.tdir,'content.opf'),'w') as self.content,\
				 open(os.path.join(self.tdir,'toc.ncx')    ,'w') as self.toc:
				self.ncx = []
				self.make_mimetype()
				self.make_META()
				self.make_css()
				self.open_content_toc()
				self.search_cover()
				self.make_tree()
				self.close_content_toc()
			self.zip.write(os.path.join(self.tdir,'content.opf'),'OEBPS\\content.opf')
			self.zip.write(os.path.join(self.tdir,'toc.ncx'),'OEBPS\\toc.ncx')
				
		if self.progress:
			self.progress['value'] = self.progress['maximum']
			
	def make_mimetype(self):
		self.zip.writestr('mimetype','application/epub+zip')
		
	def make_META(self):
		self.zip.writestr('META-INF\\container.xml','''<?xml version='1.0' encoding='utf-8'?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile media-type="application/oebps-package+xml" full-path="OEBPS/content.opf"/>
  </rootfiles>
</container>''')
		
	def make_css(self):
		self.zip.writestr('OEBPS\\stylesheet.css','''body
{
	margin:0pt;
	padding:0pt;
	text-align:center;
}
''')
		
	def make_tree(self):
		walker = os.walk(self.dir,onerror=self.throw_error)
		root, dirs, files = walker.send(None)
		walker.close()
		
		dirs = sorted(dirs)
		files = self.get_images(sorted(files),root)
		
		if self.progress:
			self.progress['maximum'] = len(dirs) + 2
			self.progress['value'] = 0
			
		counter = 1
		
		for sub_dir in dirs:
			if self.progress:
				self.progress['value'] = counter
				
			walker = os.walk(os.path.join(root,sub_dir),onerror=self.throw_error)
			sub_files = []
			for sub in walker:
				if self.stopped():
					return
				sub_files.extend(self.get_images(sorted(sub[2]),sub[0]))
			walker.close()
			chapter = open(os.path.join(self.tdir,'chapter%s.xhtml'%counter),'w')
			chapter.write('''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
		<link href="stylesheet.css" rel="stylesheet" type="text/css"/>
		<title>Chapter %s</title>
	</head>
	<body>
		<div>''' % counter)
			for image in sub_files:
				chapter.write('''
			<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="100%%" height="100%%" viewBox="0 0 %(width)s %(height)s" preserveAspectRatio="none">
				<image width="%(width)s" height="%(height)s" xlink:href="images/%(filename)s"/>
			</svg>'''%image)
			chapter.write('''
		</div>
	</body>
</html>
''')
			chapter.close()
			self.zip.write(os.path.join(self.tdir,'chapter%s.xhtml'%counter),'OEBPS\\chapter%s.xhtml'%counter)
			self.content.write('''
		<item id="chapter%(counter)s" href="chapter%(counter)s.xhtml" media-type="application/xhtml+xml"/>'''%{'counter':counter})
			self.ncx.append('\n\t\t<itemref idref="chapter%s" />'%counter)
			self.toc.write('''
	<navPoint id="chapter%(counter)s" playOrder="%(number)s">
		<navLabel>
			<text>%(title)s</text>
		</navLabel>
		<content src="chapter%(counter)s.xhtml"/>
	</navPoint>'''%{'counter':counter,'number':len(self.ncx),'title':sub_dir})
			counter+=1
			
		if self.progress:
			self.progress['value'] = counter
			
		if files:
			chapter = open(os.path.join(self.tdir,'leftover.xhtml'),'w')
			chapter.write('''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
		<link href="stylesheet.css" rel="stylesheet" type="text/css"/>
		<title>Leftovers</title>
	</head>
	<body>
		<div>''')
			for image in files:
				chapter.write('''
			<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="100%%" height="100%%" viewBox="0 0 %(width)s %(height)s" preserveAspectRatio="none">
				<image width="%(width)s" height="%(height)s" xlink:href="images/%(filename)s"/>
			</svg>'''%image)
			chapter.write('''
		</div>
	</body>
</html>
''')
			chapter.close()
			self.zip.write(os.path.join(self.tdir,'leftover.xhtml'),'OEBPS\\chapter%s.xhtml'%counter)
			self.content.write('''
			<item id="leftover" href="leftover.xhtml" media-type="application/xhtml+xml"/>''')
			self.ncx.append('\n\t\t<itemref idref="leftover" />')
			self.toc.write('''
	<navPoint id="leftover" playOrder="%s">
		<navLabel>
			<text>Leftovers</text>
		</navLabel>
		<content src="leftover.xhtml"/>
	</navPoint>'''%len(self.ncx))
			
	def search_cover(self):
		walker = os.walk(self.dir,onerror=self.throw_error)
		for sub in walker:
			if self.stopped():
				return
			for x in self.get_images(sorted(sub[2])):
				if 'cover' in x.lower():
					filename = 'cover'+x[x.rfind('.'):]
					self.zip.write(os.path.join(sub[0],x),'OEBPS\\images\\'+filename)
					width,height = self.get_image_size(os.path.join(sub[0],x))
					self.zip.writestr('OEBPS\\cover.xhtml','''<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en">
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
		<meta name="calibre:cover" content="true"/>
		<link href="stylesheet.css" rel="stylesheet" type="text/css"/>
		<title>Cover</title>
	</head>
	<body>
		<div>
			<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" width="100%%" height="100%%" viewBox="0 0 %(width)s %(height)s" preserveAspectRatio="none">
				<image width="%(width)s" height="%(height)s" xlink:href="images/%(filename)s"/>
			</svg>
		</div>
	</body>
</html>
'''%{'width':width,'height':height,'filename':filename})
					root, extension = os.path.splitext(x)
					filetype = media_types.get(extension)
					self.content.write('''
		<item id="%(filename)s" href="images/%(filename)s" media-type="%(type)s"/>
		<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>'''%{'filename':filename,'type':filetype})
					self.ncx.append('\n\t\t<itemref idref="cover" />')
					self.toc.write('''
	<navPoint id="cover" playOrder="1">
		<navLabel>
			<text>Cover Page</text>
		</navLabel>
		<content src="cover.xhtml"/>
	</navPoint>''')
					return True
		walker.close()
		return False
		
	def get_images(self,files,root=None):
		result = []
		for x in files:
			if self.stopped():
				return
			ignore, extension = os.path.splitext(x)
			file_type = media_types.get(extension)
			if file_type:
				if root:
					file_name = str(self.picture_at)+extension
					self.zip.write(os.path.join(root,x),'OEBPS\\images\\'+file_name)
					self.content.write('\n\t\t<item id="image%(id)s" href="images/%(name)s" media-type="%(type)s"/>'%{'id':self.picture_at,'name':file_name,'type':file_type})
					width,height = self.get_image_size(os.path.join(root,x))
					result.append({'filename':file_name,'width':width,'height':height})
					self.picture_at += 1
				else:
					result.append(x)
		return result
		
	def open_content_toc(self):
		uuid = 'bookmadeon' + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
		self.content.write('''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookID" version="2.0" >
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
        <dc:title>%s</dc:title>
        <dc:language>en-US</dc:language>
        <dc:rights>Public Domain</dc:rights>
        <dc:creator opf:role="aut">ePub Creator</dc:creator>
        <dc:publisher>ePub Creator</dc:publisher>
        <dc:identifier id="BookID" opf:scheme="UUID">%s</dc:identifier>
        <meta name="Sigil version" content="0.2.4"/>
    </metadata>
    <manifest>
        <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />
        <item id="style" href="stylesheet.css" media-type="text/css" />''' % (self.name,uuid))
		self.toc.write('''<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">

<head>
    <meta name="dtb:uid" content="%s"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
</head>

<docTitle>
    <text>%s</text>
</docTitle>

<navMap>''' % (uuid,self.name))
		
	def close_content_toc(self):
		self.content.write('''
	</manifest>
	<spine toc="ncx">''')
		
		for line in self.ncx:
			self.content.write(line)
			
		self.content.write('''
	</spine>
</package>''')
		self.toc.write('''
</navMap>
</ncx>''')
		
	def get_image_size(self,fname):
		fhandle = open(fname, 'rb')
		head = fhandle.read(24)
		if len(head) != 24:
			return
		if imghdr.what(fname) == 'png':
			check = struct.unpack('>i', head[4:8])[0]
			if check != 0x0d0a1a0a:
				return
			width, height = struct.unpack('>ii', head[16:24])
		elif imghdr.what(fname) == 'gif':
			width, height = struct.unpack('<HH', head[6:10])
		elif imghdr.what(fname) == 'jpeg':
			try:
				fhandle.seek(0) # Read 0xff next
				size = 2
				ftype = 0
				while not 0xc0 <= ftype <= 0xcf:
					fhandle.seek(size, 1)
					byte = fhandle.read(1)
					while ord(byte) == 0xff:
						byte = fhandle.read(1)
					ftype = ord(byte)
					size = struct.unpack('>H', fhandle.read(2))[0] - 2
				# We are at a SOFn block
				fhandle.seek(1, 1)  # Skip `precision' byte.
				height, width = struct.unpack('>HH', fhandle.read(4))
			except Exception: #IGNORE:W0703
				return
		else:
			return
		return width, height
			
	def stop(self):
		self.stop_event.set()
		
	def stopped(self):
		return self.stop_event.isSet()
		
	def throw_error(self,e):
		raise e
		
class CmdProgress:
	def __init__(self,nice):
		self.width = 60
		self.maximum = 150
		self.value = 0
		self.nice = nice
		
	def __getitem__(self,key):
		if key == "value":
			return self.value
		elif key == "maximum":
			return self.maximum
			
	def __setitem__(self,key,value):
		if key == "value" and isinstance(value,int) and 0 <= value and value <= self.maximum:
			self.value = value
			if self.nice:
				edge = ['','░','▒','▓']
				
				progress = self.value/self.maximum*self.width*3.0
				
				print('┌'+'─'*self.width+'┐')
				print('│'+'▓'*math.floor(progress/3)+edge[math.ceil(progress%3)]+' '*(self.width-math.ceil(progress/3))+'│')
				print('└'+'─'*self.width+'┘')
			else:
				print('At %s/%s'%(self.value,self.maximum))
		elif key == 'maximum' and isinstance(value,int) and 0 <= value:
			self.maximum = value
			
class StopException(Exception):
	def __str__(self):
		return "The ePub creator has been stopped!"
		
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
			creator = EpubMaker(None,dir,dir+'.epub',tail,progress=CmdProgress(options.progress))
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
				creator = EpubMaker(None,options.dir,options.file,options.name,progress=CmdProgress(options.progress))
				creator.run()
		else:
			root = tk.Tk()
			main_frame(root,dir=options.dir,save_file=options.file,str_name=options.name).mainloop()
			