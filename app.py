import os
import time
import json
import re
from flask import Flask, Response, url_for
from flask import render_template
import requests
from werkzeug.contrib.cache import SimpleCache
from flask_cache_response_decorator import cache

app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])

auth_params = {
    "client_id": os.environ['GITHUB_ID'],
    "client_secret": os.environ['GITHUB_SECRET']
}

# todo: deployed should be memcached
server_cache = SimpleCache()

default_timeout = 5 * 60

@app.route('/')
def hello():
    return render_template("home.html")

@app.route('/settings')
def get_settings():
    return "APP_SETTINGS: {}".format(os.environ['APP_SETTINGS'])

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

def nested_extract(m, key):
    keys = key.split("/")
    cur_m = m
    for k in keys:
        cur_m = cur_m[k]
    return cur_m

def fetch_filtered_json(raw_get_fn, args, cache_key, filter_keys):
    if cache_key == None:
        rv = raw_get_fn(args)
        raw_list = json.loads(rv)
    else:
        rv = fetch_and_cache_json(raw_get_fn, args, cache_key)
        raw_list = json.loads(rv)["payload"]
    filtered_list = []
    for e in raw_list:
        filtered_list.append({ k: nested_extract(e,k) for k in filter_keys })
    return json.dumps(filtered_list)

# here is the core time api
def time_get_raw_json(args):
    return '[{{"time": "{}"}}]'.format(time.ctime())

time_keys = [ "time" ]
time_cache_key = "time"

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

# here is the core org members api
def members_get_raw_json(org):
    r = requests.get('https://api.github.com/orgs/{}/members'.format(org), params=auth_params)
    return r.text

members_keys = ["login", "avatar_url", "html_url"]
def members_cache_key(org):
    return "members/{}".format(org)

# route that is live (dynamic)
@app.route("/members/<org>.raw.live.json")
def get_members_raw_live(org):
    return members_get_raw_json(org)

@app.route("/members/<org>.raw.json")
@cache(default_timeout)
def get_members_raw(org):
    return fetch_and_cache_json(members_get_raw_json, org, members_cache_key(org))

@app.route("/members/<org>.live.json")
def get_members_live_json(org):
    return fetch_filtered_json(members_get_raw_json, org, None, members_keys)

@app.route("/members/<org>.json")
@cache(default_timeout)
def get_members_json(org):
    return fetch_filtered_json(members_get_raw_json, org, members_cache_key(org), members_keys)

@app.route("/members/<org>.live.html")
def get_members_live_html(org):
    j = fetch_filtered_json(members_get_raw_json, org, None, members_keys)
    return render_template("members.html",
                           org=org, keys=members_keys, members=json.loads(j))

@app.route("/members/<org>.html")
@cache(default_timeout)
def get_members_html(org):
    j = fetch_filtered_json(members_get_raw_json, org, members_cache_key(org), members_keys)
    return render_template("members.html",
                           org=org, keys=members_keys, members=json.loads(j))

### should now be easy to add "list gist forks"

# here is the core list gists forks api
def forks_get_raw_json(gist_id):
    r = requests.get('https://api.github.com/gists/{}/forks'.format(gist_id), params=auth_params)
    return r.text

forks_keys = ["id", "owner/login", "owner/avatar_url", "owner/html_url"]
def forks_cache_key(gist_id):
    return "forks/{}".format(gist_id)

@app.route("/forks/<gist_id>.raw.json")
@cache(default_timeout)
def get_forks_raw(gist_id):
    return fetch_and_cache_json(forks_get_raw_json, gist_id, forks_cache_key(gist_id))

@app.route("/forks/<gist_id>.json")
@cache(default_timeout)
def get_forks_json(gist_id):
    return fetch_filtered_json(forks_get_raw_json, gist_id, forks_cache_key(gist_id), forks_keys)

