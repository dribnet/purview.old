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

def time_get_raw_json(args):
    return '{{"time": "{}"}}'.format(time.ctime())

time_keys = [ "time" ]
time_cache_key = "time"

def fetch_and_cache_json(raw_get_fn, args, cache_key):
    rv = server_cache.get(cache_key)
    if rv is None:
        rv = raw_get_fn(args)
        r_json = json.loads(rv)
        cache_time = time.ctime()
        r_package = {
            "payload": r_json,
            "cachetime": cache_time
        }
        rv = json.dumps(r_package)
        server_cache.set(cache_key, rv, timeout=default_timeout)
    return rv

def fetch_filtered_json(raw_get_fn, args, cache_key, filter_keys):
    if cache_key == None:
        rv = raw_get_fn(args)
        raw_map = json.loads(rv)
    else:
        rv = fetch_and_cache_json(raw_get_fn, args, cache_key)
        raw_map = json.loads(rv)["payload"]
    filtered_list = []
    for k,v in raw_map.items():
        filtered_list.append({ k: v for k in filter_keys })
    return json.dumps(filtered_list)

# route that is live (dynamic)
@app.route("/time.raw.live.json")
def get_time_live():
    return time_get_raw_json(None)

@app.route("/time.raw.json")
@cache(default_timeout)
def get_time_raw():
    return fetch_and_cache_json(time_get_raw_json, None, time_cache_key)

@app.route("/time.live.json")
def get_time_live_json():
    return fetch_filtered_json(time_get_raw_json, None, None, time_keys)

@app.route("/time.json")
@cache(default_timeout)
def get_time_json():
    return fetch_filtered_json(time_get_raw_json, None, time_cache_key, time_keys)

@app.route("/time.live.html")
def get_time_live_html():
    j = fetch_filtered_json(time_get_raw_json, None, None, time_keys)
    return render_template("time.html",
                           time=j)

@app.route("/time.html")
@cache(default_timeout)
def get_time_html():
    j = fetch_filtered_json(time_get_raw_json, None, time_cache_key, time_keys)
    return render_template("time.html",
                           time=j)

### now do something similar for "org members"

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

