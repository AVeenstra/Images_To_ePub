# coding=utf-8
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
import tempfile, threading, traceback, zipfile, datetime, struct, imghdr, math, os

media_types = {'.png':'image/png','.jpg':'image/jpeg','.gif':'image/gif'}

class EPubMaker(threading.Thread):
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
					print("error",str(e))
					self.master.showerror("Error encountered", "The following error was thrown:\n%s\nDon't forget to delete the incomplete file!"%str(e))
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
		'''Determine the image type of fhandle and return its size.
		from draco'''
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
		
class StopException(Exception):
	def __str__(self):
		return "The ePub creator has been stopped!"
		
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
			