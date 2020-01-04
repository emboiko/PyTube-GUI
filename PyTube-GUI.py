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
from platform import system
from re import sub, findall
from subprocess import run
from html import unescape

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

        #Layout
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

        self.link_entry.bind("<Return>", self.submit)


    def hq_download(self, yt_vid, directory):
        """
            Slower download rate on average, higher resolution + ffmpeg zip
        """
        
        self.update_status_label("Select Stream")
        self.master.resizable(width=True, height=True)
        self.master.geometry("450x250")
        self.stream_list.grid(row=5,column=0, columnspan=2, sticky="nsew")
        self.master.resizable(width=True, height=False)

        self.stream_list.bind("<Return>", self.update_stream_selection)
        self.stream_list.bind("<Double-Button-1>", self.update_stream_selection)
        
        streams = yt_vid.streams.filter(adaptive=True, subtype="mp4").all()
        for stream in streams:
            self.stream_list.insert("end",stream)

        self.master.update()
        self.master.wait_variable(self.stream_selection)

        itag = findall("itag=\"\d*\"", self.stream_selection.get())
        itag = sub("itag=\"|\"","",itag[0])

        hq_stream = yt_vid.streams.get_by_itag(itag)

        path = directory + "/" + clean_file_name(unescape(hq_stream.title)) + ".mp4"
        (filename, full_path) = name_file(path)

        try:
            hq_path = hq_stream.download(directory, filename=filename+" VIDEO")
        except HTTPError as err:
            messagebox.showwarning(
                "Error",
                f"{err}\n https://github.com/nficano/pytube/issues/399"
            )
            return
        
        except Exception as err:
            messagebox.showwarning(
                "Error",
                f"{err}"
            )
            return

        try:
            audio_path = audio_stream = yt_vid \
                .streams \
                .filter(only_audio=True, subtype="mp4") \
                .order_by("abr") \
                .desc() \
                .first() \
                .download(directory, filename=filename+" AUDIO")

        except Exception as err:
            messagebox.showwarning(
                "Error",
                f"{err}"
            )
            return
        
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
                #Audio only streams download rather slowly via pytube,
                #therefore, we take the audio in place w/ pydub & ffmpeg:
                self.update_status_label("Extracting Audio...")
                audio = AudioSegment.from_file(full_path)
                audio.export(full_path, format="mp4")


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
            #Not sure what to do here other than just capture & return
            messagebox.showwarning(
                "Error",
                f"{err}\n"
                "https://github.com/nficano/pytube/issues/536\n"\
                "https://github.com/nficano/pytube/pull/537\n"\
                "Sometimes retrying with the same link actually works."
            )
            self.update_status_label("Ready")
            self.link_entry.selection_range(0,"end")
            return

        except Exception as err:
            #Same as above, capture & return
            messagebox.showwarning(
                "Invalid Link",
                "Unable to fetch video."
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

        if self.mode.get() == "HQ":
            self.hq_download(yt_vid, directory)
        else:
            self.download(yt_vid, directory)

        self.stream_list.grid_remove()
        self.stream_list_y_scroll.grid_remove()

        self.master.resizable(width=True, height=True)
        self.master.geometry("450x125")
        self.master.resizable(width=True, height=False)

        self.update_status_label("Ready")
        self.stream_list.delete(0,"end")
        self.link_entry.delete(0, "end")


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

    return sub("\\\\|/|:|\*|\?|\"|'|>|<|\.","", file_name)


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
