import os
import time
import json
from flask import Flask, Response
from flask import render_template
import requests
from werkzeug.contrib.cache import SimpleCache
from flask_cache_response_decorator import cache

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

auth_params = {
    "id": os.environ['GITHUB_ID'],
    "secret": os.environ['GITHUB_SECRET']
}

# todo: deployed should be memcached
server_cache = SimpleCache()

default_timeout = 5 * 60

@app.route('/')
def hello():
    return "Hello World!"

@app.route('/settings')
def get_settings():
    return "APP_SETTINGS: {}".format(os.environ['APP_SETTINGS'])

### these versions of time / cachedtime are useful for debugging

# route that is live (dynamic)
@app.route("/time")
def get_time():
    return time.ctime()

# route that is live for client but cached for server
@app.route("/cachedtime_server")
def get_cachedtime_server():
    rv = server_cache.get('cachedtime')
    if rv is None:
        rv = get_time()
        server_cache.set('cachedtime', rv, timeout=default_timeout)
    return rv

# route that is live for server but cached for client
@app.route("/cachedtime_client")
@cache(default_timeout)
def get_cachedtime_client():
    return get_time()

# default will be to cache on server and client
@app.route("/cachedtime")
@cache(default_timeout)
def get_cachedtime():
    return get_cachedtime_server()

def fetch_members_json(org):
    cache_key = 'members/{}'.format(org)
    rv = server_cache.get(cache_key)
    if rv is None:
        r = requests.get('https://api.github.com/orgs/{}/members'.format(org), params=auth_params)
        r_json = json.loads(r.text)
        cache_time = get_time()
        r_package = {
            "payload": r_json,
            "cachetime": cache_time
        }
        rv = json.dumps(r_package)
        server_cache.set(cache_key, rv, timeout=default_timeout)
    return rv

@app.route('/members/<org>.raw.json')
@cache(default_timeout)
def get_members_raw_json(org):
    json = fetch_members_json(org)
    return Response(json, mimetype='application/json')

members_keys = ["login", "avatar_url", "html_url"]
def get_members_dict(org):
    j = fetch_members_json(org)
    members_list = json.loads(j)["payload"]
    filtered_list = []
    for d in members_list:
        filtered_list.append({ k: d[k] for k in members_keys })
    return filtered_list

@app.route('/members/<org>.json')
@cache(default_timeout)
def get_members_json(org):
    d = get_members_dict(org)
    rv = json.dumps(d)
    return Response(rv, mimetype='application/json')

@app.route('/members/<org>.html')
@cache(default_timeout)
def get_members_html(org):
    d = get_members_dict(org)
    return render_template("members.html",
                           org=org,
                           keys=members_keys,
                           members=d)

if __name__ == '__main__':
    app.run()

