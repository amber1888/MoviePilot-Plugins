import requests

class JmClient:
    def __init__(self, id):
        self.id = id

    def download(self):
        data = {'album_id': str(self.id)}
        response = requests.post('http://192.168.1.96:18000/download-album', json=data)
        if response.status_code == 200:
            return True, ""
        return False, response.json()