@app.route("/forks/<gist_id>.html")
@cache(default_timeout)
def get_forks_html(gist_id):
    j = fetch_filtered_json(forks_get_raw_json, gist_id, forks_cache_key(gist_id), forks_keys)
    return render_template("forks.html",
                           gist_id=gist_id, keys=forks_keys, forks=json.loads(j))

# here is the core purview versions api
# this could be set from env, etc. in future
js_settings = {
    "blocks_run_root": "http://bl.ocks.org/",
    "purview_file_root": "http://purview-blocks.herokuapp.com/"
}

def gist_branch_to_sha(gist_id, gist_branch):
    r = requests.get('https://api.github.com/gists/{}/{}'.format(gist_id, gist_branch), stream=True, params=auth_params)
    content = r.raw.read(256, decode_content=True).decode("utf-8")
    print("CONTENT: ", content)
    if content.startswith('{"url":'):
        match = re.search('^{"url":"([^"]*)"', content)
        if match == None:
            return None
        url = match.group(1)
        parts = url.split("/")
        return parts[-1]
    else:
        print("branch {} not found: {}".format(gist_branch, content))
        return None

def versions_get_raw_json(gist_id):
    purview_text = "null"
    sha_of_purview_branch = gist_branch_to_sha(gist_id, "purview")
    if sha_of_purview_branch is not None:
        r = requests.get('http://purview-blocks.herokuapp.com/anonymous/raw/{}/{}/purview.json'.format(gist_id, sha_of_purview_branch))
        purview_text = r.text

    r = requests.get('https://api.github.com/gists/{}'.format(gist_id), params=auth_params)
    return '{"purview":' + purview_text + ', "api":' + r.text + '}'

def versions_cache_key(gist_id):
    return "versions/{}".format(gist_id)

@app.route("/versions/<gist_id>.raw.json")
@cache(default_timeout)
def get_versions_raw(gist_id):
    return fetch_and_cache_json(versions_get_raw_json, gist_id, versions_cache_key(gist_id))

def history_to_commits(d):
    commits = [[v["version"], v["committed_at"]] for v in d["history"]]
    return {"commits": commits}

def history_to_records(gist_id, login, desc, api):
    meta = {
        "login": login,
        "id": gist_id,
        "description": desc,
        "blocks_link": js_settings["blocks_run_root"] + login + "/" + gist_id
    }
    records = [{
            "login": login,
            "id": gist_id,
            "sha": h["version"],
            "description": None,
            "created_at": h["committed_at"],
            "updated_at": h["committed_at"]
        } for h in api["history"]]
    return {"meta": meta, "records": records}

def purview_commits_to_records(gist_id, login, desc, commits):
    meta = {
        "login": login,
        "id": gist_id,
        "description": desc,
        "blocks_link": js_settings["blocks_run_root"] + login + "/" + gist_id
    }
    records = [{
            "login": login,
            "id": gist_id,
            "sha": c[0],
            "description": c[1],
            "created_at": "unknown",
            "updated_at": "unknown"
        } for c in commits]
    return {"meta": meta, "records": records}

def get_converted_versions(gist_id):
    d = json.loads(fetch_and_cache_json(versions_get_raw_json, gist_id, versions_cache_key(gist_id)))
    payload = d["payload"]
    login = payload["api"]["owner"]["login"]
    desc = payload["api"]["description"]
    if payload["purview"] is not None and "commits" in payload["purview"]:
        return purview_commits_to_records(gist_id, login, desc, payload["purview"]["commits"])
    return history_to_records(gist_id, login, desc, payload["api"])

@app.route("/versions/<gist_id>.json")
@cache(default_timeout)
def get_versions_json(gist_id):
    return json.dumps(get_converted_versions(gist_id))

@app.route("/versions/<gist_id>.html")
@cache(default_timeout)
def get_versions_html(gist_id):
    d = get_converted_versions(gist_id)
    j = json.dumps(d)
    return render_template("versions.html", json=j,
        meta=d["meta"], num_versions=len(d["records"]),
        js_settings=js_settings, gist_id=gist_id)


if __name__ == '__main__':
    app.run()

