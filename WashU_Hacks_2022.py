import ntpath
import time
from io import BytesIO
from PIL import Image, ImageTk
import os
import tkinter as tk
from tkinter.messagebox import showinfo
from tqdm import tqdm
import sqlite3
from tkinter import *
from tkinter import filedialog, messagebox, ttk
import numpy as np
import cv2
import requests
import base64
import io
import glob
import json
from PIL import Image
from ttkwidgets.autocomplete import AutocompleteEntry
from tkcalendar import Calendar, DateEntry
from tkinterdnd2 import *

# Connect to local database
conn = sqlite3.connect('elephant_inferences.db')
# Create cursor
c = conn.cursor()
# Create table if needed
try:
    c.execute("""CREATE TABLE inferences (
                location_name text,
                date text,
                num_elephants integer,
                change integer
                )""")
    # Commit changes
    conn.commit()
except Exception:
    print("Table already made")

# Create the root window
root = TkinterDnD.Tk()
auto = tk.StringVar()
root.title("Elephant Detection Inferences")
root.geometry('350x590')

# Establish global variables
num_elephants = 0
change = 0
files = []
num_files = []

files_selected_label = Label(root)
num_elephants_label = Label(root)
num_elephants_pred_label = Label(root)
change_label = Label(root)
change_pred_label = Label(root)


# Counts and displays the number of files entered into the listbox
def files_entered():
    try:
        # Destroys existing widgets
        files_del = root.grid_slaves(row=2)
        for f in files_del:
            f.destroy()
    except:
        pass
    files_selected_label = Label(root, text=str(listbox.size()) + " file(s) entered")
    files_selected_label.grid(row=2, column=0)


# Browse button command to upload files
def clicked():
    global files
    global num_files
    global files_selected_label
    files = []
    num_files = []

    # Read file input
    files = filedialog.askopenfilenames(parent=root, title='Choose image files')

    # Insert files into listbox
    for file in files:
        listbox.insert(tk.END, file)
    # Display file count
    files_entered()


# Add files to listbox after drag and drop event
def addto_listbox(event):
    global files
    global num_files
    global files_selected_label

    # Parse dropped files and insert into listbox
    files_list = parse_drop_files(event.data)
    for item in files_list:
        listbox.insert(tk.END, item)
    # Display file count
    files_entered()


# Parse files uploaded via drag and drop
def parse_drop_files(filename):
    size = len(filename)
    # List of file paths
    res = []
    name = ""
    idx = 0
    while idx < size:
        if filename[idx] == "{":
            j = idx + 1
            while filename[j] != "}":
                name += filename[j]
                j += 1
            res.append(name)
            name = ""
            idx = j
        elif filename[idx] == " " and name != "":
            res.append(name)
            name = ""
        elif filename[idx] != " ":
            name += filename[idx]
        idx += 1
    if name != "":
        res.append(name)
    return res


# Delete function
def delete():
    global files_selected_label
    listbox.delete(0, tk.END)
    # Display file count
    files_entered()


# Delete selected file
def delete_selected():
    global files_selected_label
    selection = listbox.curselection()
    for i in reversed(selection):
        listbox.delete(i)
    # Display file count
    files_entered()


# Autogenerated predictive input for location name
def match_string():
    hits = []
    got = auto.get()
    for item in get_headers():
        if item.startswith(got):
            hits.append(item)
    return hits


# Retrieve keyboard input
def get_typed(event):
    if len(event.keysym) == 1:
        hits = match_string()
        show_hit(hits)


# Show keyboard hits
def show_hit(lst):
    if len(lst) == 1:
        auto.set(lst[0])
        detect_pressed.filled = True


# Detect if keyboard is pressed
def detect_pressed(event):
    key = event.keysym
    if len(key) == 1 and detect_pressed.filled is True:
        pos = location_name.index(tk.INSERT)
        location_name.delete(pos, tk.END)


