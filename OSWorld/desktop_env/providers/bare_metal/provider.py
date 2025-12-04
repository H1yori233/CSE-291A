from desktop_env.providers.base import Provider

class BareMetalProvider(Provider):
    def __init__(self):
        super().__init__()

    def start_emulator(self, *args, **kwargs):
        # We are already running in the environment, so nothing to start
        pass

    def get_ip_address(self, *args, **kwargs):
        # Format: ip:server_port:chromium_port:vnc_port:vlc_port
        # We need to map these to ports that are actually listening on localhost
        return "127.0.0.1:5000:9222:8006:8080"

    def stop_emulator(self, *args, **kwargs):
        # Don't stop the host!
        pass
    
    def save_state(self, *args, **kwargs):
        pass
        
    def revert_to_snapshot(self, *args, **kwargs):
        return "localhost"
