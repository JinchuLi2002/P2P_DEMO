import matplotlib.pyplot as plt
import socket
import shutil
import subprocess
import time
import threading
from multiprocessing import Process, Queue
import random
import os
import numpy as np

USE_RANDOM_WALK_ROUTING = True

BASE_PORT = 5000


def generate_known_peers(number_of_peers, exclude_port=None):
    """
    Generates a list of known peers excluding the peer that matches exclude_port.
    :param number_of_peers: Total number of peers in the experiment.
    :param exclude_port: Port of the peer to exclude from the list (typically the peer itself).
    :return: A list of tuples (host, port) for known peers.
    """
    return [('localhost', BASE_PORT + i) for i in range(number_of_peers) if (BASE_PORT + i) != exclude_port]


def start_peer(peer_id, port, shared_folder, number_of_peers):
    known_peers = generate_known_peers(number_of_peers, exclude_port=port)
    friend_peers = known_peers
    known_peers_str = str([(peer[0], peer[1]) for peer in known_peers])
    friend_peers_str = known_peers_str

    if USE_RANDOM_WALK_ROUTING:
        cmd = f'python peer.py {peer_id} localhost {port} "{shared_folder}" "{known_peers_str}"'
    else:
        cmd = f'python peer_friend.py {peer_id} localhost {port} "{shared_folder}" "{friend_peers_str}" "{known_peers_str}"'

    return subprocess.Popen(cmd, shell=True)


def run_experiment(experiment_type, parameters):
    experiment_results = []

    for parameter in parameters:
        if experiment_type == 'files':
            adjust_shared_folders(parameter)
            peers = start_peers(5)  # Assuming starting with 5 peers
            peers_info = [(f'localhost', 5000 + i) for i in range(5)]
        elif experiment_type == 'peers':
            peers = start_peers(parameter)
            adjust_shared_folders(10)  # Fixed number of files
            peers_info = [(f'localhost', 5000 + i) for i in range(parameter)]
        elif experiment_type == 'queries':
            adjust_shared_folders(10)  # Fixed number of files
            peers = start_peers(5)  # Fixed number of peers
            peers_info = [(f'localhost', 5000 + i) for i in range(5)]

        time.sleep(5)  # Allow network to stabilize

        latencies, throughput = perform_queries_and_measure(
            parameter if experiment_type == 'queries' else 10, peers_info, "file1.txt" if experiment_type != 'files' else f"file{random.randint(1, parameter)}.txt")

        stop_peers(peers)

        experiment_results.append({'parameter': parameter, 'latency': np.mean(
            latencies), 'throughput': throughput})
        print(
            f"Experiment with {parameter} {experiment_type}: Avg Latency = {np.mean(latencies)}, Throughput = {throughput}")

    return experiment_results


def adjust_shared_folders(number_of_files, number_of_peers=5):
    base_shared_dir = "./peer_folders"
    for i in range(number_of_peers):  # Now dynamically adjusting to the number of peers
        shared_folder = os.path.join(base_shared_dir, f"Peer{i+1}")
        if not os.path.exists(shared_folder):
            os.makedirs(shared_folder)
        else:
            for filename in os.listdir(shared_folder):
                file_path = os.path.join(shared_folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')

        for n in range(number_of_files):
            file_path = os.path.join(shared_folder, f"file{n+1}.txt")
            with open(file_path, 'w') as f:
                f.write(f"This is file {n+1} in {shared_folder}.\n")


def start_peers(number_of_peers):
    """Starts a specified number of peer processes, passing the total number of peers to each."""
    peers = []
    for i in range(number_of_peers):
        peer_id = f'Peer{i+1}'
        port = BASE_PORT + i
        shared_folder = f"./peer_folders/{peer_id}"
        peer = start_peer(peer_id, port, shared_folder, number_of_peers)
        peers.append(peer)
    return peers


def stop_peers(peers):
    """Stops the given peer processes."""
    for peer in peers:
        peer.terminate()
        peer.wait()


def perform_queries_and_measure(query_count, peers_info, requested_filename="file1.txt"):
    latencies = []
    successful_queries = 0
    start_time = time.time()

    for _ in range(query_count):
        peer_host, peer_port = random.choice(
            peers_info)  # Choose a random peer
        try:
            file_request_start = time.time()
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((peer_host, peer_port))
                sock.sendall(f"REQUEST:{requested_filename}".encode('utf-8'))
                response = b''
                while True:
                    part = sock.recv(1024)
                    if not part:
                        break
                    response += part
                file_request_end = time.time()

                if response:
                    successful_queries += 1
                    latencies.append(file_request_end - file_request_start)
        except Exception as e:
            print(f"Error requesting file from {peer_host}:{peer_port}: {e}")

    total_time = time.time() - start_time
    throughput = successful_queries / total_time if total_time > 0 else 0

    return latencies, throughput


def plot_graphs(results, title_prefix):
    parameters = [result['parameter'] for result in results]
    latencies = [result['latency'] for result in results]
    throughputs = [result['throughput'] for result in results]

    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(parameters, latencies, marker='o', linestyle='-')
    plt.title(f'{title_prefix} - Latency')
    plt.xlabel(f'# of {title_prefix}')
    plt.ylabel('Latency (s)')

    plt.subplot(1, 2, 2)
    plt.plot(parameters, throughputs, marker='o', linestyle='-')
    plt.title(f'{title_prefix} - Throughput')
    plt.xlabel(f'# of {title_prefix}')
    plt.ylabel('Throughput (requests/s)')

    plt.tight_layout()
    plt.show()


def run_experiment_and_plot(experiment_type, parameters):
    results = run_experiment(experiment_type, parameters)
    plot_graphs(results, experiment_type.capitalize())


def main():
    scenarios = {
        'files': [5, 10, 20],
        'queries': [10, 20, 40],
        'peers': [5, 10, 20]
    }

    for scenario, parameters in scenarios.items():
        print(f"Running {scenario} scenario experiments...")
        run_experiment_and_plot(scenario, parameters)


if __name__ == "__main__":
    main()