# Run inferences using API on uploaded image
def run_inference(img):
    inferences = []

    try:
        # Load Image with PIL
        image = Image.open(img).convert("RGB")
        # Convert to JPEG Buffer
        buffered = io.BytesIO()
        image.save(buffered, quality=90, format="JPEG")
        # Base 64 Encode
        img_str = base64.b64encode(buffered.getvalue())
        img_str = img_str.decode("ascii")
        # Construct the URL
        upload_url = "".join([
            "https://detect.roboflow.com/aug_xtrain/1",
            "?api_key=EMXeLXTkv1EBinOpNZLZ",
            "&name=", ntpath.basename(img)
        ])
        # POST to the API
        r = requests.post(upload_url, data=img_str, headers={
            "Content-Type": "application/x-www-form-urlencoded"
        })
        # Output result
        inferences.append(r.json())
        r = requests.post(upload_url, data=img_str, headers={'Connection': 'close'})
    except:
        messagebox.showerror("Error", "Please upload JPEG files under 3.4 MB")
    return inferences


# Count number of elephants from inferences
def count_elephants(inferences):
    count = 0
    try:
        for pred in inferences:
            for obj in pred['predictions']:
                count += 1
    except:
        messagebox.showerror("Error", "Image is too large")
    return count


# Calculate change at a given location from last inference
def get_change():
    global num_elephants
    global change

    # Connect to database
    conn = sqlite3.connect('elephant_inferences.db')
    c = conn.cursor()
    # Query database by descending order and location name
    c.execute("SELECT * FROM inferences WHERE location_name ='" + location_name.get() + "' ORDER BY rowid DESC")
    try:
        # Get the number of elephants from the last inference if exists
        record = c.fetchone()[2]
    except:
        record = 0
    # Calculate change
    change = num_elephants - record

    conn.commit()
    conn.close()
    return change


# Get the location name headers from database entries
def get_headers():
    headers = []
    # Connect to database
    conn = sqlite3.connect('elephant_inferences.db')
    c = conn.cursor()
    # Select distinct location names from database in alphabetical order
    c.execute("SELECT DISTINCT location_name FROM inferences ORDER BY location_name ASC")
    records = c.fetchall()

    # Retrieve the location name
    for record in records:
        headers.append(str(record)[2:-3])

    conn.commit()
    conn.close()
    return headers


# Run predictions
def predict():
    global num_elephants
    global num_elephants_label
    global num_elephants_pred_label
    global change_label
    global change_pred_label
    global files

    num_elephants = 0
    files = listbox.get(0, END)

    # Run inferences on files and count elephants
    for f in tqdm(files):
        img = str(f)
        result = run_inference(img)
        num_elephants += count_elephants(result)

    # Update labels
    num_elephants_label = Label(frame_pred, text="Predicted Number of Elephants")
    num_elephants_label.grid(row=0, column=0)

    num_elephants_pred_label = Label(frame_pred, text=str(num_elephants))
    num_elephants_pred_label.grid(row=0, column=1)

    change_label = Label(frame_pred, text="Change")
    change_label.grid(row=1, column=0)

    change_pred_label = Label(frame_pred, text=str(get_change()))
    change_pred_label.grid(row=1, column=1)


# Check if a location name exists in database
def exists(location_name):
    dup = True
    # Connect to database
    conn = sqlite3.connect('elephant_inferences.db')
    c = conn.cursor()

    # Select one from query for location name if exists
    c.execute("SELECT 1 FROM inferences WHERE location_name='" + location_name + "'")
    qry = c.fetchall()

    if str(qry) == 'None':
        dup = False

    conn.commit()
    conn.close()
    return dup


# Save command for entering a new record into the database
def enter():
    global num_elephants
    global change

    # Connect to database
    conn = sqlite3.connect('elephant_inferences.db')
    c = conn.cursor()

    # Insert into table
    c.execute("INSERT INTO inferences VALUES (:location_name, :date, :num_elephants, :change)",
              {
                  'location_name': location_name.get(),
                  'date': date.get(),
                  'num_elephants': num_elephants,
                  'change': change
              })
    conn.commit()
    conn.close()

    # Clear the window for new inferences
    try:
        location_name.delete(0, END)
    except:
        pass
    update_listbox(get_headers())
    delete()
    # Clear files selected label
    root.grid_slaves(row=2, column=0)[0].destroy()
    # Clear predicted elephants label
    pred_del = root.grid_slaves(row=5)
    for p in pred_del:
        p.destroy()
    root.update_idletasks()


