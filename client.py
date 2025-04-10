import tkinter as tk
import threading
import socket
import queue

class App:
    def __init__(self, master):
        self.master = master
        master.title("Chat")
    
        #Variables
        self.username = ""
        self.running = False
        self.data_queue = queue.Queue()
        
        #Server config
        self.host = "localhost"
        self.port = 7580
        
        #Login frame
        self.loginFrame = tk.Frame(master)
        self.loginFrame.pack(fill="both", expand=True)
        
        tk.Label(self.loginFrame, text="Enter your username:").pack(pady=10)
        self.usernameEntry = tk.Entry(self.loginFrame, width=30)
        self.usernameEntry.pack(pady=5)
        self.usernameEntry.focus()
        

        tk.Button(self.loginFrame, text="Connect", command=self.connectToServer).pack(pady=10)
        
        #Chat frame
        self.chatFrame = tk.Frame(master)
        
        #Display
        chatDisplayFrame = tk.Frame(self.chatFrame)
        chatDisplayFrame.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.chatDisplay = tk.Text(chatDisplayFrame, wrap=tk.WORD)
        self.chatDisplay.pack(side="left", fill="both", expand=True)
        
        #Individual text color
        self.chatDisplay.tag_configure("myMsg", background="#90EE90") #TEXT COLOR
      
        
        # Input area frame
        inputFrame = tk.Frame(self.chatFrame)
        inputFrame.pack(padx=10, pady=5, fill="x", side="bottom")
        
        #Message
        self.messageEntry = tk.Entry(inputFrame, width=50)
        self.messageEntry.pack(side="left", fill="x", expand=True, padx=(0, 5), pady=10)
        self.messageEntry.bind("<Return>", self.sendMessageEvent)
        
        #Send
        tk.Button(inputFrame, text="Send", command=self.sendMessage).pack(side="right", padx=5, pady=10)

    def connectToServer(self):
        self.username = self.usernameEntry.get().strip()
        if not self.username:
            self.errorLabel.config(text="ERROR: Username cannot be empty")
            return
        
        try:
            #Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            #Send username to server
            self.socket.sendall(self.username.encode('utf-8'))
            
            #Switch from login frame to chat frame
            self.loginFrame.pack_forget()
            self.chatFrame.pack(fill="both", expand=True)
            
            #Chat window title - USERNAME and PORT
            self.master.title(f"Chat: {self.username} (Port: {self.port})")
            
            #Good connection
            self.running = True
            
            #Initiate socket reader thread
            self.socket_thread = threading.Thread(target=self.read_socket)
            self.socket_thread.daemon = True
            self.socket_thread.start()
            
            #Initiate GUI update
            self.update_gui()
            
        except Exception as e:
            self.errorLabel.config(text=f"Failed to connect: {str(e)}")
    
    def read_socket(self):
        try:
            while self.running:
                data = self.socket.recv(1024)
                if not data:
                    self.data_queue.put(("Error:", "systemMsg"))
                    self.running = False
                    break
                self.data_queue.put((data.decode(), None))
        except Exception as e:
                self.data_queue.put((f"Error: {e}", "systemMsg"))
                self.running = False
    
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
        
        try:
            #Color tag for sender
            self.display_message(f"{self.username}: {message}", "myMsg")
            
            #Send to server
            self.socket.sendall(message.encode('utf-8'))
            #Clear message after sent
            self.messageEntry.delete(0, tk.END)
            
        except Exception as e:
            self.display_message(f"System: Error sending message: {e}", "systemMsg")
    
    def sendMessageEvent(self, event):
        self.sendMessage()
        return 
    
    def close(self):
        self.running = False
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    chat = App(root)
    root.protocol("WM_DELETE_WINDOW", chat.close)
    root.mainloop()