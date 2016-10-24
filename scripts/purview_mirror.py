import os
import shutil
import requests
import json
import argparse
from web.app import fetch_purview_records
from flask import render_template_string, Flask
import flask
import sys
import subprocess

# example
# PYTHONPATH=.:./web python scripts/purview_mirror.py -d archive/ps3

def ensure_directory_cleaned(dirname):
    if os.path.exists(dirname):
        shutil.rmtree(dirname)
    os.mkdir(dirname)

def clone_all_forks(gist_id, forks_json, outdir):
    ensure_directory_cleaned(outdir)
    forks = json.loads(forks_json)
    print("{} forks".format(len(forks)))

    with open("web/templates/versions.html") as template_file:
        template_text = template_file.read()

    for f in forks:
        print(f)
        # clone master branch
        pull_url = f["git_pull_url"]
        owner = f["owner"]["login"]
        desc = f["description"]
        print("Cloning {}: {}".format(owner, pull_url))
        os.mkdir("{}/{}".format(outdir, owner))
        command = "git clone {} {}/{}/master".format(pull_url, outdir, owner)
        os.system(command)

        master_sha = subprocess.getoutput("cd {}/{}/master && git rev-parse HEAD".format(outdir, owner))

        # now purview branch
        try:
            purview_dir = "{}/{}/purview".format(outdir, owner)
            os.mkdir(purview_dir)
            os.system("cd {} && git init".format(purview_dir))
            os.system("cd {} && git remote add origin ../master".format(purview_dir))
            os.system("cd {} && git fetch origin remotes/origin/purview".format(purview_dir))
            os.system("cd {} && git reset --hard FETCH_HEAD".format(purview_dir))


            # now open purview.json and make the other directories
            with open("{}/purview.json".format(purview_dir)) as json_file:
                purview_text = json_file.read()
                purview_map = json.loads(purview_text)
        except:
            purview_map = {"commits": []}

        known_shas = [c["sha"] for c in purview_map["commits"]]
        if not master_sha in known_shas:
            commits = purview_map["commits"]
            commits.insert(0, {"sha": master_sha, "name": "master"})
            purview_map["commits"] = commits

        purview_records = fetch_purview_records(gist_id, owner, purview_map)
        js_settings = {
            "blocks_run_root": "",
            "purview_file_root": ""
        }
        meta = {
            "login": owner,
            "id": gist_id,
            "description": desc,
            "blocks_link": js_settings["blocks_run_root"] + owner + "/" + gist_id
        }
        d = {"records": purview_records, "meta": meta}
        j = json.dumps(d)

        sha_path = "/{}".format(gist_id)
        app = flask.Flask(__name__)
        @app.route(sha_path)
        def index():
            return render_template_string(template_text, json=j,
                meta=d["meta"], js_settings=js_settings, gist_id=gist_id)
        rv = app.test_client().get(sha_path)

        text_file = open("{}/{}/index.html".format(outdir, owner), "wb")
        text_file.write(rv.data)
        text_file.close()

        # now put all files in place
        raw_dir = "{}/{}/{}/raw/{}".format(outdir, owner, owner, gist_id)
        os.makedirs(raw_dir)
        link_src = "raw/{}".format(gist_id)
        link_dst = "{}/{}/{}/{}".format(outdir, owner, owner, gist_id)
        os.symlink(link_src, link_dst)

        for c in purview_map["commits"]:
            sha = c["sha"]

            sha_dir = "{}/{}".format(raw_dir, sha)
            os.mkdir(sha_dir)
            os.system("cd {} && git init".format(sha_dir))
            os.system("cd {} && git remote add origin ../../../../master".format(sha_dir))
            os.system("cd {} && git fetch origin".format(sha_dir))
            os.system("cd {} && git reset --hard {}".format(sha_dir, sha))


if __name__ == "__main__":
    # argparse
    parser = argparse.ArgumentParser(description='Fetch members of an org')    
    parser.add_argument('-o','--org', help='filter by org', default=None)
    parser.add_argument('-i','--id', help='id of gist', default="a937cdee02e0ee311d500000cf9e7a6c")
    parser.add_argument('-s','--secret', help='json credentials (or "none")', default="env")
    parser.add_argument('-d','--output-directory', dest='outdir',
        help='output directory for cloning', default="cloned")
    args = parser.parse_args()

    params = {}
    if args.secret.lower() == "env":
        params = {
            "client_id": os.environ['GITHUB_ID'],
            "client_secret": os.environ['GITHUB_SECRET']
        }
    elif args.secret.lower() != "none":
        try:
            with open(args.secret) as json_file:
                params = json.load(json_file)
        except IOError:
            print("no secret.json file, requests will be unauthenticated")
        except:
            print("secret.json file could not be read, requests will be unauthenticated")

    with open("test.json") as json_file:
        test_text=json_file.read()
    clone_all_forks(args.id, test_text, args.outdir)
    # r = requests.get('https://api.github.com/gists/{}/forks'.format(args.id), params=params)
    # print(r.text)
    # clone_all_forks(r.text, args.outdir)

    