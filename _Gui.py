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
import tkinter as tk
import tkinter.messagebox as mbox
import tkinter.ttk as ttk
from operator import setitem
from queue import Queue, Empty
from tkinter.filedialog import askdirectory, asksaveasfilename
from typing import Optional

from _ePubMaker import EPubMaker

COLOR_ERROR = "red"
COLOR_NORMAL = "black"
UPDATE_TIME = 100


def validate(condition, entry, result):
    if not condition:
        entry.config(highlightbackground=COLOR_ERROR)
        return result
    else:
        entry.config(highlightbackground=COLOR_NORMAL)


class MainFrame(tk.Frame):
    def __init__(self, _master, input_dir=None, file=None, name="", author=None, publisher=None, language="pt-BR", reversed_mode=False):
        tk.Frame.__init__(self, master=_master, width=525, height=215)
        self.master.protocol("WM_DELETE_WINDOW", self.close)
        self.generic_queue = Queue()
        self.progress_queue = Queue()

        if input_dir and os.path.isdir(input_dir):
            self.input_dir = input_dir
            self.input_dir_var = tk.StringVar(value=self.input_dir)
        else:
            self.input_dir = None
            self.input_dir_var = tk.StringVar(value="No directory given")
            
        self.file = file
        self.working = False
        self.thread: Optional[EPubMaker] = None
        self.showerror = mbox.showerror

        self.master.title("EPUB maker")

        panel = tk.Frame()
        panel.place(in_=self, anchor="c", relx=.5, rely=.5)

        # Directory
        self.input_dir_entry = tk.Entry(panel, state='readonly', textvariable=self.input_dir_var, width=50)
        self.input_dir_entry.grid(row=0, column=0, padx=5)

        self.button_dir = tk.Button(panel, text="Change directory", command=self.get_dir, width=15)
        self.button_dir.grid(row=0, column=1, padx=5, pady=3)

        # File
        self.file_var = tk.StringVar(value=self.file)
        self.file_entry = tk.Entry(panel, state='readonly', textvariable=self.file_var, width=50)
        self.file_entry.grid(row=1, column=0, padx=5)

        self.button_file = tk.Button(panel, text="Change file", command=self.save_as, width=15)
        self.button_file.grid(row=1, column=1, padx=5, pady=3)

        # Name
        name_frame = tk.Frame(panel)
        name_frame.grid(row=2, column=0, columnspan=2, pady=3)
        tk.Label(name_frame, text="Name:").grid(row=0, column=0)
        self.name = tk.StringVar(value=name)
        self.name_entry = tk.Entry(name_frame, textvariable=self.name, validate="key", width=50)
        self.name_entry.grid(row=0, column=1, padx=5)

        # Metadata
        metadata_frame = tk.Frame(panel)
        metadata_frame.grid(row=3, column=0, columnspan=2, pady=3)
        tk.Label(metadata_frame, text="Author:").grid(row=0, column=0)
        self.author = tk.StringVar(value=author)
        self.author_entry = tk.Entry(metadata_frame, textvariable=self.author, validate="key", width=25)
        self.author_entry.grid(row=0, column=1, padx=5)
        tk.Label(metadata_frame, text="Publisher:").grid(row=0, column=2)
        self.publisher = tk.StringVar(value=publisher)
        self.publisher_entry = tk.Entry(metadata_frame, textvariable=self.publisher, validate="key", width=25)
        self.publisher_entry.grid(row=0, column=3, padx=5)

        # Options
        options_frame = tk.Frame(panel)
        options_frame.grid(row=5, column=0, columnspan=2, pady=3)
        self.reversed_mode = tk.BooleanVar(value=reversed_mode)
        self.reversed_mode_entry = tk.Checkbutton(options_frame, text="Reversed mode", variable=self.reversed_mode)
        self.reversed_mode_entry.grid(row=0, column=3, padx=5)
        tk.Label(options_frame, text="Language:").grid(row=0, column=4)
        self.language = tk.StringVar(value=language)
        languages_list = ["pt-BR", "en-US", "ja-JP"]
        self.language_entry = tk.OptionMenu(options_frame, self.language, *languages_list)
        self.language_entry.grid(row=0, column=5, padx=5)

        # Progress
        progress = tk.Frame(panel)
        progress.grid(row=6, column=0, columnspan=2, pady=3)
        self.button_start = tk.Button(progress, text="Start", command=self.start, width=10)
        self.button_start.grid(row=0, column=0, padx=5, pady=3)

        self.progress = ttk.Progressbar(progress, length=200, mode='determinate', name='progress of making the ePub')
        self.progress.grid(row=0, column=1, padx=5, pady=3)

        self.button_stop = tk.Button(progress, text="Stop", command=self.stop, width=10)
        self.button_stop.grid(row=0, column=2, padx=5, pady=3)

        self.set_state()

        self.pack(expand=True)

        self.after(UPDATE_TIME, self.process_queue)

    def get_dir(self):
        self.input_dir = askdirectory(master=self)
        self.input_dir_var.set(self.input_dir or "No directory given")
        self.set_state()

    def save_as(self):
        self.file = asksaveasfilename(defaultextension='.epub')
        self.file_var.set(self.file or "No output file given")
        self.set_state()

    def get_invalid(self):
        author = self.author.get()
        publisher = self.publisher.get()
        result = [
            validate(self.input_dir and os.path.isdir(self.input_dir), self.input_dir_entry, "input directory"),
            validate(self.file, self.file_entry, "ouput file"),
            validate(self.name.get(), self.name_entry, "name"),
            validate(not author or author, self.author_entry, "author"),
            validate(not publisher or publisher, self.publisher_entry, "publisher"),
            validate(self.language.get(), self.language_entry, "language"),
        ]
        
        return list(filter(None, result))

    def set_state(self):
        state = tk.DISABLED if self.working else tk.NORMAL
        self.button_dir.config(state=state)
        self.button_file.config(state=state)
        self.name_entry.config(state=state)
        self.reversed_mode_entry.config(state=state)
        self.button_stop.config(state=tk.NORMAL if self.working else tk.DISABLED)
        self.button_start.config(state=tk.NORMAL if not self.working else tk.DISABLED)
        return True

    def start(self):
        invalid = self.get_invalid()
        if not invalid:
            self.working = True
            self.thread = EPubMaker(
                master=self, input_dir=self.input_dir, file=self.file, name=self.name.get(), 
                author=self.author.get(), publisher=self.publisher.get(), language=self.language.get(), reversed_mode=self.reversed_mode.get(),
                                    )
            self.thread.start()
        else:
            mbox.showerror(
                "Invalid input",
                f"Please check the following field{'s' if 1 < len(invalid) else ''}: the {', the '.join(invalid)}"
            )
        self.set_state()

    def stop(self, value=0):
        if self.thread:
            self.thread.stop()
            self.thread.join()
            self.thread = None
            self.working = False
            self.clear_progress_queue()
            self.progress["maximum"] = 1
            self.progress["value"] = value
        self.set_state()

    def clear_progress_queue(self):
        last = None
        try:
            while True:
                last = self.progress_queue.get_nowait()
        except Empty:
            return last

    def progress_set_maximum(self, maximum):
        self.generic_queue.put(lambda: setitem(self.progress, "maximum", maximum))
        self.clear_progress_queue()

    def progress_set_value(self, value):
        self.progress_queue.put(lambda: setitem(self.progress, "value", value))

    def close(self):
        self.stop()
        self.master.destroy()

    def process_queue(self):
        try:
            while True:
                self.generic_queue.get_nowait()()
        except Empty:
            pass
        last = self.clear_progress_queue()
        if last is not None:
            last()
        self.after(UPDATE_TIME, self.process_queue)


def start_gui(input_dir=None, file=None, name="", author=None, publisher=None, language="pt-BR", reversed_mode=False):
    root = tk.Tk()
    MainFrame(
        root, input_dir=input_dir, file=file, name=name, author=author, publisher=publisher, language=language, reversed_mode=reversed_mode).mainloop()


if __name__ == "__main__":
    start_gui()
