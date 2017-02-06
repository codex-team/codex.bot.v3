import requests
from configuration.globalcfg import URL

token = input('Input token: ')

req = requests.post("{}notifications/{}".format(URL, token), {'message': 'Hello, my name is Test Codex Bot'}, verify=False)
print(req.content)
