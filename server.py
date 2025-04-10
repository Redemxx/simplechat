import time
from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
from queue import Queue
import re
import datetime

incoming_port = 7580
username_regex = r"(\B|\b)@[^ ]+\b"
client_close_connection_message = "&&&SYSTEM-CLOSE&&&"
client_list_request = "&&&USER-LIST&&&"
log_lock = False

client_connections = {}


def log(message):
    global log_lock
    while log_lock:
        time.sleep(0.01)

    log_lock = True
    print(f"{datetime.datetime.now()}/> {message}")
    log_lock = False


def client_connection(socket_conn: socket, addr):
    try:
        username = socket_conn.recv(1024).decode()
        if username in client_connections.keys():
            socket_conn.sendall("&&&USERNAME-TAKEN&&&".encode('utf-8'))
            raise ConnectionError("Username in use")
        else:
            socket_conn.sendall("&&&OK&&&".encode('utf-8'))

        forward_message("System", f"{username} joined the chat.")
        log(f"{username} connected")
    except:
        socket_conn.close()
        log(f"Unable to establish communication with {addr}")
        return

    message_queue = Queue()
    client_connections[username] = message_queue

    outgoing_thread = Thread(target=client_outgoing, args=(socket_conn, message_queue, username,))
    outgoing_thread.start()

    try:
        while username in client_connections:
            # May need to consider multi-packet messages.
            message = socket_conn.recv(1024).decode()

            if message == client_close_connection_message:
                break
            elif message == client_list_request:
                response = "\n".join(client_connections.keys())
                print(response)
                client_connections[username].put(response)
                continue
            else:
                forward_message(username, message)
    except:
        pass
    finally:
        socket_conn.close()
        client_connections[username].put(client_close_connection_message)
        outgoing_thread.join()
        client_connections.pop(username)
        forward_message("System", f"{username} disconnected")
        log(f"{username} disconnected")


def client_outgoing(socket_conn: socket, queue, username):
    while username in client_connections:
        try:
            item = queue.get()

            if item == client_close_connection_message:
                break

            socket_conn.sendall(item.encode('utf-8'))
            queue.task_done()
        except:
            # Client disconnected
            pass
    log(f"Closed outgoing thread for {username}")


def forward_message(sender, message: str):
    message = sender + ": " + message

    # Direct Message
    direct_message = re.search(username_regex, message)
    if direct_message:
        recipient = direct_message.group(0)[1:]

        try:
            client_connections[recipient].put(message)
        except:
            client_connections[sender].put(f"System: Could not find user {recipient}")
        finally:
            return

    # Message all users
    for client in client_connections:
        if client == sender:
            continue

        client_connections[client].put(message)


if __name__ == "__main__":
    log(f"Server started on port {incoming_port}")

    welcomeSocket = socket(AF_INET, SOCK_STREAM)
    welcomeSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    welcomeSocket.bind(("", incoming_port))
    welcomeSocket.listen(4)

    while True:
        connectionSocket, addr = welcomeSocket.accept()
        thread = Thread(target=client_connection, args=(connectionSocket, addr,))
        thread.start()

    welcomeSocket.close()
