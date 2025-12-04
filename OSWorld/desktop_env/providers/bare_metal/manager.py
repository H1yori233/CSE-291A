from desktop_env.providers.base import VMManager

class BareMetalManager(VMManager):
    def __init__(self):
        pass

    def create_vm(self, *args, **kwargs):
        pass

    def delete_vm(self, *args, **kwargs):
        pass
    
    def list_vms(self):
        return []
    
    def get_vm_ip(self, vm_name):
        return "127.0.0.1"
        
    def add_vm(self, *args, **kwargs):
        pass
        
    def check_and_clean(self, *args, **kwargs):
        pass
        
    def get_vm_path(self, *args, **kwargs):
        return "localhost"
        
    def initialize_registry(self, *args, **kwargs):
        pass
        
    def list_free_vms(self, *args, **kwargs):
        return ["localhost"]
        
    def occupy_vm(self, *args, **kwargs):
        pass
