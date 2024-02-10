import os

base_dir = './peers'

peers = {
    'Peer1': 5001,
    'Peer2': 5002,
    'Peer3': 5003,
    'Peer4': 5004,
    'Peer5': 5005,
}

for peer, port in peers.items():
    peer_dir = os.path.join(base_dir, f"{peer}_{port}")
    os.makedirs(peer_dir, exist_ok=True)

    for i in range(1, 6):
        file_path = os.path.join(peer_dir, f"file{i}.txt")
        with open(file_path, 'w') as f:
            f.write(f"This is file {i} in {peer} shared folder.\n")

print("Directories and files created successfully.")
