# coding=utf-8
""" Convert a folder with images to an ePub file. Great for Comics and Manga!
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
import math
import os
import re
import sys
import threading
import traceback
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from ebooklib import epub

import PIL.Image
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import mimetypes

TEMPLATE_DIR = Path(__file__).parent.joinpath("templates")


def natural_keys(text):
   
    return [(int(c) if c.isdigit() else c) for c in re.split(r'(\d+)', text)]

class Chapter:
    def __init__(self, dir_path, files=[]):
        self.dir_path = dir_path
        self.title = dir_path.name
        self.files=files
        self.children: List[Chapter] = []

    @property
    def depth(self) -> int:
        if self.children:
            return 1 + max(child.depth for child in self.children)
        return 1

class EPubMaker(threading.Thread):
    def __init__(self, master, input_dir, file:str, name, author=None, publisher=None, language="pt-BR", reversed_mode=False, progress=None):
        threading.Thread.__init__(self)
        self.master = master
        self.progress = None
        if self.master:
            self.progress = master
        elif progress:
            self.progress = progress
        self.dir = input_dir
        self.file = Path(file).with_suffix('.epub').as_posix()
        self.name = name
        self.picture_at = 1
        self.stop_event = False

        self.template_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), undefined=StrictUndefined)

        self.chapter_tree: Optional[Chapter] = None
        self.chapter_shortcuts = {}
        self.uuid = 'urn:uuid:' + str(uuid.uuid1())
        self.author = author
        self.publisher = publisher
        self.language = language
        self.reversed_mode = "rtl" if reversed_mode else "ltr"
        self.image_mode = False

    def run(self):
        try:
            assert os.path.isdir(self.dir), "The given directory does not exist!"
            assert self.name, "No name given!"

            self.create_epub()

            if self.master is None:
                print("ePub created")
            else:
                self.master.generic_queue.put(lambda: self.master.stop(1))

        except Exception as e:
            if not isinstance(e, StopException):
                if self.master is not None:
                    self.master.generic_queue.put(lambda: self.master.showerror(
                        "Error encountered",
                        "The following error was thrown:\n{}".format(str(e))))
                else:
                    print("Error encountered:", file=sys.stderr)
                    traceback.print_exc()
            try:
                if os.path.isfile(self.file):
                    os.remove(self.file)
            except IOError:
                pass

    def create_epub(self):
        
        book = epub.EpubBook()
        book.set_identifier(self.uuid)
        book.set_title(self.name)
        book.set_language(self.language)
        book.add_author(self.author)
        book.add_metadata('DC', 'publisher', self.publisher)
        book.set_direction(self.reversed_mode)
        self.make_tree()


        allcaps=[]
        chapters_infos={}
        list_chapters=list(self.chapter_shortcuts.values())

        if self.progress:
            self.progress.progress_set_maximum(len(list_chapters))
            self.progress.progress_set_value(0)

        for progress, obj in enumerate(list_chapters):

            caps=[]

            if obj.dir_path!=Path(self.dir).parent:

                pos=list_chapters.index(obj)
                verif_obj=obj
                
                while (len(verif_obj.files)==0 or all(Path(file).suffix.lower()=='.epub' for file in verif_obj.files)) and pos<len(list_chapters):
                    pos+=1
                    verif_obj=list_chapters[pos]

                if obj.files:

                    if self.image_mode:


                            nome=os.path.splitext(obj.dir_path.name)[0]
                            cap = epub.EpubHtml(title=nome, file_name=obj.dir_path.with_suffix('.xhtml').name)
                            cap.content=''
                            for file in sorted(obj.files, key=natural_keys):   

                                file=Path(file)
                                file_name=os.path.join(nome, file.name)
                                ext=os.path.splitext(file_name)[-1]
                                if os.path.splitext(file.name)[0]=='cover':
                                    
                                    book.set_cover(nome, open(file, 'rb').read())

                                elif ext in ['.png', '.jpg']:

                                    image = epub.EpubImage(file_name=file_name, content=open(file, "rb").read())
                                    book.add_item(image)
                                    cap.content+='<img src="{}"/>'.format(file_name) 

                            if len(cap.content):
                                book.add_item(cap)
                                caps.append(cap)

                    else:
                        for file in sorted(obj.files, key=natural_keys):

                            file=Path(file)
                            file_name=file.with_suffix('.xhtml').name
                            nome=os.path.splitext(file.name)[0]
                            ext=os.path.splitext(file.name)[-1]

                            if nome=='cover':

                                book.set_cover(nome, open(file, 'rb').read())

                            elif ext in ['.html', '.png', '.jpg']:

                                cap = epub.EpubHtml(title=nome, file_name=file_name)

                                if ext=='.html':   

                                    cap.content = open(file, 'r', encoding='utf-8').read()

                                else:  

                                    image = epub.EpubImage(file_name=file.name, content=open(file, "rb").read())
                                    book.add_item(image)
                                    cap.content ='<img src="{}"/>'.format(file.name) 

                                book.add_item(cap)
                                caps.append(cap)

                if self.image_mode:
                    if len(caps):
                        section=caps
                    else:
                        section=[epub.Section(obj.title, Path(verif_obj.title).with_suffix('.xhtml').name), caps]
                else:
                    section=[epub.Section(obj.title, Path(sorted(verif_obj.files, key=natural_keys)[0]).with_suffix('.xhtml').name), caps]
                allcaps.extend(caps)
                chapters_infos.update({obj.dir_path: section})
                
            if self.progress:
                self.progress.progress_set_value(progress)
            self.check_is_stopped()
      
        if self.progress:
            self.progress.progress_set_value(len(list_chapters))

        infos_copy=chapters_infos.copy()
        for dir_path, section in reversed(chapters_infos.items()):
            if dir_path!=Path(self.dir):
                add=infos_copy.pop(dir_path)
                qnt=len(add)
                if self.image_mode:
                    index=0
                    if qnt==1:
                        add=add[0]
                else:  
                    index=qnt
                infos_copy[dir_path.parent][-1].insert(index, add)
            
        book.toc=list(infos_copy.values())
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        
        # define CSS style
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content="BODY {color: white;}",
                                )
        
        book.add_item(nav_css)
        
        book.spine = ["nav"]+allcaps
        
        epub.write_epub(self.file, book, {})


    def make_tree(self):

        root = Path(self.dir)
        self.chapter_tree = Chapter(root.parent)
        self.chapter_shortcuts = {root.parent: self.chapter_tree}
        allfiles=[]

        for dir_path, dir_names, filenames in os.walk(self.dir):
            allfiles.extend(filenames)
            dir_names.sort(key=natural_keys)
            filesdir = [os.path.join(dir_path, file) for file in filenames]
            dir_path = Path(dir_path)
            chapter = Chapter(dir_path, filesdir)
            self.chapter_shortcuts[dir_path.parent].children.append(chapter)
            self.chapter_shortcuts[dir_path] = chapter

        while len(self.chapter_tree.children) == 1:
            self.chapter_tree = self.chapter_tree.children[0]

        if all('image' in mimetypes.guess_type(file)[0] for file in allfiles if Path(file).suffix.lower()!='.epub'):
            self.image_mode=True

    def stop(self):
        self.stop_event = True

    def check_is_stopped(self):
        if self.stop_event:
            raise StopException()


class StopException(Exception):
    def __str__(self):
        return "The ePub creator has been stopped!"


class CmdProgress:
    def __init__(self, nice):
        self.last_update = datetime.now()
        self.update_interval = timedelta(seconds=0.25)
        self.nice = nice
        self.edges = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
        self.width = 60
        self.maximum = 150
        self.value = 0

    def progress_set_value(self, value):
        self.value = value
        if 0 <= self.value <= self.maximum:
            if self.maximum == self.value or datetime.now() > self.last_update + self.update_interval:
                self.last_update = datetime.now()
                if self.nice:
                    if self.value < self.maximum:
                        progress = self.value / self.maximum * self.width * 8.0
                        done = math.floor(progress / 8)
                        edge = self.edges[int(progress - done * 8)]

                        print('\r│' + '█' * done + edge + ' ' * (self.width - done - 1) + '│ ', end="")
                    else:
                        print('\r│' + '█' * self.width + '│')
                else:
                    print('At {}/{}'.format(self.value, self.maximum))

    def progress_set_maximum(self, value):
        self.maximum = value
        if 0 <= value:
            if self.nice:
                print('\r│' + ' ' * self.width + '│ ', end="")