import toml
import subprocess
import os
import socket
import time
import struct
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

RELOAD_BACKOFF = 5  # seconds
MAX_RELOAD_ATTEMPTS = 6

SOCKET_MESSAGE_TO_GET_PID = b""

def modify_config(file_path, config_path):
    modified = False
    with open(file_path, 'r') as file:
        config = toml.load(file)

    # Check if config_path is correctly set
    if 'plugins' not in config or 'io.containerd.grpc.v1.cri' not in config['plugins']:
        config.setdefault('plugins', {})
        config['plugins'].setdefault('io.containerd.grpc.v1.cri', {})
    if 'registry' not in config['plugins']['io.containerd.grpc.v1.cri']:
        config['plugins']['io.containerd.grpc.v1.cri']['registry'] = {}

    if config['plugins']['io.containerd.grpc.v1.cri']['registry'].get('config_path') != "/etc/containerd/certs.d":
        config['plugins']['io.containerd.grpc.v1.cri']['registry']['config_path'] = "/etc/containerd/certs.d"
        modified = True


### NEW CODE START
    # Read the registries from the key-value pair file
    registries_file = os.path.join(config_path, 'registries')
    # Read the registries from the key-value pair file
    registries_file = os.path.join(config_path, 'registries')
    if os.path.exists(registries_file):
        registries = {}
        with open(registries_file, 'r') as f:
            for line in f:
                if '=' in line:
                    repo, mirror = line.strip().split('=', 1)
                    registries[repo.strip()] = mirror.strip()
    for repo, mirror in registries.items():
        repo_dir = os.path.join('/etc/containerd/certs.d', repo)
        os.makedirs(repo_dir, exist_ok=True)
        hosts_file = os.path.join(repo_dir, 'hosts.toml')

        if os.path.exists(hosts_file):
            # Read existing configuration
            with open(hosts_file, 'r') as existing_file:
                existing_config = toml.load(existing_file)
        
            # Check if the repo and mirror already exist with the same configuration
            if 'server' in existing_config and existing_config['server'] == f'https://{repo}':
                if 'host' in existing_config:
                    existing_hosts = existing_config['host']
                    if (f'https://{mirror}' in existing_hosts and existing_hosts[f'https://{mirror}'] == {'capabilities': ['pull', 'resolve']}) and (f'https://{repo}' in existing_hosts and existing_hosts[f'https://{repo}'] == {'capabilities': ['pull', 'resolve']}):
                        logger.info(f"Skipping update for {repo} as configuration already exists.")
                        continue

        # Generate hosts.toml using the new structure
        hosts_config = {
            'server': f'https://{repo}',
            'host': {
                f'https://{mirror}': {
                    'capabilities': ['pull', 'resolve']
                },
                f'https://{repo}': {
                    'capabilities': ['pull', 'resolve']
                }
            }
        }

        with open(hosts_file, 'w') as host_file:
            toml.dump(hosts_config, host_file)
        logger.info(f"Updated or created hosts.toml for {repo}")
        modified = True
    return modified



### NEW CODE END


def signal_containerd(socket_path):
    logger.info("Sending SIGHUP signal to containerd")

    def retriable():
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(socket_path)
            
            # Set SO_PASSCRED socket option
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            
            # Send message to get PID
            sock.sendmsg([SOCKET_MESSAGE_TO_GET_PID], [], 0, (socket.CMSG_SPACE(4), 0))
            
            # Receive control message
            data, ancdata, _, _ = sock.recvmsg(1, socket.CMSG_SPACE(4))
            for cmsg_level, cmsg_type, cmsg_data in ancdata:
                if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_CREDENTIALS:
                    pid, uid, gid = struct.unpack("III", cmsg_data[:12])
                    
                    # Send SIGHUP to the process
                    try:
                        os.kill(pid, signal.SIGHUP)
                        logger.info(f"SIGHUP signal sent to PID: {pid}")
                        return None
                    except ProcessLookupError:
                        return "Process with PID does not exist"
                    except PermissionError:
                        return "Permission denied when sending signal"
                    except Exception as e:
                        return f"Error sending SIGHUP: {e}"
            return "Failed to retrieve PID from control message"
        
        except Exception as e:
            return f"Error in socket operations: {e}"
        finally:
            sock.close()

    error = None
    for attempt in range(MAX_RELOAD_ATTEMPTS):
        error = retriable()
        if error is None:
            break
        if attempt == MAX_RELOAD_ATTEMPTS - 1:
            break
        logger.warning(f"Error signaling containerd, attempt {attempt+1}/{MAX_RELOAD_ATTEMPTS}: {error}")
        time.sleep(RELOAD_BACKOFF)
    
    if error:
        logger.warning(f"Max retries reached {MAX_RELOAD_ATTEMPTS}/{MAX_RELOAD_ATTEMPTS}, aborting")
        return error

    logger.info("Successfully signaled containerd")
    return None




if __name__ == "__main__":
    config_file = '/etc/containerd/config.toml'
    config_path = '/etc/containerd-config/'  # Path where configmap data is mounted
    while True:
        try:
            if modify_config(config_file, config_path):
                signal_containerd(socket)
            else:
                logger.info("No changes made to containerd configuration.")
        except Exception as e:
            logger.error(f"An error occurred while updating containerd configuration: {e}")
        
        # Sleep for 30 minutes (1800 seconds)
        time.sleep(1800)
