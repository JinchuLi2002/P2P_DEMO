import socket
import threading
import os
import sys
import time
import ast


class FriendPeer:
    def __init__(self, peer_id, host, port, shared_folder, friend_peers, known_peers):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.shared_folder = shared_folder
        self.known_peers = known_peers  # List of peer addresses
        # Ensure the shared folder exists
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
            print(f"File {filename} sent.")
        except FileNotFoundError:
            print("File not found.")
        client_socket.close()

    def handle_connection(self, client_socket):
        """Handle incoming connection."""
        data = client_socket.recv(1024).decode('utf-8')
        command, filename = data.split(":")
        if command == "REQUEST":
            self.serve_file(client_socket, filename)

    def start_server(self):
        """Start the peer server to accept connections."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen()
        print(
            f"FriendPeer {self.peer_id} listening as {self.host}:{self.port}")
        while True:
            client_socket, _ = server_socket.accept()
            threading.Thread(target=self.handle_connection,
                             args=(client_socket,)).start()

    def request_file(self, filename):
        """Request a file from friends first, then from known peers if not found."""
        peers_tried = set()
        for peer in self.friend_peers + self.known_peers:
            if peer in peers_tried:
                continue  # Avoid duplicate requests
            peer_host, peer_port = peer
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((peer_host, peer_port))
                    s.sendall(f"REQUEST:{filename}".encode('utf-8'))
                    response_file = os.path.join(
                        self.shared_folder, f"downloaded_{filename}")
                    with open(response_file, 'wb') as f:
                        while True:
                            data = s.recv(1024)
                            if not data:
                                break
                            f.write(data)
                    print(
                        f"File {filename} downloaded from {peer_host}:{peer_port}.")
                    return
            except Exception as e:
                print(
                    f"Error requesting file from {peer_host}:{peer_port}: {e}")
            peers_tried.add(peer)
        print(f"File {filename} not found on any peer.")

    def run(self):
        threading.Thread(target=self.start_server, daemon=True).start()


if __name__ == "__main__":
    if len(sys.argv) < 7:
        print("Usage: python peer_friend.py <peer_id> <host> <port> <shared_folder> <friend_peers> <known_peers>")
        sys.exit(1)

    peer_id = sys.argv[1]
    host = sys.argv[2]
    port = int(sys.argv[3])
    shared_folder = sys.argv[4]
    friend_peers = sys.argv[5]
    known_peers = sys.argv[6]

    peer = FriendPeer(peer_id, host, port, shared_folder,
                      friend_peers, known_peers)
    peer.run()

    # Keep the main thread alive
    while True:
        time.sleep(1)
