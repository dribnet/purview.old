import requests
import json
import argparse

if __name__ == "__main__":
    # argparse
    parser = argparse.ArgumentParser(description='Fetch members of an org')
    parser.add_argument('-o','--org', help='filter by org', default=None)
    parser.add_argument('-i','--id', help='id of gist', default="ccd26455c5e6c1f8385655c175d4c3f0")
    parser.add_argument('-s','--secret', help='json credentials (or "none")', default="secret.json")
    args = parser.parse_args()

    params = {}
    if args.secret.lower() != "none":
        try:
            with open(args.secret) as json_file:
                params = json.load(json_file)
        except IOError:
            print("no secret.json file, requests will be unauthenticated")
        except:
            print("secret.json file could not be read, requests will be unauthenticated")

    # strangely, this only works when not authenticated?
    r = requests.get('https://api.github.com/gists/{}/forks'.format(args.id))
    print(r.url)
    print(r.text)

    