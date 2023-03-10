import os
import json
import requests
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from prompts import format_description
from text_processing import fix_description_fine_tune
from utils import (headers, API_KEY, logger)
from typing import Optional

load_dotenv()

#app = FastAPI()

class request_body(BaseModel):
    property_type: str
    listing_type: str
    keywords: str
    locality: str
    city: str
    price: int
    area: int
    area_unit: str
    facing: str
    amenities: str
    furnishing: str
    project: str
    bedrooms: str
    bathrooms: Optional[int]
    parking: Optional[int]
    property_age: Optional[str]
    floor_number: Optional[int]
    total_floor_count: Optional[int]



#CURIE_URL = os.getenv('CURIE_URL')
#API_KEY = os.getenv('API_KEY')

'''
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer {}".format(API_KEY)
}
'''
#"model": "curie:ft-squareyards-2022-08-27-11-03-01",
#model: curie:ft-squareyards-2022-08-30-06-27-41
#"model": "curie:ft-squareyards-2022-08-29-09-56-23"
#curie:ft-squareyards-2022-08-30-09-13-47
#curie:ft-squareyards-2022-08-31-05-23-35
#curie:ft-squareyards-2022-09-02-05-06-03
#curie:ft-squareyards-2022-09-02-06-50-00
#curie:ft-squareyards-2022-09-02-07-00-55
#curie:ft-squareyards-2022-09-05-09-39-33

payload= {
    "model": "curie:ft-squareyards-2022-09-05-09-39-33",
    "max_tokens": 200,
    "temperature": 0.5,
    "top_p": 1,
    "best_of": 1,
    "n": 1,
    "stream": False,
    "logprobs": None,
    "stop": [" END"]
}

#prompt1="\"description\":\"A stylishly designed flat is available with 516 square feet of space and at a price of Rs 2,50,00,001 which is quite affordable. You will get 3 bedroom at the apartment along with 2 bathrooms as well and 1 parking making it suitable for a small family, working bachelors. The prime location of Goregaon West in Mumbai is a key feature for the property since it is located close to public transportation in a safe & secure neighborhood. This is a garden facing apartment with a nice view on the 6th floor of a 17 storied building and is 10+ years old while being semi-furnished. Community amenities include a cycling cum jogging track, playing zone for children, large green zone and 24 hour security.\"\n\n###\n\n\"keywords\": {},\n\"city\": {},\n\"locality\": {},\n\"area\": {}},\n\"area_unit\": {},\n\"price\": {},\n\"furnishing\": {},\n\"bedrooms\": 3,\n\"property_age\": {},\n\"bathrooms\": {},\n\"parking\": {},\n\"facing\": {},\n\"floor_number\": {},\n\"total_floor_count\": {}},\n\"amenities\": {},\n\"description\": {}"
#prompt1="keywords: stylishly, affordable, small family, working bachelors, prime location, secure neighborhood,\ncity: Mumbai,\nlocality: Goregaon West,\narea: 516,\narea_unit: Square Feet,\nprice: 25000001,\nfurnishing: Semi-Furnished,\nbedrooms: 3,\nproperty_age: 10 years,\nbathrooms: 2,\nparking: 1,\nfacing: garden,\nfloor_number: 6,\ntotal_floor_count: 17,\namenities: cycling cum jogging track, playing zone for children, large green zone and 24 hour security,\ndescription:A stylishly designed flat is available with 516 square feet of space and at a price of Rs 2,50,00,001 which is quite affordable. You will get 3 bedroom at the apartment along with 2 bathrooms as well and 1 parking making it suitable for a small family, working bachelors. The prime location of Goregaon West in Mumbai is a key feature for the property since it is located close to public transportation in a safe & secure neighborhood. This is a garden facing apartment with a nice view on the 6th floor of a 17 storied building and is 10+ years old while being semi-furnished. Community amenities include a cycling cum jogging track, playing zone for children, large green zone and 24 hour security.\n\n###\n\nkeywords: {},\ncity: {},\nlocality: {},\narea: 516,\narea_unit: {},\nprice: {},\nfurnishing: {},\nbedrooms: 3,\nproperty_age: {},\nbathrooms: {},\nparking: {},\nfacing: {},\nfloor_number: {},\ntotal_floor_count: {}},\namenities: {},\ndescription: "
#prompt1="keywords: stylishly, affordable, small family, working bachelors, prime location, secure neighborhood,\ncity: Mumbai,\nlocality: Goregaon West,\narea: 516,\narea_unit: Square Feet,\nprice: 25000001,\nfurnishing: Semi-Furnished,\nbedrooms: 3,\nproperty_age: 10 years,\nbathrooms: 2,\nparking: 1,\nfacing: garden,\nfloor_number: 6,\ntotal_floor_count: 17,\namenities: cycling cum jogging track, playing zone for children, large green zone and 24 hour security,\ndescription:A stylishly designed flat is available with 516 square feet of space and at a price of Rs 2,50,00,001 which is quite affordable. You will get 3 bedroom at the apartment along with 2 bathrooms as well and 1 parking making it suitable for a small family, working bachelors. The prime location of Goregaon West in Mumbai is a key feature for the property since it is located close to public transportation in a safe & secure neighborhood. This is a garden facing apartment with a nice view on the 6th floor of a 17 storied building and is 10+ years old while being semi-furnished. Community amenities include a cycling cum jogging track, playing zone for children, large green zone and 24 hour security.\n\n###\n\nkeywords: {},\ncity: {},\nlocality: {},\narea: {},\narea_unit: {},\nprice: {},\ndescription: "
#prompt1 = "keywords:{},\ncity:{},\nlocality:{},\narea:{},\narea_unit:{},\nprice:{},\nfurnishing:{},\nbedrooms:{},\nproperty_age:{},\nbathrooms:{},\nparking:{},\nfacing:{},\nfloor_number:{},\ntotal_floor_count:{},\namenities:{}.\n\n###\n\n"
prompt1="keywords: {},\ncity: {},\nlocality:{},\narea: {},\narea_unit:{},\nprice: {},\nfurnishing: {},\nbedrooms: {},\nproperty_age: {},\nbathrooms: {},\nparking: {},\nfacing: {},\nfloor_number: {},\ntotal_floor_count: {},\namenities: {}.\n\n###\n\n"
#print(type(prompt))