# Show all records in database
def query():
    # Create a new window for viewing
    records_win = Toplevel(root)

    # Connect to database
    conn = sqlite3.connect('elephant_inferences.db')
    c = conn.cursor()

    # Select all from database
    c.execute("SELECT *, oid FROM inferences")
    records = c.fetchall()

    # Print contents of databse
    print_records = ''
    for record in records:
        print_records += str(record[:-1]) + "\n"
    query_label = Label(records_win, text=print_records)
    query_label.pack()

    conn.commit()
    conn.close()

    records_win.mainloop()


# Command for opening window for viewing and editing records in database
def search():
    # Wait function to confirm deletion of record
    def wait(id):
        nonlocal delete
        nonlocal Time
        nonlocal j
        nonlocal num

        num = id
        frm.grid_slaves(row=num, column=j + 1)[0].destroy()
        confirm = Button(frm, text="Confirm?", command=lambda: wait2(id))
        confirm.grid(row=num, column=j + 1)

        # Return button to normal after a period of delay
        Time = frm.after(3000, normal)

    # Return delete button to normal
    def normal():
        nonlocal delete

        nonlocal num
        frm.grid_slaves(row=num, column=j + 1)[0].destroy()

        delete = Button(frm, text="Delete", command=lambda: wait(num))
        delete.grid(row=num, column=j + 1)

    # Deletes selected record from database
    def wait2(id):
        nonlocal delete
        nonlocal i
        nonlocal num
        nonlocal deleted
        nonlocal sub

        frm.after_cancel(Time)
        idx = frm.grid_slaves(row=id, column=4)[0].get()

        # Connect to database
        conn = sqlite3.connect('elephant_inferences.db')
        c = conn.cursor()

        deleted = deleted + 1

        # Delete record based off of id field
        records = c.execute("DELETE FROM inferences WHERE rowid=" + str(idx))
        sub = sub + 10

        # Delete corresponding widgets associated with record
        l = list(frm.grid_slaves(row=id))
        for w in (l):
            w.destroy()

        conn.commit()
        conn.close()

        data = get_headers()
        update_listbox(data)

    # Save edited record
    def top_save(row):
        # Connect to database
        conn = sqlite3.connect('elephant_inferences.db')
        c = conn.cursor()

        # Get table values from label info
        p = frm.grid_slaves(row=row, column=0)[0].get()
        d = frm.grid_slaves(row=row, column=1)[0].get()
        n = frm.grid_slaves(row=row, column=2)[0].get()
        g = frm.grid_slaves(row=row, column=3)[0].get()
        id = frm.grid_slaves(row=row, column=4)[0].get()

        # Update database
        c.execute("UPDATE inferences SET location_name=?, date=?, num_elephants=?, change=? WHERE rowid=?", (p, d, n, g, id))
        conn.commit()
        show()

        conn.commit()
        conn.close()

    # Save all entries
    def save_entries():
        # Connect to database
        conn = sqlite3.connect('elephant_inferences.db')
        c = conn.cursor()

        for k in range(2):
            nonlocal i
            nonlocal sub

            rows = range(3, (len(frm.grid_slaves(column=0))))
            print(rows)

            # Parse through all rows in window
            for row in rows:
                try:
                    p = frm.grid_slaves(row=row, column=0)[0].get()
                    d = frm.grid_slaves(row=row, column=1)[0].get()
                    n = frm.grid_slaves(row=row, column=2)[0].get()
                    g = frm.grid_slaves(row=row, column=3)[0].get()
                    id = frm.grid_slaves(row=row, column=4)[0].get()

                    c.execute("UPDATE inferences SET location_name=?, date=?, num_elephants=?, change=? WHERE rowid=?",
                              (p, d, n, g, id))
                except:
                    pass

            # Deleted entries
            dellist = list(range(0, deleted))
            numbers = 0

            for w in dellist:
                for x in list(frm.grid_slaves(row=i + w)):
                    x.destroy()

            conn.commit()
            show()
            sub = sub + i

            conn.commit()
            conn.close()

    # Show records
    def show():
        nonlocal i
        nonlocal delete

        # Connect to database
        conn = sqlite3.connect('elephant_inferences.db')
        c = conn.cursor()

        # Show all records
        c.execute("SELECT COUNT(*) FROM inferences")
        all_records = c.fetchone()

        # Search records if input in search field
        sql = ""
        if len(search_entry.get()) != 0:
            for row in range(3, 3 + int(str(all_records)[1:-2])):
                for col in range(0, 7):
                    item = frm.grid_slaves(row=row, column=col)
                    for l in item:
                        l.destroy()
            try:
                sql = " WHERE location_name='" + search_entry.get() + "'"
            except:
                messagebox.showerror("Invalid Location Name")

        c.execute("SELECT *, oid from inferences" + sql)
        records = c.fetchall()

        # Row value of records
        i = 3
        nonlocal j

        # Populate window with records
        for record in records:
            values = []
            for j in range(len(record)):
                e = Entry(frm, width=10)
                e.grid(row=i, column=j)
                e.insert(END, record[j])
                if j == 4:
                    e.config(state=DISABLED)
                values.append(e.get())

            # Add delete and save buttons
            delete = Button(frm, text='Delete', command=lambda d=i: wait(d))
            delete.grid(row=i, column=j + 1)
            save = Button(frm, text="Save", command=lambda d=i: top_save(d))
            save.grid(row=i, column=j + 2)
            i = i + 1

        conn.commit()
        conn.close()

    # Refresh window
    def refresh():
        show()

    # Reset window
    def reset(text):
        nonlocal i
        nonlocal delete
        nonlocal deleted

        # Connect to database
        conn = sqlite3.connect('elephant_inferences.db')
        c = conn.cursor()

        # Populate database records
        for k in range(2):
            c.execute("SELECT COUNT(*) FROM inferences")
            all_records = c.fetchone()

            sql = ""
            if len(search_entry.get()) != 0:
                for row in range(3, 3 + int(str(all_records)[1:-2])):
                    for col in range(0, 7):
                        item = frm.grid_slaves(row=row, column=col)
                        for l in item:
                            l.destroy()
                try:
                    sql = " WHERE location_name='" + search_entry.get() + "'"
                except:
                    messagebox.showerror("Invalid Location Name")

            c.execute("SELECT *, oid from inferences" + sql)
            records = c.fetchall()

            # Row value of records
            i = 3
            nonlocal j

            conn.execute("VACUUM")

            for record in records:
                values = []
                for j in range(len(record)):
                    e = Entry(frm, width=10)
                    e.grid(row=i, column=j)
                    e.insert(END, record[j])
                    if j == 4:
                        e.config(state=DISABLED)
                    values.append(e.get())

                delete = Button(frm, text='Delete', command=lambda d=i: wait(d))
                delete.grid(row=i, column=j + 1)
                save = Button(frm, text="Save", command=lambda d=i: top_save(d))
                save.grid(row=i, column=j + 2)
                i = i + 1

            dellist = []
            dellist = list(range(0, deleted))
            numbers = 0
            for w in dellist:
                print(w)

                for x in list(frm.grid_slaves(row=i + w)):
                    x.destroy()

            conn.commit()
            conn.close()

    # Reopen search window
    top_search = tk.Toplevel(root)
    top_search.geometry("750x425")
    top_search.title("Search Window")

    # Helper function
    def myfunction(event):
        canvas.configure(scrollregion=canvas.bbox("all"), width=500, height=300)

    # Show records
    def show_enter(event):
        show()

    # Search window frame
    myframe2 = Frame(top_search, width=100, height=100)
    myframe2.pack(side=TOP, anchor=NW)

    # Search location name label
    search_label = Label(myframe2, text="Search by Location Name")
    search_label.grid(row=0, column=1, sticky=N + E + S + W, padx=10, pady=5)

    # Search location name entry
    search_entry = Entry(myframe2, width=10)
    search_entry.grid(row=1, column=1, sticky=N + E + S + W, padx=10)

    # Search button
    search_entry_btn = Button(myframe2, text="Search", command=show)
    search_entry_btn.grid(row=1, column=2, sticky=N + E + S + W)

    top_search.columnconfigure(0, weight=1)
    top_search.columnconfigure(1, weight=2)

    # Column headers
    p_label = Label(myframe2, text="                                       Location")
    p_label.grid(row=2, column=1, pady=2)
    d_label = Label(myframe2, text='Date')
    d_label.grid(row=2, column=2, pady=2)
    n_label = Label(myframe2, text='        Elephants')
    n_label.grid(row=2, column=4, pady=5)
    c_label = Label(myframe2, text='    Change')
    c_label.grid(row=2, column=5, pady=5)
    i_label = Label(myframe2, text='      ID           ')
    i_label.grid(row=2, column=6, pady=5)

    # Reset ID button
    Reset_ID = Button(myframe2, text="Reset ID", command=lambda: reset("plant"))
    Reset_ID.grid(row=1, column=8)

    # Refresh button
    refresh_btn = Button(myframe2, text="Refresh", command=lambda: refresh())
    refresh_btn.grid(row=1, column=9)

    # Save all button
    save_all = Button(myframe2, text="Save All", command=save_entries)
    save_all.grid(row=1, column=10)

    # Records frame
    myframe = Frame(top_search, bd=1)
    myframe.pack()
    canvas = Canvas(myframe)
    frm = Frame(canvas)

    # Scrollbar
    myscrollbar = Scrollbar(myframe, orient=VERTICAL, command=canvas.yview)
    canvas.config(yscrollcommand=myscrollbar.set)
    myscrollbar.config(command=canvas.yview)

    search_entry.bind("<Return>", show_enter)
    myscrollbar.pack(side="right", fill="y")
    canvas.pack(side="left")
    canvas.create_window((0, 0), window=frm, anchor='nw')
    frm.bind("<Configure>", myfunction)

    # Connect to database
    conn = sqlite3.connect('elephant_inferences.db')
    c = conn.cursor()

    # Variables
    delete = Button()
    i = 0
    Time = ""
    j = 0
    num = 0
    deleted = 0
    sub = 0

    show()
    conn.commit()
    conn.close()

    top_search.mainloop()


