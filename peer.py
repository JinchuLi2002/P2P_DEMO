import socket
import threading
import os
import sys
import time
import ast
import random


class RandomWalkPeer:
    def __init__(self, peer_id, host, port, shared_folder, known_peers):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.shared_folder = shared_folder
        # Convert string representation of list to list
        self.known_peers = ast.literal_eval(known_peers)
        os.makedirs(self.shared_folder, exist_ok=True)
        self.files = self.scan_shared_folder()

    def scan_shared_folder(self):
        """Scan the shared folder for files to share."""
        return os.listdir(self.shared_folder)

    def serve_file(self, client_socket, filename):
        """Serve a file to another peer."""
        try:
            with open(os.path.join(self.shared_folder, filename), 'rb') as f:
                client_socket.sendall(f.read())
            print(f"File {filename} sent by {self.peer_id}.")
        except FileNotFoundError:
            print(f"File not found by {self.peer_id}.")
        client_socket.close()

    def handle_connection(self, client_socket):
        """Handle incoming connection."""
        data = client_socket.recv(1024).decode('utf-8')
        command, filename = data.split(":")
        if command == "REQUEST":
            if filename in self.files:
                self.serve_file(client_socket, filename)
            else:
                self.forward_request(filename)

    def forward_request(self, filename):
        """Forward a file request to another randomly selected peer."""
        if self.known_peers:
            next_peer_host, next_peer_port = random.choice(self.known_peers)
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((next_peer_host, next_peer_port))
                    s.sendall(f"REQUEST:{filename}".encode('utf-8'))
                    print(
                        f"Request for {filename} forwarded by {self.peer_id} to {next_peer_host}:{next_peer_port}")
            except Exception as e:
                print(
                    f"Error forwarding request from {self.peer_id} to {next_peer_host}:{next_peer_port}: {e}")

    def start_server(self):
        """Start the peer server to accept connections."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(
            f"RandomWalkPeer {self.peer_id} listening as {self.host}:{self.port}")
        while True:
            client_socket, _ = server_socket.accept()
            threading.Thread(target=self.handle_connection,
                             args=(client_socket,)).start()

    def run(self):
        threading.Thread(target=self.start_server, daemon=True).start()


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print("Usage: python peer.py <peer_id> <host> <port> <shared_folder> <known_peers>")
        sys.exit(1)

    peer_id = sys.argv[1]
    host = sys.argv[2]
    port = int(sys.argv[3])
    shared_folder = sys.argv[4]
    known_peers = sys.argv[5]

    peer = RandomWalkPeer(peer_id, host, port, shared_folder, known_peers)
    peer.run()

    while True:
        time.sleep(1)