'''
@app.post("/apartment_fine_tuned")
async def apartment_description_fine_tuned(data: request_body, format: bool = False):
        payload_fine_tune["prompt"] = prompt1.format(data.keywords,data.city,data.locality,data.area,data.area_unit,data.price,data.furnishing,data.bedrooms,data.property_age,data.bathrooms,data.parking,data.facing,data.floor_number,data.total_floor_count,data.amenities)
        #payload["prompt"] = prompt1.format(data.keywords,data.city,data.locality,data.area,data.area_unit,data.price)
        response0 = requests.post(CURIE_URL, headers=headers, data=json.dumps(payload_fine_tune))
        res_data0 = response0.json()
        description0 = res_data0['choices'][0]['text'].strip()
        if format:
            description = format_description(description0)
        #description1 = description0.replace('\n', '<br />')
        #description1 = description1.replace("'", "")
        #char0 = description0.split("\n")
        return description
'''

'''
async def apartment_description_fine_tuned(data, format = False):
    logger.info(data.property_type)
    logger.info(data.listing_type)
    if data.property_type == "apartment" and data.listing_type == "sale" and len(data.locality) >= 3 and len(data.city) >= 3:
        payload["prompt"] = prompt1.format(data.keywords,data.city,data.locality,data.area,data.area_unit,data.price,data.furnishing,data.bedrooms,data.property_age,data.bathrooms,data.parking,data.facing,data.floor_number,data.total_floor_count,data.amenities)
        #payload["prompt"] = prompt1.format(data.keywords,data.city,data.locality,data.area,data.area_unit,data.price)
        response0 = requests.post(CURIE_URL, headers=headers, data=json.dumps(payload))
        res_data0 = response0.json()
        description0 = res_data0['choices'][0]['text'].strip()
        description1 = fix_description_fine_tune(description0, data)
        print(description1)
        if format:
            description = format_description(description1)
        else:
            description = description1
        #description1 = description0.replace('\n', '<br />')
        #description1 = description1.replace("'", "")
        #char0 = description0.split("\n")
        logger.info(description)
        return description
    else:
        return("please enter property_type == apartment, listing_type == sale and make sure you have entered locality, city.")


async def apartment_description_fine_tuned(fine_tune_apartment, format = False):
    logger.info(fine_tune_apartment.property_type)
    logger.info(fine_tune_apartment.listing_type)
    if fine_tune_apartment.property_type == "apartment" and fine_tune_apartment.listing_type == "sale" and len(fine_tune_apartment.locality) >= 3 and len(fine_tune_apartment.city) >= 3:
        payload["prompt"] = prompt1.format(fine_tune_apartment.keywords,fine_tune_apartment.city,fine_tune_apartment.locality,fine_tune_apartment.area,fine_tune_apartment.area_unit,fine_tune_apartment.price,fine_tune_apartment.furnishing,fine_tune_apartment.bedrooms,fine_tune_apartment.property_age,fine_tune_apartment.bathrooms,fine_tune_apartment.parking,fine_tune_apartment.facing,fine_tune_apartment.floor_number,fine_tune_apartment.total_floor_count,fine_tune_apartment.amenities)
        #payload["prompt"] = prompt1.format(data.keywords,data.city,data.locality,data.area,data.area_unit,data.price)
        response0 = requests.post(CURIE_URL, headers=headers, data=json.dumps(payload)) 
        res_data0 = response0.json()
        print(res_data0)
        description0 = res_data0['choices'][0]['text'].strip()
        description1 = fix_description_fine_tune(description0, fine_tune_apartment)
        print(description1)
        if format:
            description = format_description(description1)
        else:
            description = description1
        #description1 = description0.replace('\n', '<br />')
        #description1 = description1.replace("'", "")
        #char0 = description0.split("\n")
        logger.info(description)
        return description
    else:
        return("please enter property_type == apartment, listing_type == sale and make sure you have entered locality, city.")
'''