# Update listbox
def update_listbox(data):
    # Clear listbox
    listbox_list.delete(0, END)
    # Add items to listbox
    for item in data:
        listbox_list.insert(END, item)


# Update entry box with listbox clicked
def fillout_listbox(e):
    # Delete whatever is in the entry box
    location_name.delete(0, END)
    # Add clicked list item to entry box
    location_name.insert(0, listbox_list.get(ANCHOR))


# Create function to check entry vs listbox
def check_listbox(e):
    # Grab what was typed
    typed = location_name.get()
    if typed == '':
        data = headers
    else:
        data = []
        for item in headers:
            if typed.lower() in item.lower():
                data.append(item)

    # Update listbox with selected items
    update_listbox(data)


# Cursor helper function
def shift_cursor(event=None):
    position = location_name.index(INSERT)
    location_name.icursor(END)


# Initialize to false
detect_pressed.filled = False

# Initialize frames in main window
frame_files = Frame(root)
frame_files.grid(row=0, column=0, padx=10, pady=5)

frame_file_buttons = Frame(frame_files)
frame_file_buttons.grid(row=1, column=0)

frame_pred = Frame(root)
frame_pred.grid(row=5, column=0)

frame_filebox = Frame(root)
frame_filebox.grid(row=1, column=0, padx=10, pady=10)

