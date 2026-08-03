import requests
s = requests.Session()
login = s.post('http://127.0.0.1:8000/api/auth/login', json={'identifier':'admin','password':'YourStrongPassword1'})
print('login_status', login.status_code)
print(login.text)
if login.ok:
    agents = s.get('http://127.0.0.1:8000/api/agents')
    print('agents_status', agents.status_code)
    print(agents.text)
