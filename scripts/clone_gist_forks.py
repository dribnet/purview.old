import os
import shutil
import requests
import json
import argparse

def ensure_directory_cleaned(dirname):
    if os.path.exists(dirname):
        shutil.rmtree(dirname)
    os.mkdir(dirname)

def clone_all_forks(forks_json, outdir):
    ensure_directory_cleaned(outdir)
    forks = json.loads(forks_json)
    print("{} forks".format(len(forks)))
    for f in forks:
        pull_url = f["git_pull_url"]
        owner = f["owner"]["login"]
        print("Cloning {}: {}".format(owner, pull_url))
        command = "git clone {} {}/{}".format(pull_url, outdir, owner)
        os.system(command)

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
    clone_all_forks(test_text, args.outdir)
    # r = requests.get('https://api.github.com/gists/{}/forks'.format(args.id), params=params)
    # clone_all_forks(r.text, args.outdir)

    