frame_bottom = Frame(root)
frame_bottom.grid(row=3, column=0, padx=10, pady=5)

frame_inf = Frame(root)
frame_inf.grid(row=4, column=0, padx=10, pady=5)

# File instructions label
lbl = Label(frame_files, text="Select or Drag and Drop Files")
lbl.grid(row=0, column=0)

# The button to insert the item in the list
button = Button(frame_file_buttons, text="Browse", command=clicked)
button.grid(row=0, column=0)

# The button to delete everything
button_delete = Button(frame_file_buttons, text="Clear All", command=delete)
button_delete.grid(row=0, column=1)

# The button to delete only the selected item in the list
button_delete_selected = Button(frame_file_buttons, text="Delete Selected", command=delete_selected)
button_delete_selected.grid(row=0, column=2)

# The file listbox
listbox = Listbox(frame_filebox, width=50, selectmode="extended")
listbox.grid(row=0, column=0)
listbox.drop_target_register(DND_FILES)
listbox.dnd_bind('<<Drop>>', addto_listbox)

# File scrollbar y-axis
filesy_sb = Scrollbar(frame_filebox, orient=VERTICAL)
filesy_sb.grid(row=0, column=1, sticky=NS)
listbox.config(yscrollcommand=filesy_sb.set)
filesy_sb.config(command=listbox.yview)

