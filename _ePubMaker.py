# coding=utf-8
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

import PIL.Image
from jinja2 import Environment, FileSystemLoader, StrictUndefined

MEDIA_TYPES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.gif': 'image/gif'}
TEMPLATE_DIR = Path(__file__).parent.joinpath("templates")


def natural_keys(text):
    """
    http://nedbatchelder.com/blog/200712/human_sorting.html
    """
    return [(int(c) if c.isdigit() else c) for c in re.split(r'(\d+)', text)]


def filter_images(files):
    files.sort(key=natural_keys)
    for x in files:
        _, extension = os.path.splitext(x)
        file_type = MEDIA_TYPES.get(extension)
        if file_type:
            yield x, file_type, extension


class Chapter:
    def __init__(self, dir_path, title, start: str = None):
        self.dir_path = dir_path
        self.title = title
        self.children: List[Chapter] = []
        self._start = start

    @property
    def start(self) -> Optional[str]:
        if self._start:
            return self._start
        if self.children:
            return self.children[0].start

    @start.setter
    def start(self, value):
        self._start = value

    @property
    def depth(self) -> int:
        if self.children:
            return 1 + max(child.depth for child in self.children)
        return 1


class EPubMaker(threading.Thread):
    def __init__(self, master, input_dir, file, name, wrap_pages, grayscale, max_width, max_height, progress=None):
        threading.Thread.__init__(self)
        self.master = master
        self.progress = None
        if self.master:
            self.progress = master
        elif progress:
            self.progress = progress
        self.dir = input_dir
        self.file = file
        self.name = name
        self.picture_at = 1
        self.stop_event = False

        self.template_env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), undefined=StrictUndefined)

        self.zip: Optional[ZipFile] = None
        self.cover = None
        self.chapter_tree: Optional[Chapter] = None
        self.images = []
        self.uuid = 'urn:uuid:' + str(uuid.uuid1())
        self.grayscale = grayscale
        self.max_width = max_width
        self.max_height = max_height
        self.wrap_pages = wrap_pages

    def run(self):
        try:
            assert os.path.isdir(self.dir), "The given directory does not exist!"
            assert self.name, "No name given!"

            self.make_epub()

            if self.master is None:
                print()
                print("ePub created")
            else:
                self.master.generic_queue.put(lambda: self.master.stop(1))

        except Exception as e:
            if not isinstance(e, StopException):
                if self.master is not None:
                    self.master.generic_queue.put(lambda: self.master.showerror(
                        "Error encountered",
                        "The following error was thrown:\n{}".format(e)
                    ))
                else:
                    print("Error encountered:", file=sys.stderr)
                    traceback.print_exc()
            try:
                if os.path.isfile(self.file):
                    os.remove(self.file)
            except IOError:
                pass

    def make_epub(self):
        with ZipFile(self.file, mode='w', compression=ZIP_DEFLATED) as self.zip:
            self.zip.writestr('mimetype', 'application/epub+zip', compress_type=ZIP_STORED)
            self.add_file('META-INF', "container.xml")
            self.add_file('stylesheet.css')
            self.make_tree()
            self.assign_image_ids()
            self.write_images()
            self.write_template('package.opf')
            self.write_template('toc.xhtml')
            self.write_template('toc.ncx')

    def add_file(self, *path: str):
        self.zip.write(TEMPLATE_DIR.joinpath(*path), os.path.join(*path))

    def make_tree(self):
        root = Path(self.dir)
        self.chapter_tree = Chapter(root.parent, None)
        chapter_shortcuts = {root.parent: self.chapter_tree}

        for dir_path, dir_names, filenames in os.walk(self.dir):
            dir_names.sort(key=natural_keys)
            images = self.get_images(filenames, dir_path)
            dir_path = Path(dir_path)
            chapter = Chapter(dir_path, dir_path.name, images[0] if images else None)
            chapter_shortcuts[dir_path.parent].children.append(chapter)
            chapter_shortcuts[dir_path] = chapter

        while len(self.chapter_tree.children) == 1:
            self.chapter_tree = self.chapter_tree.children[0]

    def get_images(self, files, root):
        result = []
        for x, file_type, extension in filter_images(files):
            data = self.add_image(os.path.join(root, x), file_type, extension)
            result.append(data)
            if not self.cover and 'cover' in x.lower():
                self.cover = data
                data["is_cover"] = True
        return result

    def add_image(self, source, file_type, extension):
        data = {"extension": extension, "type": file_type, "source": source, "is_cover": False}
        self.images.append(data)
        return data

    def assign_image_ids(self):
        if not self.cover and self.images:
            cover = self.images[0]
            cover["is_cover"] = True
            self.cover = cover
        padding_width = len(str(len(self.images)))
        for count, image in enumerate(self.images):
            image["id"] = f"image_{count:0{padding_width}}"
            image["filename"] = image["id"] + image["extension"]

    def write_images(self):
        if self.progress:
            self.progress.progress_set_maximum(len(self.images))
            self.progress.progress_set_value(0)

        template = self.template_env.get_template("page.xhtml.jinja2")

        for progress, image in enumerate(self.images):
            output = os.path.join('images', image["filename"])
            image_data: PIL.Image.Image = PIL.Image.open(image["source"])
            image["width"], image["height"] = image_data.size
            image["type"] = image_data.get_format_mimetype()
            should_resize = (self.max_width and self.max_width < image["width"]) or (
                        self.max_height and self.max_height < image["height"])
            should_grayscale = self.grayscale and image_data.mode != "L"
            if not should_grayscale and not should_resize:
                self.zip.write(image["source"], output)
            else:
                image_format = image_data.format
                if should_resize:
                    width_scale = image["width"] / self.max_width if self.max_width else 1.0
                    height_scale = image["height"] / self.max_height if self.max_height else 1.0
                    scale = max(width_scale, height_scale)
                    image_data = image_data.resize((int(image["width"] / scale), int(image["height"] / scale)))
                    image["width"], image["height"] = image_data.size
                if should_grayscale:
                    image_data = image_data.convert("L")
                with self.zip.open(output, "w") as image_file:
                    image_data.save(image_file, format=image_format)

            if self.wrap_pages:
                self.zip.writestr(os.path.join("pages", image["id"] + ".xhtml"), template.render(image))

            if self.progress:
                self.progress.progress_set_value(progress)
            self.check_is_stopped()
        if self.progress:
            self.progress.progress_set_value(len(self.images))

    def write_template(self, name, *, out=None, data=None):
        out = out or name
        data = data or {
            "name": self.name, "uuid": self.uuid, "cover": self.cover, "chapter_tree": self.chapter_tree,
            "images": self.images, "wrap_pages": self.wrap_pages,
        }
        self.zip.writestr(out, self.template_env.get_template(name + '.jinja2').render(data))

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
