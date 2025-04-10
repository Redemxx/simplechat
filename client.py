import tkinter as tk
from tkinter import messagebox

import threading
import socket
import queue
import webbrowser
import re

url_regex_1 = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
url_regex_2 = r"[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"
emoji_regex = r":[^ ]+:"
urls = []

emojis = {
    ":smile:": "😀",
    ":sad:": "☹️",
    ":giddy:": "😁",
    ":lmao:": "🤣",
    ":smug:": "😏",
    ":angry:": "😡",
    ":gasp:": "😱",
    ":worried:": "😟",
    ":disappointed:": "😔",
    ":yikes:": "😬",
    ":o:": "😮",
    ":skull:": "💀",
    ":nerd:": "🤓",
    ":yawn:": "🥱",
    ":wave:": "👋",
    ":clap:": "👏"
}


def open_link(event):
    try:
        i = int(event.widget.tag_names(tk.CURRENT)[2])
    except:
        i = int(event.widget.tag_names(tk.CURRENT)[1])
    webbrowser.open(urls[i])


class App:
    def __init__(self, master):
        self.master = master
        master.title("Chat")

        # Variables
        self.username = ""
        self.running = False
        self.data_queue = queue.Queue()

        # Server config
        self.host = "dread.deadendnet.net"
        self.port = 7580

        # Login frame
        self.loginFrame = tk.Frame(master)
        self.loginFrame.pack(fill="both", expand=True)

        tk.Label(self.loginFrame, text="Enter your username:").pack(pady=10)
        self.usernameEntry = tk.Entry(self.loginFrame, width=30)
        self.usernameEntry.pack(pady=5)
        self.usernameEntry.bind("<Return>", self.connectToServer)
        self.usernameEntry.focus()

        tk.Button(self.loginFrame, text="Connect", command=self.connectToServer).pack(pady=10)

        # Chat frame
        self.chatFrame = tk.Frame(master)

        # Display
        chatDisplayFrame = tk.Frame(self.chatFrame)
        chatDisplayFrame.pack(padx=10, pady=10, fill="both", expand=True)

        self.chatDisplay = tk.Text(chatDisplayFrame, wrap=tk.WORD)
        self.chatDisplay.pack(side="left", fill="both", expand=True)

        # Individual text color
        self.chatDisplay.tag_configure("myMsg", background="#90EE90")  # TEXT
        self.chatDisplay.tag_configure("systemMsg", background="#f5250a", foreground="#ffffff")
        self.chatDisplay.tag_configure("directMsg", background="#3fc0e0")
        self.chatDisplay.tag_configure("weblink", foreground="#324cf0", underline=True)
        self.chatDisplay.tag_configure("infoMsg", foreground="#007787")
        self.chatDisplay.tag_bind("weblink", "<Button-1>", open_link)

        # Input area frame
        inputFrame = tk.Frame(self.chatFrame)
        inputFrame.pack(padx=10, pady=5, fill="x", side="bottom")

        # Message
        self.messageEntry = tk.Entry(inputFrame, width=50)
        self.messageEntry.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=10)
        self.messageEntry.bind("<Return>", self.sendMessageEvent)
        self.messageEntry.bind("<KeyRelease>", self.scrub_emoji)

        # Send
        tk.Button(inputFrame, text="Send", command=self.sendMessage).pack(side="right", padx=5, pady=10)

    def connectToServer(self, event=None):
        # Event is to allow the entry box to be able to call the function.
        
        self.username = self.usernameEntry.get().strip()
        if not self.username:
            messagebox.showerror("ERROR", "Username cannot be empty")
            return

        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))

            # Send username to server
            self.socket.sendall(self.username.encode('utf-8'))

            # Get response
            response = self.socket.recv(1024).decode()
            if response != "&&&OK&&&":
                self.usernameEntry.delete(0, tk.END)
                tk.messagebox.showinfo("Error", "Username Taken")
                return

            # Switch from login frame to chat frame
            self.loginFrame.pack_forget()
            self.chatFrame.pack(fill="both", expand=True)

            # Chat window title - USERNAME and PORT
            self.master.title(f"Chat: {self.username} (Port: {self.port})")

            # Good connection
            self.running = True

            # Initiate socket reader thread
            self.socket_thread = threading.Thread(target=self.read_socket)
            self.socket_thread.daemon = True
            self.socket_thread.start()

            # Initiate GUI update
            self.update_gui()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect: {str(e)}")

    def read_socket(self):
        try:
            while self.running:
                data = self.socket.recv(1024)
                if not data:
                    self.data_queue.put(("Error:", "systemMsg"))
                    self.running = False
                    break

                # Parse for message tags
                message = data.decode()

                if "@" + self.username in message:
                    self.data_queue.put((message, "directMsg"))
                elif message.startswith("System:"):
                    self.data_queue.put((message, "systemMsg"))
                else:
                    self.data_queue.put((message, None))

        except Exception as e:
            self.data_queue.put((f"Error: {e}", "systemMsg"))
            self.close()

    def update_gui(self):
        try:
            while not self.data_queue.empty():
                message, tag = self.data_queue.get_nowait()
                self.display_message(message, tag)
        except queue.Empty:
            pass
        if self.running:
            self.master.after(100, self.update_gui)  # Check every 100 ms

    def display_message(self, message, tag=None):
        self.chatDisplay.config(state="normal")

        url = re.search(url_regex_1, message)
        if url is None:
            url = re.search(url_regex_2, message)

        if url:
            url = url.group(0)
            ind = len(urls)
            urls.append(url)
            message = message.split(url)

            if tag:
                self.chatDisplay.insert(tk.END, message[0], tag)
                self.chatDisplay.insert(tk.END, url, (tag, "weblink", str(ind)))
                self.chatDisplay.insert(tk.END, message[1] + "\n", tag)
            else:
                self.chatDisplay.insert(tk.END, message[0])
                self.chatDisplay.insert(tk.END, url, ("weblink", str(ind)))
                self.chatDisplay.insert(tk.END, message[1] + "\n")
        else:
            if tag:
                self.chatDisplay.insert(tk.END, message + "\n", tag)
            else:
                self.chatDisplay.insert(tk.END, message + "\n")
        self.chatDisplay.see(tk.END)
        self.chatDisplay.config(state="disabled")

    def sendMessage(self):
        message = self.messageEntry.get().strip()
        if not message or not self.running:
            return

        if message.startswith('/'):
            self.command(message[1:])
            self.messageEntry.delete(0, tk.END)
            return

        try:
            # Color tag for sender
            self.display_message(f"{self.username}: {message}", "myMsg")

            # Send to server
            self.socket.sendall(message.encode('utf-8'))
            # Clear message after sent
            self.messageEntry.delete(0, tk.END)

        except Exception as e:
            self.display_message(f"System: Error sending message: {e}", "systemMsg")

    def scrub_emoji(self, event=None):
        message = self.messageEntry.get().strip()
        new_message = self.messageEntry.get().strip()
        match = True
        updated = False

        while match:
            match = re.search(emoji_regex, message)

            if match:
                try:
                    emoji = emojis.get(match.group(0), None)

                    if emoji:
                        new_message = new_message.replace(match.group(0), emoji)
                        updated = True

                finally:
                    message = message.replace(match.group(0), "")

        if updated:
            self.messageEntry.delete(0, tk.END)
            self.messageEntry.insert(0, new_message)

    def sendMessageEvent(self, event):
        self.sendMessage()
        return

    def close(self):
        self.close_connection()
        self.running = False
        self.master.destroy()

    def close_connection(self):
        try:
            message = "&&&SYSTEM-CLOSE&&&"
            # Send to server
            self.socket.sendall(message.encode('utf-8'))
        except:
            # Connection is already dead
            pass

    def command(self, message):
        segments = message.split(' ')

        match segments[0]:
            case "help":
                self.display_message("Available commands:\n\temojis\n\tlist", "infoMsg")
            case "emojis":
                self.command_emojis()
            case "list":
                self.command_list()

    def command_emojis(self):
        message = "Available Emojis:"
        for emoji in emojis.keys():
            message += f"\n\t{emoji} --> {emojis[emoji]}"
        self.display_message(message, "infoMsg")

    def command_list(self):
        message = "Online Users:"
        self.socket.sendall("&&&USER-LIST&&&".encode('utf-8'))
        # data = self.socket.recv(1024).decode()
        # message += data
        self.display_message(message, "infoMsg")


if __name__ == "__main__":
    root = tk.Tk()
    chat = App(root)
    root.protocol("WM_DELETE_WINDOW", chat.close)
    root.mainloop()