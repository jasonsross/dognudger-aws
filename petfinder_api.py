import requests
import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv('flask_app/.env')
import pandas as pd

KEY = os.environ['PETFINDER_KEY']
SECRET = os.environ['PETFINDER_SECRET']

search_url = "https://www.petfinder.com/search/dogs-for-adoption/us/or/{zip}?breed%5B0%5D={breed}&distance=100"
base_api_url = """ https://api.petfinder.com/v2/animals?type=dog&breed={breed}&location={zip}&sort=distance&distance=100&status=adoptable"""

with open('petfinder_breed_converter.json', 'r') as f:
    breed_converter = json.load(f)


class Petfinder:

    def __init__(self):
        self.header = self.get_header()

    def get_header(self):
        data = {
            'grant_type': 'client_credentials',
            'client_id': KEY,
            'client_secret': SECRET
        }
        response = requests.post('https://api.petfinder.com/v2/oauth2/token', data=data)
        if response.reason != 'OK':
            print('failed to get token. check credentials')
            print('response code:', response.status_code)
            print('response reason:', response.reason)
        else:
            print('new token received')
        TOKEN = json.loads(response.text)['access_token']
        header = {
            'Authorization': 'Bearer {}'.format(TOKEN),
        }
        return header

    def get_response(self, breed, zip):
        url = base_api_url.format(breed=breed, zip=zip)
        # print('API call: ',url)
        response = requests.get(url, headers=self.header)
        return response

    def get_dogs(self, pred_df, zip):
        petfinder_recs = []
        count = 0
        ids = []  # track listing ids across breeds so don't pull same dog twice
        for i, pred_row in pred_df.iterrows():
            breed = pred_row['pred_breed']
            print('Starting API call for breed:', breed)
            if breed in breed_converter.keys():
                breed_api = breed_converter[breed]
                print('converted to similar breeds:', breed_api)
            else:
                breed_api = breed
            breed_api = breed_api.replace(' or ', ' / ').replace(' ', '+').replace(' / ', '%2f')
            response = self.get_response(breed_api, zip)
            if response.status_code != 200:
                print('Bad response. Response code:', response.status_code, 'Reason:', response.reason)
                print('attempting to get new header token')
                self.header = self.get_header()
                response = self.get_response(breed_api, zip)
                print('response status:', response.status_code)
                if response.status_code != 200:
                    print('2nd 401 response, possibly bad credentials')
                    return False
            listings = json.loads(response.text)['animals']
            if len(listings) == 0:
                print('no local dogs found for', breed_api)
                continue
            # Gather 3 listings for the breed.
            # Skip repeated id and lacking photos.
            rec = {'breed': breed,
                   'breed_search_url': search_url.format(breed=breed_api, zip=zip),
                   'listings': []
                   }
            good_listings = 0
            for i in range(len(listings)):
                id = listings[i]['id']
                name = listings[i]['name']
                if (id in ids) or (len(listings[i]['photos']) == 0):
                    print('skipping dog for repeated id or no photos')
                    continue
                ids.append(id)
                url = listings[i]['url']
                description = listings[i]['description']
                if description is not None:
                    if len(description) > 200:
                        description = description[:200] + '...'
                else:
                    description='no description provided'
                photo_url = listings[i]['photos'][0]['medium']
                rec['listings'].append({
                    'name': name,
                    'url': url,
                    'description': description,
                    'photo_url': photo_url
                })
                # print('gathered rec:', rec)
                good_listings += 1
                # break out once 3 listings gathered for this breed
                if good_listings > 2:
                    break
            petfinder_recs.append(rec)
            count += 1
            # break out once 4 breeds have been gathered
            if count > 3:
                break
        return petfinder_recs
