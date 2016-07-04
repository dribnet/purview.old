import requests
import json
import argparse

if __name__ == "__main__":
    # argparse
    parser = argparse.ArgumentParser(description='Fetch members of an org')
    parser.add_argument('-u','--user', help='user', default="dribnet")
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

    r = requests.get('https://api.github.com/users/{}/orgs'.format(args.user), params=params)
    print(r.url)
    print(r.text)

    