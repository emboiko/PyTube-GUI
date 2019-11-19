from tkinter import (
    Tk,
    Label,
    Entry,
    Scrollbar,
    Button,
    OptionMenu,
    StringVar, 
    messagebox
)
from tkinter.filedialog import askdirectory
from os.path import exists, split, splitext
from urllib.error import HTTPError
from platform import system
from html import unescape
from re import sub

from pydub import AudioSegment
from pytube import YouTube
from validators import url


class PytubeGUI:
    def __init__(self, root):
        self.master = root

        self.master.title("PyTube-GUI")
        self.master.iconbitmap("pylogo.ico")

        self.master.geometry("450x125")
        self.master.minsize(width=450, height=125)
        self.master.resizable(width=True, height=False)
        (width_offset, height_offset) = self.get_offsets()
        self.master.geometry(f"+{width_offset}+{height_offset}")
        self.master.update()

        #Widgets
        self.mode = StringVar(self.master)
        self.mode.set("Video + Audio")

        self.link_entry_x_scroll = Scrollbar(
            self.master,
            orient="horizontal"
        )

        self.link_entry = Entry(
            self.master,
            font="Sans_Serif 12",
            xscrollcommand=self.link_entry_x_scroll.set
        )

        self.link_entry_x_scroll.config(command=self.link_entry.xview)

        self.mode_menu = OptionMenu(
            self.master,
            self.mode,
            "Video + Audio",
            "Audio Only"
        )
        self.mode_menu.config(width=12)

        self.mode_label = Label(
            self.master,
            text="Mode:",
            font="Sans_Serif 10",
        )

        self.status_label = Label(
            self.master,
            text="Ready",
            font="Sans_Serif 12",
            padx=10,
            relief="sunken"
        )

        self.link_entry_button = Button(
            self.master,
            text="Submit",
            width=15,
            command=self.download
        )

        self.dir_entry_x_scroll = Scrollbar(
            self.master,
            orient="horizontal"
        )

        self.dir_entry = Entry(
            self.master,
            font="Sans_Serif 12",
            xscrollcommand=self.dir_entry_x_scroll.set
        )

        self.dir_entry_x_scroll.config(command=self.dir_entry.xview)

        self.dir_entry_button = Button(
            self.master,
            text="Select Directory",
            width=15,
            command=self.dir_select
        )

        #Layout
        self.master.columnconfigure(0, weight=1)

        self.link_entry.grid(row=0, column=0, sticky="ew")
        self.link_entry_x_scroll.grid(row=1, column=0, sticky="ew")
        self.link_entry_button.grid(row=0, column=1)
        self.mode_label.grid(row=1, column=1, sticky="ew")
        self.mode_menu.grid(row=2, column=1)
        self.status_label.grid(row=2, column=0)
        self.dir_entry.grid(row=3, column=0, sticky="ew")
        self.dir_entry_x_scroll.grid(row=4, column=0, sticky="ew")
        self.dir_entry_button.grid(row=3, column=1)    

        self.link_entry.bind("<Return>", self.download)


    def download(self):
        """
            Downloads a youtube video to a directory of the user's choice,
            and if nesseccary, renames the file to avoid overwriting.
        """

        if not self.link_entry.get():
            return
        if not url(self.link_entry.get()):
            messagebox.showwarning(
                "Invalid Input",
                "Input is not a valid URL."
            )
            self.link_entry.selection_range(0,"end")
            return

        self.update_status_label("Fetching")

        try:
            yt_vid = YouTube(self.link_entry.get())
        except Exception as err:
            messagebox.showwarning(
                "Invalid Link",
                "Input is not a valid Youtube URL."
            )
            self.update_status_label("Ready")
            self.link_entry.selection_range(0,"end")
            return

        yt_vid.register_on_progress_callback(self.progress)

        directory = self.dir_entry.get() or self.dir_select()
        if not directory:
            self.update_status_label("Ready")
            return
        if not exists(directory):
            messagebox.showwarning(
                "Invalid Path",
                "The specified directory cannot be found."
            )
            #Maybe create the directory instead?
            self.dir_entry.selection_range(0, "end")
            self.update_status_label("Ready")
            return

        stream = yt_vid.streams.filter(
            progressive="True",
            file_extension="mp4"
        ).first()

        path = directory + "/" + clean_file_name(unescape(stream.title)) + ".mp4"
        (filename, full_path) = name_file(path)

        try:
            stream.download(directory, filename=filename)

        except HTTPError as err:
            messagebox.showwarning(
                "Error",
                f"{err}\n https://github.com/nficano/pytube/issues/399"
            )
        
        except Exception as err:
            messagebox.showwarning(
                "Error",
                f"{err}"
            )

        else:
            if self.mode.get() == "Audio Only":
                self.update_status_label("Extracting Audio...")
                path = directory + "/" + filename
                audio = AudioSegment.from_file(full_path)
                audio.export(full_path, format="mp4")

        finally:
            self.update_status_label("Ready")
            self.link_entry.delete(0, "end")


    def dir_select(self):
        """
            A wrapper for askdirectory() that populates the GUI.
        """

        directory = askdirectory()
        if directory:
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, directory)
            return directory


    def update_status_label(self, status):
        """
            DRYs up two function calls, adds some dynamic behavior.
        """

        self.status_label.config(text=status)
        self.status_label.update()


    def progress(self, stream, chunk, file_handle, bytes_remaining):
        """
            Callback for download progress
        """

        dl_progress = round(
            (100*(stream.filesize - bytes_remaining)) / stream.filesize,
            2
        )

        self.update_status_label(f"Downloading... {dl_progress} %")


    def get_offsets(self):
        """
            Returns an appropriate offset for a given tkinter toplevel,
            such that it always is created center screen on the primary display.
        """

        width_offset = int(
            (self.master.winfo_screenwidth() / 2) - (self.master.winfo_width() / 2)
        )

        height_offset = int(
            (self.master.winfo_screenheight() / 2) - (self.master.winfo_height() / 2)
        )

        return (width_offset, height_offset)


def name_file(full_path):
    """
        Loops while a given path exists, and appends the filename with an index
        wrapped in parenthesis.
    """

    (root, filename) = split(full_path)
    (title, extension) = splitext(filename)
    new_title = title

    filecount = 1
    while exists(full_path):
        filecount += 1
        new_title = title + " (" + str(filecount) + ")"
        full_path = root + "/" + new_title + extension

    return (new_title, full_path)


def clean_file_name(file_name):
    """
        Returns a string free of characters restricted for Windows filenames.
    """

    return sub("\\\\|/|:|\*|\?|\"|'|>|<|\|","", file_name)


def main():
    """
        For now, this is just a tiny GUI that includes some of the basic 
        functionality of both Pytube and Pydub. If a given video fails 
        and returns 403, my best advice is to simply try it with a different 
        link. This occurs most often with a video that YouTube considers "music"
    """

    root = Tk()
    pytube_gui = PytubeGUI(root)
    root.mainloop()


if __name__ == "__main__":

    main()
