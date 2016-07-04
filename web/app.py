import os
import time
import json
from flask import Flask, Response
import requests
from werkzeug.contrib.cache import SimpleCache

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

auth_params = {
    "id": os.environ['GITHUB_ID'],
    "secret": os.environ['GITHUB_SECRET']
}

# todo: deployed should be memcached
cache = SimpleCache()

cachedtime_timeout = 5 * 60
get_members_timeout = 5 * 60

@app.route('/')
def hello():
    return "Hello World!"

@app.route('/settings')
def get_settings():
    return "APP_SETTINGS: {}".format(os.environ['APP_SETTINGS'])

@app.route("/time")
def get_time():
    return time.ctime()

@app.route('/members/<org>.json')
def get_members(org):
    cache_key = 'members/{}'.format(org)
    rv = cache.get(cache_key)
    if rv is None:
        r = requests.get('https://api.github.com/orgs/{}/members'.format(org), params=auth_params)
        r_json = json.loads(r.text)
        cache_time = get_time()
        r_package = {
            "payload": r_json,
            "cachetime": cache_time
        }
        rv = json.dumps(r_package)
        cache.set(cache_key, rv, timeout=get_members_timeout)
    return Response(rv, mimetype='application/json')

@app.route("/cachedtime")
def get_cachedtime():
    rv = cache.get('cachedtime')
    if rv is None:
        rv = get_time()
        cache.set('cachedtime', rv, timeout=cachedtime_timeout)
    return rv

if __name__ == '__main__':
    app.run()

