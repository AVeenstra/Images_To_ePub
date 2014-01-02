import tkinter as tk, tkinter.ttk as ttk, tkinter.messagebox as mbox
from tkinter.filedialog import askdirectory, asksaveasfilename
import os
from _ePubMaker import EPubMaker

class MainFrame(tk.Frame):
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
		self.showerror = mbox.showerror
		
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
			self.thread = EPubMaker(self,self.input_dir,self.save_file,self.name.get())
			self.thread.start()
		else:
			mbox.showerror("Missing values", "Enter all values")
		self.set_state()
		
	def stop(self):
		if self.thread:
			self.thread.stop()
		self.set_state()
		
def start_Gui(dir=None,save_file=None,str_name=""):
	root = tk.Tk()
	# main_frame(root,dir=dir,save_file=save_file,str_name=str_name).mainloop()
	MainFrame(root,dir="C:\\Users\\Antoine\\Downloads\\[complete]\\Manga\\Vagabond [v1-27]\\Vagabond v01",save_file="C:\\Users\\Antoine\\Desktop\\Vagabond v01.epub",str_name="Vagabond v01").mainloop()
	
if __name__ == "__main__":
	start_Gui()