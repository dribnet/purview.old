import os
from flask import Flask, Response
import requests

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

auth_params = {
    "id": os.environ['GITHUB_ID'],
    "secret": os.environ['GITHUB_SECRET']
}

@app.route('/')
def hello():
    return "Hello World!"

@app.route('/settings')
def get_settings():
    return "APP_SETTINGS: {}".format(os.environ['APP_SETTINGS'])

@app.route('/members/<org>.json')
def get_members(org):
    r = requests.get('https://api.github.com/orgs/{}/members'.format(org), params=auth_params)
    return Response(r.text, mimetype='application/json')

if __name__ == '__main__':
    app.run()

