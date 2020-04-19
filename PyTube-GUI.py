from tkinter import (
    Tk,
    Label,
    Entry,
    Scrollbar,
    Button,
    OptionMenu,
    Listbox,
    StringVar, 
    messagebox
)
from tkinter.filedialog import askdirectory
from os.path import exists, split, splitext
from urllib.error import HTTPError
from re import sub, findall
from subprocess import run
from html import unescape
from functools import wraps

from pydub import AudioSegment
from pytube import YouTube
from validators import url

#Todo:
#Webm support / no ".mp4" hardcodes
#learn how to fix pytube myself when it breaks =(

class PytubeGUI:
    """
        Minimalist GUI for pytube
    """

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
            "Audio Only",
            "HQ"
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
            command=self.submit
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

        #HQ mode widgets:
        self.stream_list_y_scroll = Scrollbar(
            self.master,
            orient="vertical"
        )

        self.stream_list = Listbox(
            self.master,
            yscrollcommand=self.stream_list_y_scroll.set
        )

        self.stream_list_y_scroll.config(command=self.stream_list.yview)
        self.stream_selection = StringVar(self.master)

        #Layout:
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(5, weight=1)

        self.link_entry.grid(row=0, column=0, sticky="ew")
        self.link_entry_x_scroll.grid(row=1, column=0, sticky="ew")
        self.link_entry_button.grid(row=0, column=1)
        self.mode_label.grid(row=1, column=1, sticky="ew")
        self.mode_menu.grid(row=2, column=1)
        self.status_label.grid(row=2, column=0)
        self.dir_entry.grid(row=3, column=0, sticky="ew")
        self.dir_entry_x_scroll.grid(row=4, column=0, sticky="ew")
        self.dir_entry_button.grid(row=3, column=1)    

        #Bindings, Traces, Protocols:
        self.link_entry.bind("<Return>", self.submit)
        self.stream_list.bind("<Return>", self.update_stream_selection)
        self.stream_list.bind("<Double-Button-1>", self.update_stream_selection)
        self.mode.trace("w", self.set_gui)
        self.master.bind("<Control-w>", self.close)
        self.master.protocol("WM_DELETE_WINDOW", self.close)


    def __str__(self):
        """
            Pretty print self w/ address
        """
        
        return f"PyTube-GUI @ {hex(id(self))}"


    def set_gui(self, *args):
        """
            Swap between GUI layouts (Stream list / No stream list)
        """

        if self.mode.get() == "HQ":
            self.master.resizable(width=True, height=True)
            self.master.geometry("450x250")
            self.stream_list.grid(row=5,column=0, columnspan=2, sticky="nsew")
            self.master.resizable(width=True, height=False)
        else:
            self.master.resizable(width=True, height=True)
            self.master.geometry("450x125")
            self.stream_list.grid_remove()
            self.master.resizable(width=True, height=False)


    def hq_download(self, yt_vid, directory):
        """
            Slower download rate on average, higher resolution + ffmpeg zip
        """
        
        self.update_status_label("Select Stream")
        self.stream_list.delete(0,"end")
        
        streams = yt_vid.streams.filter(
            adaptive=True,
            type="video",
            subtype="mp4"
        )

        for stream in streams:
            self.stream_list.insert("end",stream)

        self.master.update()
        self.master.wait_variable(self.stream_selection)

        if self.stream_selection.get() == "__NONE__":
            return self.stream_selection.get()

        itag = findall("itag=\"\d*\"", self.stream_selection.get())
        itag = sub("itag=\"|\"","",itag[0])

        hq_stream = yt_vid.streams.get_by_itag(itag)

        path = directory + "/" + clean_file_name(unescape(hq_stream.title)) + ".mp4"
        (filename, full_path) = name_file(path)

        #Try to get video stream first:
        try:
            hq_path = hq_stream.download(directory, filename=filename+" VIDEO")

        except Exception as err:
            messagebox.showwarning("Error", err)
            
        #If we have the video stream, then go for the audio as well:
        if hq_path:
            try:
                audio_path = audio_stream = yt_vid \
                    .streams \
                    .filter(only_audio=True, subtype="mp4") \
                    .order_by("abr") \
                    .desc() \
                    .first() \
                    .download(directory, filename=filename+" AUDIO")

            except Exception as err:
                messagebox.showwarning("Error", err)
            
        print(full_path)
        #If we get here with both, zip them:
        if hq_path and audio_path:
            run([
                f"ffmpeg",
                "-i",
                hq_path,
                "-i",
                audio_path,
                "-codec",
                "copy",
                full_path
            ])

            run(["del", hq_path],shell=True)
            run(["del", audio_path],shell=True)


    def download(self, yt_vid, directory):
        """
            Quicker download, lower resolution
        """

        stream = yt_vid.streams.filter(
            progressive="True",
            file_extension="mp4"
        ).first()

        path = directory + "/" + clean_file_name(unescape(stream.title)) + ".mp4"
        (filename, full_path) = name_file(path)

        try:
            stream.download(directory, filename=filename)

        except Exception as err:
            messagebox.showwarning("Error", err)

        else:
            if self.mode.get() == "Audio Only":
                #Audio only streams download rather slowly via pytube,
                #therefore, we take the audio in place w/ pydub & ffmpeg:
                self.update_status_label("Extracting Audio...")
                audio = AudioSegment.from_file(full_path)
                audio.export(full_path, format="mp4")


    def disabled_ui(fn):
        """
            Wrapper for submit() that prevents accidental repeat downloads.

            If we spam click submit, we'll end up with a bunch of duplicates, which
            probably isn't desirable. 
        """

        @wraps(fn)
        def inner(self, *args, **kwargs):

            self.link_entry_button.config(state="disabled")

            fn(self, *args, **kwargs)

            self.update_status_label("Ready")
            self.stream_list.delete(0,"end")
            self.link_entry.delete(0, "end")
            self.link_entry_button.config(state="normal")
        
        return inner


    @disabled_ui
    def submit(self):
        """
            Controller/handler for download() & hq_download()
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
        except KeyError as err:
            return messagebox.showwarning("KeyError", err)

        except Exception as err:
            #Same as above, capture & return
            return messagebox.showwarning(
                "Invalid Link",
                f"Unable to fetch video.\n{err}"
            )
            
        yt_vid.register_on_progress_callback(self.progress)

        directory = self.dir_entry.get() or self.dir_select()
        if not directory:
            self.update_status_label("Ready")
            return
        if not exists(directory):
            return messagebox.showwarning(
                "Invalid Path",
                "The specified directory cannot be found."
            )

        if self.mode.get() == "HQ":
            result = self.hq_download(yt_vid, directory)
            if result == "__NONE__":
                return
        else:
            self.download(yt_vid, directory)


    def close(self, event=None):
        """
            Callback for window close, satisfies wait_variable()
            before killing the application.
        """
        
        self.stream_selection.set("__NONE__")
        raise SystemExit


    def update_stream_selection(self,*args):
        """
            Callback for Double-Click / Enter key on stream_list.
            Serves to unblock wait_variable in hq_download()
        """

        self.stream_selection.set(
            self.stream_list.get(self.stream_list.curselection())
        )


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


    def progress(self, stream, chunk, bytes_remaining):
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
        Returns a string free of characters restricted for Windows (and ffmpeg).
    """

    return sub("\\\\|/|:|\*|\?|\"|'|>|<|\.|\|","", file_name)


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
