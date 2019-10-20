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
from platform import system
from re import sub
from urllib.error import HTTPError
from pytube import YouTube
from pydub import AudioSegment
from validators import url


def get_offset(window_width, window_height):
    """
        Returns an appropriate offset for a given tkinter toplevel,
        such that it always is created center screen on the primary display.
    """

    width_offset=int(
        (master.winfo_screenwidth() / 2) - (window_width / 2)
    )
    height_offset=int(
        (master.winfo_screenheight() / 2) - (window_height / 2)
    )
    return (width_offset, height_offset)


def name_file(full_path):
    """
        Returns a filename stripped of restricted characters,
        and, if necessary, renames the file or directory until 
        it doesn't exist by appending the filename with an index 
        wrapped in parenthesis.
    """

    (root, filename) = split(full_path)
    (title, extension) = splitext(filename)
    title = sub("\\\\|/|:|\*|\?|\"|'|>|<|\|","", title)
    new_title = title

    filecount = 1
    while exists(full_path):
        filecount += 1
        new_title = title + " (" + str(filecount) + ")"
        full_path = root + "/" + new_title + extension

    return (full_path, new_title)


def progress(stream, chunk, file_handle, bytes_remaining):
    """
        Callback for download progress updating.
    """

    dl_progress = round(
        (100*(stream.filesize - bytes_remaining)) / stream.filesize,
        2
    )

    update_status_label(f"Downloading... {dl_progress} %",)


def dir_select(dir_entry):
    """
        A wrapper for askdirectory() that populates the GUI.
    """

    directory = askdirectory()
    if directory:
        dir_entry.delete(0, "end")
        dir_entry.insert(0, directory)
        return directory


def update_status_label(status):
    """
        DRYs up two function calls, adds some dynamic behavior.
    """

    status_label.config(text=status)
    status_label.update()


def download(mode, link_entry, dir_entry, status_label, event=None):
    """
        Downloads a youtube video to a directory of the user's choice,
        and if nesseccary, renames the file to avoid overwriting.
    """

    if not link_entry.get():
        return
    if not url(link_entry.get()):
        messagebox.showwarning(
            "Invalid Input",
            "Input is not a valid URL."
        )
        link_entry.selection_range(0,"end")
        return

    update_status_label("Fetching")

    try:
        yt_vid = YouTube(link_entry.get())
    except Exception as err:
        messagebox.showwarning(
            "Invalid Link",
            "Input is not a valid Youtube URL."
        )
        update_status_label("Ready")
        link_entry.selection_range(0,"end")
        return

    yt_vid.register_on_progress_callback(progress)

    directory = dir_entry.get() or dir_select(dir_entry)
    if not directory:
        update_status_label("Ready")
        return
    if not exists(directory):
        messagebox.showwarning(
            "Invalid Path",
            "The specified directory cannot be found."
        )
        #Maybe create the directory instead?
        dir_entry.selection_range(0, "end")
        update_status_label("Ready")
        return

    stream = yt_vid.streams.filter(
        progressive="True",
        file_extension="mp4"
    ).first()

    full_path = directory + "/" + stream.title + ".mp4"
    (full_path, filename) = name_file(full_path)

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
        if mode.get() == "Audio Only":
            update_status_label("Extracting Audio...")
            audio = AudioSegment.from_file(full_path)
            audio.export(full_path, format="mp4")

    finally:
        update_status_label("Ready")
        link_entry.delete(0, "end")

if __name__ == "__main__":
    """
        Unfortunately, Pytube often fails with a 403 HTTPError, which
        renders this application mostly useless. For now, this is just a 
        tiny GUI that includes some of the basic functionality of both
        Pytube and Pydub. If a given video fails and returns 403, my best
        advice for now, is to simply try it with a different link.
    """

    master=Tk()

    if system() != "Windows":
        master.withdraw()
        messagebox.showwarning(
            "Incompatible platform",
            "MyTube currently supports Windows platforms only."
        )
        quit()

    master_width=450
    master_height=125
    master.minsize(width=450, height=125)
    master.resizable(width=True, height=False)

    (master_width_offset, master_height_offset)=get_offset(
        master_width, master_height
    )

    master.title("MyTube")
    master.iconbitmap("pylogo.ico")

    master.geometry(
        f"{master_width}"\
        f"x{master_height}"\
        f"+{master_width_offset}"\
        f"+{master_height_offset}"
    )

    master.columnconfigure(0, weight=1)

    mode = StringVar(master)
    mode.set("Video + Audio")

    #Widgets

    link_entry_x_scroll = Scrollbar(
        master,
        orient="horizontal"
    )

    link_entry = Entry(
        master,
        font="Sans_Serif 12",
        xscrollcommand=link_entry_x_scroll.set
    )

    link_entry_x_scroll.config(command=link_entry.xview)

    # from: https://effbot.org/tkinterbook/optionmenu.htm
    # the constructor syntax is:
    # OptionMenu(master, variable, *values)
    mode_menu = OptionMenu(
        master,
        mode,
        "Video + Audio",
        "Audio Only"
    )
    mode_menu.config(width=12)

    mode_label = Label(
        master,
        text="Mode:",
        font="Sans_Serif 10",
    )

    status_label = Label(
        master,
        text="Ready",
        font="Sans_Serif 12",
        padx=10,
        relief="sunken"
    )

    link_entry_button = Button(
        master,
        text="Submit",
        width=15,
        command= lambda: download(
            mode,
            link_entry,
            dir_entry,
            status_label
        )
    )

    dir_entry_x_scroll = Scrollbar(
        master,
        orient="horizontal"
    )

    dir_entry = Entry(
        master,
        font="Sans_Serif 12",
        xscrollcommand=dir_entry_x_scroll.set
    )

    dir_entry_x_scroll.config(command=dir_entry.xview)

    dir_entry_button = Button(
        master,
        text="Select Directory",
        width=15,
        command=lambda: dir_select(dir_entry)
    )

    #Layout

    link_entry.grid(row=0, column=0, sticky="ew")
    link_entry_x_scroll.grid(row=1, column=0, sticky="ew")
    link_entry_button.grid(row=0, column=1)
    mode_label.grid(row=1, column=1, sticky="ew")
    mode_menu.grid(row=2, column=1)
    status_label.grid(row=2, column=0)
    dir_entry.grid(row=3, column=0, sticky="ew")
    dir_entry_x_scroll.grid(row=4, column=0, sticky="ew")
    dir_entry_button.grid(row=3, column=1)    

    link_entry.bind(
        "<Return>",
        lambda event_handler: download(
            mode,
            link_entry,
            dir_entry,
            status_label,
            event_handler
        )
    )

    master.mainloop()