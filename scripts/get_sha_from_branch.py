import os
import requests
import json
import argparse
import re

def gist_branch_to_sha(gist_id, gist_branch, params):
    r = requests.get('https://api.github.com/gists/{}/{}'.format(gist_id, gist_branch), stream=True, params=params)
    content = r.raw.read(256, decode_content=True)
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

if __name__ == "__main__":
    # argparse
    parser = argparse.ArgumentParser(description='Fetch members of an org')
    parser.add_argument('-b','--branch', help='branch of gist', default="300b864c731f573f760835cb2fdcef2287cf8dd8")
    parser.add_argument('-i','--id', help='id of gist', default="a36efe08f5fc152227a6cffc3aa13297")
    parser.add_argument('-s','--secret', help='json credentials (or "none")', default="env")
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

    sha = gist_branch_to_sha(args.id, args.branch, params)
    if sha != None:
        print(sha)

    