# File scrollbar x-axis
filesx_sb = Scrollbar(frame_filebox, orient=HORIZONTAL)
filesx_sb.grid(row=1, column=0, sticky=NSEW)
listbox.config(xscrollcommand=filesx_sb.set)
filesx_sb.config(command=listbox.xview)

# Location name entry
location_name = Entry(frame_bottom, width=30, textvariable=auto)
location_name.focus_set()
location_name.bind('<KeyRelease>', get_typed)
location_name.bind('<Key>', detect_pressed)
location_name.bind("<KeyRelease>", check_listbox, add='+')
location_name.bind("<Return>", shift_cursor, add='+')

# Location name label
location_name_label = Label(frame_bottom, text="Location Name")
location_name_label.grid(row=0, column=0)
location_name.grid(row=1, column=0)

# Locationname listbox
listbox_list = Listbox(frame_bottom, width=30)
listbox_list.grid(row=2, column=0)

# Create a list of headers
headers = get_headers()
# Add the items to our list
update_listbox(headers)
# Create a binding on the listbox onclick
listbox_list.bind("<<ListboxSelect>>", fillout_listbox)

# Location name scrollbar
location_name_sb = Scrollbar(frame_bottom, orient=VERTICAL)
location_name_sb.grid(row=2, column=1, sticky=NS)
listbox_list.config(yscrollcommand=location_name_sb.set)
location_name_sb.config(command=listbox_list.yview)

# Date label
date_label = Label(frame_bottom, text="Date")
date_label.grid(row=0, column=2)

# Date entry
date = DateEntry(frame_bottom)
date.grid(row=1, column=2)

# Predict button
pred_btn = Button(frame_inf, text="Predict", command=predict)
pred_btn.grid(row=0, column=0)

# Infer button
infer = Button(frame_inf, text="Visualize", command=lambda: [infer(), ])
infer.grid(row=0, column=1)

# Save button
save_btn = Button(frame_inf, text="Save Info", command=enter)
save_btn.grid(row=0, column=2)

# All records button
search_btn = Button(frame_inf, text="All Records", command=lambda: search())
search_btn.grid(row=0, column=3)


