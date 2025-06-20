import requests

#from app.log import logger

class JmClient:
    def __init__(self, id):
        self.id = id

    def download(self):
        data = {'album_id': str(self.id)}
        response = requests.post('http://100.66.1.2:18000/download-album', json=data)
        if response.status_code != 200:
            return True, ""
        return False, response.json()

if __name__ == "__main__":
    client = JmClient("438696")
    client.download()
