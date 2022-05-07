

class Target:

    def __init__(self, ip, service_id, service_name, custom={}):
        self.ip = ip
        self.custom = custom
        self.service_id = service_id
        self.service_name = service_name

    def getObj(self):
        return {'ip': self.ip, 'service_id': self.service_id, 'service_name': self.service_name, 'custom': self.custom}
