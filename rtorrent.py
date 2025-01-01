from xmlrpc.client import ServerProxy, Transport, SafeTransport
import base64
from urllib.parse import urlparse, urljoin
import os
from dotenv import load_dotenv
import ssl
import requests
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class RTorrentTransport(Transport):  # Changed from SafeTransport to Transport
    def __init__(self, use_datetime=False, use_builtin_types=False, username=None, password=None):
        super().__init__(use_datetime=use_datetime, use_builtin_types=use_builtin_types)
        self.username = username
        self.password = password
        
    def send_headers(self, connection, headers):
        if self.username and self.password:
            auth = f'{self.username}:{self.password}'
            auth_b64 = base64.b64encode(auth.encode()).decode()
            connection.putheader('Authorization', f'Basic {auth_b64}')
        connection.putheader('User-Agent', 'Python-xmlrpc')
        connection.putheader('Content-Type', 'text/xml')

class RTorrent:
    def __init__(self):
        load_dotenv()
        self.url = os.getenv('RTORRENT_URL')
        self.username = os.getenv('RTORRENT_USER')
        self.password = os.getenv('RTORRENT_PASS')
        
        # Create custom transport with auth and SSL context
        transport = RTorrentTransport(
            use_datetime=True,
            username=self.username,
            password=self.password
        )
        
        # Create XMLRPC proxy with custom transport
        self.server = ServerProxy(
            self.url,
            transport=transport,
            verbose=False,
            allow_none=True,
            use_builtin_types=True
        )

        # Add common labels/fields
        self.LABEL_FIELD = 'custom1'
        self.HASH_CHECK_FIELD = 'd.custom=hashcheck'
        self.MOVE_COMPLETED_FIELD = 'custom.move_completed'

    def add_torrent(self, torrent_url):
        """Add a torrent using its URL by first downloading the .torrent file"""
        try:
            session = requests.Session()
            session.verify = False
            
            print(f"Downloading torrent from: {torrent_url}")
            response = session.get(torrent_url)
            
            if response.status_code != 200:
                print(f"Error downloading torrent file: {response.status_code}")
                return False

            torrent_data = response.content
            if not torrent_data:
                print("Error: No torrent data received")
                return False
            
            print(f"Downloaded torrent size: {len(torrent_data)} bytes")
            torrent_b64 = base64.b64encode(torrent_data).decode()
            
            try:
                # Load and start the torrent in one command
                self.server.load.raw_start(
                    '',          # Empty string for target
                    torrent_b64, # Base64 encoded torrent data
                    'd.directory.set=/downloads',  # Set download directory
                    'd.custom1.set=added_by_script'  # Set label
                )
                
                # Verify the torrent was added by checking the list
                downloads = self.server.d.multicall2(
                    '',
                    'main',
                    'd.hash=',
                    'd.name='
                )
                
                if downloads:
                    latest = downloads[-1]
                    print(f"Successfully added torrent: {latest[1]} with hash: {latest[0]}")
                    return True
                    
            except Exception as e:
                print(f"Error in XMLRPC call: {e}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error adding torrent: {e}")
            import traceback
            traceback.print_exc()
            return False

    def list_torrents(self):
        """List all torrents with their details."""
        try:
            # Fix: Keep the '=' in method names as required by rTorrent
            downloads = self.server.d.multicall2(
                '',  # Empty string for current view
                'main',  # Default view name
                'd.hash=',  # Keep the '=' in method names
                'd.name=',
                'd.size_bytes=',
                'd.complete=',
                'd.directory=',
                'd.ratio=',
                'd.is_active=',
                'd.is_hash_checking='
            )
            
            torrent_list = []
            for items in downloads:
                info = {
                    'hash': items[0],
                    'name': items[1],
                    'size': items[2],
                    'completed': items[3],
                    'path': items[4],
                    'ratio': items[5],
                    'is_active': items[6],
                    'is_hash_checking': items[7]
                }
                torrent_list.append(info)
            return torrent_list
        except Exception as e:
            print(f"Error listing torrents: {e}")
            return []

    def remove_torrent(self, torrent_hash, with_data=False):
        """Remove a torrent by its hash."""
        try:
            if with_data:
                self.server.d.erase(torrent_hash)
            else:
                self.server.d.stop(torrent_hash)
                self.server.d.close(torrent_hash)
            return True
        except Exception as e:
            print(f"Error removing torrent: {e}")
            return False

    def get_version(self):
        """Get rTorrent version"""
        try:
            return self.server.system.client_version()
        except:
            return None

    def get_torrent_by_hash(self, hash):
        """Get specific torrent details by hash"""
        try:
            # First check if torrent exists
            downloads = self.server.d.multicall2(
                '',
                'main',
                'd.hash=',
                'd.name=',
                'd.directory=',
                'd.size_bytes=',
                'd.complete=',
                'd.custom1=',
                'd.down.rate=',
                'd.up.rate=',
                'd.is_active=',
                'd.is_open=',
                'd.is_hash_checking=',
                'd.peers_accounted=',
                'd.priority='
            )
            
            for torrent in downloads:
                if torrent[0] == hash:
                    return {
                        'hash': torrent[0],
                        'name': torrent[1],
                        'path': torrent[2],
                        'size': torrent[3],
                        'completed': torrent[4],
                        'label': torrent[5],
                        'download_rate': torrent[6],
                        'upload_rate': torrent[7],
                        'is_active': torrent[8],
                        'is_open': torrent[9],
                        'is_hash_checking': torrent[10],
                        'peers': torrent[11],
                        'priority': torrent[12]
                    }
            return None
        except Exception as e:
            print(f"Error getting torrent details: {e}")
            return None

    def add_torrent_from_data(self, data, download_dir=None, label=None):
        """Add a torrent using its raw data"""
        try:
            torrent_b64 = base64.b64encode(data).decode()
            
            if download_dir:
                # Fix: Use correct method names and parameters
                self.server.load.raw('', torrent_b64)
                # Get the hash of the newly added torrent
                downloads = self.server.d.multicall2('', 'main', 'd.hash=')
                latest_hash = downloads[-1][0]
                self.server.d.directory.set('', latest_hash, download_dir)
                
                if label:
                    self.server.d.custom1.set('', latest_hash, label)
            else:
                self.server.load.raw('', torrent_b64)
            
            return True
        except Exception as e:
            print(f"Error adding torrent from data: {e}")
            return False

    def set_torrent_priority(self, hash, priority):
        """Set torrent priority (0=off, 1=low, 2=normal, 3=high)"""
        try:
            self.server.d.priority.set('', hash, priority)
            return True
        except Exception as e:
            print(f"Error setting priority: {e}")
            return False

    def get_download_rate(self, hash):
        """Get current download rate in bytes/second"""
        try:
            return self.server.d.down.rate(hash)
        except Exception as e:
            print(f"Error getting download rate: {e}")
            return 0

    def pause_torrent(self, hash):
        """Pause a torrent"""
        try:
            self.server.d.stop(hash)
            return True
        except Exception as e:
            print(f"Error pausing torrent: {e}")
            return False

    def resume_torrent(self, hash):
        """Resume a torrent"""
        try:
            self.server.d.start(hash)
            return True
        except Exception as e:
            print(f"Error resuming torrent: {e}")
            return False

# Example usage:
if __name__ == "__main__":
    rtorrent = RTorrent()
    add_torrent = rtorrent.add_torrent("https://archlinux.org/releng/releases/2024.12.01/torrent/")
    
    # List current torrents
    torrents = rtorrent.list_torrents()
    for torrent in torrents:
        print(f"Name: {torrent['name']}, Completed: {torrent['completed']}")

    # Example adding a torrent (commented out)
    # rtorrent.add_torrent("http://example.com/sample.torrent")