# Visualize elephant inferences
def infer():
    global List_Images

    List_Images = []
    files = listbox.get(0, END)
    count = []

    for file in tqdm(files):
        try:
            # Load image from file
            image = Image.open(file).convert("RGB")

            # Convert to JPEG Buffer
            buffered = io.BytesIO()
            image.save(buffered, quality=90, format="JPEG")

            # Base 64 Encode
            img_str = base64.b64encode(buffered.getvalue())
            img_str = img_str.decode("ascii")

            # Aug model
            upload_url = "".join([
                "https://detect.roboflow.com/aug_xtrain/1",
                "?api_key=EMXeLXTkv1EBinOpNZLZ",
                "&name=",
                file,
                "&format=image"
            ])

            # Get prediction from Roboflow Infer API
            resp = requests.post(upload_url, data=img_str, headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }, stream=True).raw

            bytes_stream = BytesIO(resp.read())
            img = Image.open(bytes_stream)
            img = img.resize((1500, 750))
            img = ImageTk.PhotoImage(img)
            List_Images.append(img)

            # Retrieve JSON file for elephant count
            inference = run_inference(file)
            count.append(count_elephants(inference))

        except:
            print(file + " could not be inferred.")

    # Create new window
    display = Toplevel()
    display.geometry("1500x850")

    # Frame for arrows
    frame_arrows = Frame(display)
    frame_arrows.grid(row=3, column=0, pady=10)

    # Display image
    my_label = Label(display, image=List_Images[0])
    my_label.grid(row=0, column=0)

    # File name
    im_num = Label(display, text=files[0])
    im_num.grid(row=1, column=0)

    # Number of elephants
    elephant_count = Label(display, text=str(count[0]) + " elephant(s)")
    elephant_count.grid(row=2, column=0)

    # Forward button
    def img_forward(image_number):
        nonlocal my_label
        nonlocal forward_button
        nonlocal back_button
        nonlocal button_exit
        nonlocal files
        nonlocal im_num
        nonlocal elephant_count

        # Forward image
        display.grid_slaves(row=0, column=0)[0].destroy()
        my_label = Label(display, image=List_Images[image_number - 1])
        my_label.grid(row=0, column=0)

        # Forward file name
        display.grid_slaves(row=1, column=0)[0].destroy()
        im_num = Label(display, text=files[image_number - 1])
        im_num.grid(row=1, column=0)

        # Forward elephant count
        display.grid_slaves(row=2, column=0)[0].destroy()
        elephant_count = Label(display, text=str(count[image_number - 1]) + " elephant(s)")
        elephant_count.grid(row=2, column=0)

        # Reset arrows
        arrows = frame_arrows.grid_slaves(row=0)
        for a in arrows:
            a.destroy()
        forward_button = Button(frame_arrows, text=">", command=lambda: img_forward(image_number + 1))
        back_button = Button(frame_arrows, text="<", command=lambda: img_back(image_number - 1))
        button_exit = Button(frame_arrows, text="Exit", command=display.destroy)

        if image_number == len(List_Images):
            forward_button = Button(frame_arrows, text=">", state=DISABLED)

        back_button.grid(row=0, column=0)
        button_exit.grid(row=0, column=1)
        forward_button.grid(row=0, column=2)

    # Back button
    def img_back(image_number):
        nonlocal my_label
        nonlocal forward_button
        nonlocal back_button
        nonlocal button_exit
        nonlocal files
        nonlocal im_num
        nonlocal elephant_count

        # Back image
        display.grid_slaves(row=0, column=0)[0].destroy()
        my_label = Label(display, image=List_Images[image_number - 1])
        my_label.grid(row=0, column=0)

        # Back file name
        display.grid_slaves(row=1, column=0)[0].destroy()
        im_num = Label(display, text=files[image_number - 1])
        im_num.grid(row=1, column=0)

        # Back elephant count
        display.grid_slaves(row=2, column=0)[0].destroy()
        elephant_count = Label(display, text=str(count[image_number - 1]) + " elephant(s)")
        elephant_count.grid(row=2, column=0)

        # Reset arrows
        arrows = frame_arrows.grid_slaves(row=0)
        for a in arrows:
            a.destroy()
        forward_button = Button(frame_arrows, text=">", command=lambda: img_forward(image_number + 1))
        back_button = Button(frame_arrows, text="<", command=lambda: img_back(image_number - 1))
        button_exit = Button(frame_arrows, text="Exit", command=display.destroy)

        if image_number == 1:
            back_button = Button(frame_arrows, text="<", state=DISABLED)

        back_button.grid(row=0, column=0)
        button_exit.grid(row=0, column=1)
        forward_button.grid(row=0, column=2)

    # Display arrows
    back_button = Button(frame_arrows, text="<", command=img_back, state=DISABLED)
    button_exit = Button(frame_arrows, text="Exit", command=display.destroy)
    forward_button = Button(frame_arrows, text=">", command=lambda: img_forward(2))

    if len(List_Images) == 1:
        forward_button = Button(frame_arrows, text=">", state=DISABLED)

    back_button.grid(row=0, column=0)
    button_exit.grid(row=0, column=1)
    forward_button.grid(row=0, column=2)

    display.mainloop()
    return List_Images


root.mainloop()