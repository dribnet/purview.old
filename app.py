import os
import time
import json
from flask import Flask, Response
from flask import render_template
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

def fetch_members_json(org):
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
    return rv

@app.route('/members/<org>.raw.json')
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
def get_members_json(org):
    d = get_members_dict(org)
    rv = json.dumps(d)
    return Response(rv, mimetype='application/json')

# consider this cache idea: https://gist.github.com/glenrobertson/954da3acec84606885f5

@app.route('/members/<org>.html')
def get_members_html(org):
    d = get_members_dict(org)
    return render_template("members.html",
                           org=org,
                           keys=members_keys,
                           members=d)

@app.route("/cachedtime")
def get_cachedtime():
    rv = cache.get('cachedtime')
    if rv is None:
        rv = get_time()
        cache.set('cachedtime', rv, timeout=cachedtime_timeout)
    return rv

if __name__ == '__main__':
    app.run()

