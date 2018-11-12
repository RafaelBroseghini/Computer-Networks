"""Python Web server implementation"""
from socket import socket, AF_INET, SOCK_STREAM
from datetime import datetime
import sys
import json

server = socket(AF_INET, SOCK_STREAM)

ADDRESS = "127.0.0.2"  # Local client is going to be 127.0.0.1
PORT = 4300  # Open http://127.0.0.2:4300 in a browser
LOGFILE = "webserver.log"
ALICE_LENGTH = str(sum(len(word) for word in open("alice30.txt").readlines()))


def write_to_json(data: bytearray):
    json_array = data.decode().split("\r\n")[1:len(data.decode().split("\r\n"))-2]
    if len(json_array) > 0:
        json_data = {}
        for h in range(len(json_array)):
            subpart = json_array[h].split(": ")
            key, value = subpart[0], subpart[1]
            json_data[key] = value

        return json_data

def write_to_log(uri_path: str, data: dict):
    with open(LOGFILE, "a+") as outfile:
        time, uri, client, user_agent = datetime.now(), uri_path, "127.0.0.1", data["User-Agent"]
        outfile.write("{} | {} | {} | {}\n".format(time, uri, client, user_agent))


def build_and_send_response(conn: socket, data: list):
    headers = {
            "FULL HTTP"         : "",
            "Content-Length"    : "Content-Length: ",
            "Content-Type"      : "Content-Type: text/plain; charset=utf-8\r\n",
            "Date"              : "Date: {}".format(str(datetime.now()) + "\r\n"),
            "Last-Modified"     : "Last-Modified: Friday, August 29, 2018 11:00 AM\r\n",
            "Server"            : "Server: CS430-Rafa\r\n\r\n"
        }

    if data[0] != "GET":
        content = "<html><body><h1>Use GET to retrieve resources.</h1></body></html>\r\n"

        headers["FULL HTTP"] = "HTTP/1.1 405 Method Not Allowed\r\n"
        headers["Content-Length"] = "Content-Length: {}\r\n".format(len(content))

        full_header = [headers[h] for h in headers if h != "Last-Modified"]

        for h in full_header:
            conn.send(h.encode())

        conn.send("{}".format(content).encode())

    elif data[1] != "/alice30.txt":
        content = "<html><body><h1>404 Not Found.</h1></body></html>\r\n"

        headers["FULL HTTP"] = "HTTP/1.1 404 Not Found\r\n"
        headers["Content-Length"] = "Content-Length: {}\r\n".format(len(content))

        full_header = [headers[h] for h in headers if h != "Last-Modified"]

        for h in full_header:
            conn.send(h.encode())

        conn.send("{}".format(content).encode())

    else:
        headers["FULL HTTP"] = "HTTP/1.1 200 OK\r\n"
        headers["Content-Length"] += ALICE_LENGTH + "\r\n"

        response = [h.encode() for h in headers.values()]
        content = [word.encode() for word in open("alice30.txt").readlines()]

        for h in response:
            conn.send(h)

        for line in content:
            conn.send(line)

def main():
    """Main loop"""
    with server as s:
        s.bind((ADDRESS, PORT))
        s.listen(1)
        print('Listening on port {}'.format(PORT))
        conn, addr = s.accept()
        with conn:
            print('Accepted connection from {}'.format(addr))
            while True:
                # Receives 1024bytes of data maximum.
                data = conn.recv(1024)

                json_data = write_to_json(data)
                
                data = data.decode().split()

                if len(data) > 0 and len(json_data) > 0:
                    uri = data[1]
                    write_to_log(uri, json_data)
                    build_and_send_response(conn, data)
                else:
                    print('Connection closed')
                    exit()

if __name__ == "__main__":
    main()
