'''Simple server program'''
import socket

HOST = '127.0.0.1'
PORT = 4300


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen(1)
        print('Listening on port {}'.format(PORT))
        conn, addr = s.accept()
        with conn:
            print('Accepted connection from {}'.format(addr))
            while True:
                # Receives 1024bytes of data maximum.
                data = conn.recv(1024)
                if not data:
                    print('Connection closed')
                    break
                # Here we decode the name passed in as cmd line argument on the client side 
                # and greet the user. 
                conn.sendall("Hello, {}".format(data.decode()).encode())


if __name__ == '__main__':
    main()
