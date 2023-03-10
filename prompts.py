#!/usr/bin/python
import os
import re
import json
import random

from fastapi import HTTPException
from babel.numbers import format_currency

from utils import logger, hit_gpt_api1, hit_gpt_api, headers
from text_processing import get_tokens,\
                            get_scores,\
                            get_best_description,\
                            encode_description_to_preserve_some_tokens,\
                            remove_encodings,\
                            fix_description,\
                            fix_furnish, fix_furnish_2,\
                            FURNISH_TOKEN


TOKEN_COVERAGE_THRESHOLD = 0.40
# After this many iterations. No fixing will be done.
# This is done to avoid infinite loops.
FIXING_ITERATIONS = 30
# Number of times the program is going to hit GPT-3 in case the 
# returned descriptions are not up to the mark.
API_HIT_ITERATIONS_THRESHOLD = 2
# Number of descriptions to be returned by GPT-3 in each request.
NUM_EXAMPLES = 2

# GPT-3 payload.
BASE_PAYLOAD = {
    "max_tokens": 300,
    "temperature": 0.5,
    "top_p": 0.8,
    "n": NUM_EXAMPLES,
    "stream": False,
    "logprobs": None,
    "stop": ["-----"]
}

FINE_TUNE_PAYLOAD_SALE_APARTMENT = {
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

FINE_TUNE_PAYLOAD_RENT_APARTMENT = {
    "model": "curie:ft-squareyards-2022-09-19-10-14-46",
    "max_tokens": 200,
    "temperature": 0.5,
    "top_p": 1,
    "best_of": 1,
    "n": 1,
    "stream": False,
    "logprobs": None,
    "stop": [" END"]
}

FINE_TUNE_PAYLOAD_SALE_APARTMENT_ZERO_HANDLED= {
    "model": "curie:ft-squareyards-2022-09-27-07-02-21",
    "max_tokens": 170,
    "temperature": 0.5,
    "top_p": 1,
    "best_of": 1,
    "n": 1,
    "stream": False,
    "logprobs": None,
    "stop": [" END"]
}

FINE_TUNE_PAYLOAD_RENT_APARTMENT_ZERO_HANDLED= {
    "model": "curie:ft-squareyards-2022-09-28-04-32-09",
    "max_tokens": 170,
    "temperature": 0.5,
    "top_p": 1,
    "best_of": 1,
    "n": 1,
    "stream": False,
    "logprobs": None,
    "stop": [" END"]
}

#prompts only used for fine-tune model
prompt1="keywords: {},\ncity: {},\nlocality:{},\narea: {},\narea_unit:{},\nprice: {},\nfurnishing: {},\nbedrooms: {},\nproperty_age: {},\nbathrooms: {},\nparking: {},\nfacing: {},\nfloor_number: {},\ntotal_floor_count: {},\namenities: {}.\n\n###\n\n"
#prompts only used for fine-tune model - Zero handled
prompt2="keywords: {},\ncity: {},\nlocality:{},\narea: {},\narea_unit:{},\nprice: {},\nfurnishing: {},\nbedrooms: {},\nbathrooms: {},\nparking: {},\nfacing: {},\namenities: {}.\n\n###\n\n"



async def generate_description(listing_data, format=False):
    """
    Generates a description for any type of BaseListingData.
    Steps:
        1. Hit the API
        2. Find best description from returned description using scoring.
        3. If description is acceptable then return it.
        4. If it is not acceptable. Repeat steps 1-3 certain number of times before giving up.
    """

    listing_data_dict = dict(listing_data)
    keywords = []
    for key, vals in listing_data_dict.items():
        token_list = get_tokens(vals)
        keywords.extend(token_list)

    payload = dict(BASE_PAYLOAD)
    payload['prompt'] = create_prompt(listing_data)
    
    data = await hit_gpt_api(payload)
    description_scores, data = get_scores(data, set(keywords))
    # for i in range(len(description_scores)):
    #     print(data["choices"][description_scores[i][2]]["text"])
    #     print(description_scores[i][0], description_scores[i][1])
    #     print("--xx--")
    description = None

    description, correct_description_found, unique_token_score, token_coverage_score = get_best_description(data, description_scores)

    # Again hit the GPT-3 API in case we don't get a satisfactory description.
    hit_iterations = 1
    while hit_iterations < API_HIT_ITERATIONS_THRESHOLD and correct_description_found == False:
        new_data = await hit_gpt_api(payload)

        for new_description in new_data['choices']:
            data['choices'].append(new_description)
        description_scores, data = get_scores(data, set(keywords))

        description, correct_description_found, unique_token_score, token_coverage_score = get_best_description(data, description_scores)
        hit_iterations += 1

    # Return error if we API is unable to find description.
    if correct_description_found == False and token_coverage_score < TOKEN_COVERAGE_THRESHOLD:
        logger.info("-------->>  Failed for prompt: \n"+str(payload['prompt']))
        logger.info("========>> Best description for failed prompt: \n"+str(description))
        raise HTTPException(status_code=500, detail="Could not generate the description for the given input.")


    description_copy = description
    try:
        cnt = 0
        modified = True
        while modified and cnt < FIXING_ITERATIONS:
            cnt += 1
            description_copy = re.sub(" +", " ", description_copy)
            description_copy, modified = encode_description_to_preserve_some_tokens(description_copy)
        
        description_copy = description_copy.replace("-", " ")
        description_copy = remove_encodings(description_copy)
        description_copy = description_copy.replace("bhk", " bhk")\
                                            .replace(" rs.", " Rs ")
    except:
        pass

    try:
        description_copy = re.sub(" +", " ", description_copy)
        modified = True
        cnt = 0
        print(description_copy)
        while modified and cnt < FIXING_ITERATIONS:
            cnt += 1
            description_copy, modified = fix_description(description_copy, listing_data)
    except:
        pass

    # Fixing for furnish
    # try:
    #     description_copy = fix_furnish(description_copy, listing_data.furnishing.replace("-", " "))
    # except:
    #     pass
    description_copy_before_furnish = description_copy
    try:
        # print(listing_data.furnishing)
        description_copy = re.sub(" +", " ", description_copy)
        modified = True
        cnt = 0
        # print("Before furnish fix", description_copy)
        while modified and cnt < 5:
            cnt += 1
            description_copy, modified = fix_furnish_2(description_copy)

        replace_val = listing_data.furnishing
        if replace_val == "furnished":
            replace_val = "well furnished"
        description_copy = description_copy.replace(" furnished ", FURNISH_TOKEN)\
                                            .replace(FURNISH_TOKEN, replace_val)\
                                            .replace("_", "")
    except Exception as e:
        description_copy = description_copy_before_furnish
        print("Furnish Exception ", e)

    description_copy = re.sub(" +", " ", description_copy).strip()
    description_copy = description_copy.replace(" rs ", " Rs ")
    description_copy = description_copy.replace("fully semi-furnished", "semi-furnished")
    description_copy = description_copy.replace("fully unfurnished", "unfurnished")
    description_copy = description_copy.replace("fully Unfurnished", "unfurnished")
    description_copy = description_copy.replace("fully Semi-Furnished", "semi-furnished")
    description_copy = description_copy.replace("Flats", "Flat")
    description_copy = description_copy.replace("flats", "flat")
    description_copy = description_copy.replace("sq ft", "sqft")
    description_copy = description_copy.replace("sq. ft.", "sqft")
    description_copy = description_copy.replace("Sq. Ft.", "sqft")
    description_copy = description_copy.replace("sq. Ft.", "sqft")
    description_copy = description_copy.replace("sq yd", "sqyd")
    description_copy = description_copy.replace("sq. yd.", "sqyd")
    description_copy = description_copy.replace("sq. mt.", "sqmt")

    if format:
        description_copy = format_description(description_copy)
    logger.info(dict(listing_data))
    logger.info(description_copy)
    return description_copy


#for dubai

async def generate_description1(listing_data, format=False):
    """
    Generates a description for any type of BaseListingData.
    Steps:
        1. Hit the API
        2. Find best description from returned description using scoring.
        3. If description is acceptable then return it.
        4. If it is not acceptable. Repeat steps 1-3 certain number of times before giving up.
    """

    listing_data_dict = dict(listing_data)
    keywords = []
    for key, vals in listing_data_dict.items():
        token_list = get_tokens(vals)
        keywords.extend(token_list)

    payload = dict(BASE_PAYLOAD)
    payload['prompt'] = create_prompt(listing_data)
    
    data = await hit_gpt_api(payload)
    description_scores, data = get_scores(data, set(keywords))
    # for i in range(len(description_scores)):
    #     print(data["choices"][description_scores[i][2]]["text"])
    #     print(description_scores[i][0], description_scores[i][1])
    #     print("--xx--")
    description = None

    description, correct_description_found, unique_token_score, token_coverage_score = get_best_description(data, description_scores)

    # Again hit the GPT-3 API in case we don't get a satisfactory description.
    hit_iterations = 1
    while hit_iterations < API_HIT_ITERATIONS_THRESHOLD and correct_description_found == False:
        new_data = await hit_gpt_api(payload)

        for new_description in new_data['choices']:
            data['choices'].append(new_description)
        description_scores, data = get_scores(data, set(keywords))

        description, correct_description_found, unique_token_score, token_coverage_score = get_best_description(data, description_scores)
        hit_iterations += 1

    # Return error if we API is unable to find description.
    if correct_description_found == False and token_coverage_score < TOKEN_COVERAGE_THRESHOLD:
        logger.info("-------->>  Failed for prompt: \n"+str(payload['prompt']))
        logger.info("========>> Best description for failed prompt: \n"+str(description))
        raise HTTPException(status_code=500, detail="Could not generate the description for the given input.")


    description_copy = description
    try:
        cnt = 0
        modified = True
        while modified and cnt < FIXING_ITERATIONS:
            cnt += 1
            description_copy = re.sub(" +", " ", description_copy)
            description_copy, modified = encode_description_to_preserve_some_tokens(description_copy)
        
        description_copy = description_copy.replace("-", " ")
        description_copy = remove_encodings(description_copy)
        description_copy = description_copy.replace("bhk", " bhk")\
                                            .replace(" rs.", " Rs ")
    except:
        pass

    try:
        description_copy = re.sub(" +", " ", description_copy)
        modified = True
        cnt = 0
        print(description_copy)
        while modified and cnt < FIXING_ITERATIONS:
            cnt += 1
            description_copy, modified = fix_description(description_copy, listing_data)
    except:
        pass

    # Fixing for furnish
    # try:
    #     description_copy = fix_furnish(description_copy, listing_data.furnishing.replace("-", " "))
    # except:
    #     pass
    description_copy_before_furnish = description_copy
    try:
        # print(listing_data.furnishing)
        description_copy = re.sub(" +", " ", description_copy)
        modified = True
        cnt = 0
        # print("Before furnish fix", description_copy)
        while modified and cnt < 5:
            cnt += 1
            description_copy, modified = fix_furnish_2(description_copy)

        replace_val = listing_data.furnishing
        if replace_val == "furnished":
            replace_val = "well furnished"
        description_copy = description_copy.replace(" furnished ", FURNISH_TOKEN)\
                                            .replace(FURNISH_TOKEN, replace_val)\
                                            .replace("_", "")
    except Exception as e:
        description_copy = description_copy_before_furnish
        print("Furnish Exception ", e)

    description_copy = re.sub(" +", " ", description_copy).strip()
    description_copy = description_copy.replace(" Rs ", " AED ")
    description_copy = description_copy.replace(" rs ", " AED ")
    description_copy = description_copy.replace(" aed ", " AED ")
    description_copy = description_copy.replace("fully semi-furnished", "semi-furnished")
    description_copy = description_copy.replace("fully unfurnished", "unfurnished")
    description_copy = description_copy.replace("fully Unfurnished", "unfurnished")
    description_copy = description_copy.replace("fully Semi-Furnished", "semi-furnished")
    description_copy = description_copy.replace("Flats", "Flat")
    description_copy = description_copy.replace("flats", "flat")
    description_copy = description_copy.replace("sq ft", "sqft")
    description_copy = description_copy.replace("sq. ft.", "sqft")
    description_copy = description_copy.replace("Sq. Ft.", "sqft")
    description_copy = description_copy.replace("sq. Ft.", "sqft")
    description_copy = description_copy.replace("sq yd", "sqyd")
    description_copy = description_copy.replace("sq. yd.", "sqyd")
    description_copy = description_copy.replace("sq. mt.", "sqmt")
    

    if format:
        description_copy = format_description(description_copy)
    logger.info(dict(listing_data))
    logger.info(description_copy)
    return description_copy


#for fine tune

async def generate_description_fine_tune(fine_tune_apartment, format=False):
    """
    Generates a description for any type of BaseListingData.
    Steps:
        1. Hit the API
        2. Find best description from returned description using scoring.
        3. If description is acceptable then return it.
        4. If it is not acceptable. Repeat steps 1-3 certain number of times before giving up.
    """
    #print(fine_tune_apartment)
    listing_data_dict = dict(fine_tune_apartment)
    keywords = []
    for key, vals in listing_data_dict.items():
        token_list = get_tokens(vals)
        keywords.extend(token_list)
    
    if fine_tune_apartment.listing_type == "sale" and (fine_tune_apartment.floor_number != 0 and fine_tune_apartment.total_floor_count != 0):
        payload = dict(FINE_TUNE_PAYLOAD_SALE_APARTMENT)
        payload["prompt"] = prompt1.format(fine_tune_apartment.keywords,fine_tune_apartment.city,fine_tune_apartment.locality,fine_tune_apartment.area,fine_tune_apartment.area_unit,fine_tune_apartment.price,fine_tune_apartment.furnishing,fine_tune_apartment.bedrooms,fine_tune_apartment.property_age,fine_tune_apartment.bathrooms,fine_tune_apartment.parking,fine_tune_apartment.facing,fine_tune_apartment.floor_number,fine_tune_apartment.total_floor_count,fine_tune_apartment.amenities)
        #print("1")
    

    elif fine_tune_apartment.listing_type == "sale" and (fine_tune_apartment.floor_number == 0 or fine_tune_apartment.total_floor_count == 0):
        payload = dict(FINE_TUNE_PAYLOAD_SALE_APARTMENT_ZERO_HANDLED)       
        payload["prompt"] = prompt2.format(fine_tune_apartment.keywords,fine_tune_apartment.city,fine_tune_apartment.locality,fine_tune_apartment.area,fine_tune_apartment.area_unit,fine_tune_apartment.price,fine_tune_apartment.furnishing,fine_tune_apartment.bedrooms,fine_tune_apartment.bathrooms,fine_tune_apartment.parking,fine_tune_apartment.facing,fine_tune_apartment.amenities)
        #print("2")
    
    elif fine_tune_apartment.listing_type == "rent" and (fine_tune_apartment.floor_number != 0 and fine_tune_apartment.total_floor_count != 0):
        payload = dict(FINE_TUNE_PAYLOAD_RENT_APARTMENT)
        payload["prompt"] = prompt1.format(fine_tune_apartment.keywords,fine_tune_apartment.city,fine_tune_apartment.locality,fine_tune_apartment.area,fine_tune_apartment.area_unit,fine_tune_apartment.price,fine_tune_apartment.furnishing,fine_tune_apartment.bedrooms,fine_tune_apartment.property_age,fine_tune_apartment.bathrooms,fine_tune_apartment.parking,fine_tune_apartment.facing,fine_tune_apartment.floor_number,fine_tune_apartment.total_floor_count,fine_tune_apartment.amenities)
        #print("3")

    elif fine_tune_apartment.listing_type == "rent" and (fine_tune_apartment.floor_number == 0 or fine_tune_apartment.total_floor_count == 0):
        payload = dict(FINE_TUNE_PAYLOAD_RENT_APARTMENT_ZERO_HANDLED)
        payload["prompt"] = prompt2.format(fine_tune_apartment.keywords,fine_tune_apartment.city,fine_tune_apartment.locality,fine_tune_apartment.area,fine_tune_apartment.area_unit,fine_tune_apartment.price,fine_tune_apartment.furnishing,fine_tune_apartment.bedrooms,fine_tune_apartment.bathrooms,fine_tune_apartment.parking,fine_tune_apartment.facing,fine_tune_apartment.amenities)
        #print("4")
   
    else:
        return("error: check attributes")
    #payload["prompt"] = prompt1.format(fine_tune_apartment.keywords,fine_tune_apartment.city,fine_tune_apartment.locality,fine_tune_apartment.area,fine_tune_apartment.area_unit,fine_tune_apartment.price,fine_tune_apartment.furnishing,fine_tune_apartment.bedrooms,fine_tune_apartment.property_age,fine_tune_apartment.bathrooms,fine_tune_apartment.parking,fine_tune_apartment.facing,fine_tune_apartment.floor_number,fine_tune_apartment.total_floor_count,fine_tune_apartment.amenities)
    
    data = await hit_gpt_api1(payload)
    #print("check this",data)
    description_scores, data = get_scores(data, set(keywords))
    # for i in range(len(description_scores)):
    #     print(data["choices"][description_scores[i][2]]["text"])
    #     print(description_scores[i][0], description_scores[i][1])
    #     print("--xx--")
    description = None

    description, correct_description_found, unique_token_score, token_coverage_score = get_best_description(data, description_scores)

    # Again hit the GPT-3 API in case we don't get a satisfactory description.
    hit_iterations = 1
    while hit_iterations < API_HIT_ITERATIONS_THRESHOLD and correct_description_found == False:
        new_data = await hit_gpt_api1(payload)

        for new_description in new_data['choices']:
            data['choices'].append(new_description)
        description_scores, data = get_scores(data, set(keywords))

        description, correct_description_found, unique_token_score, token_coverage_score = get_best_description(data, description_scores)
        hit_iterations += 1

    # Return error if we API is unable to find description.
    if correct_description_found == False and token_coverage_score < TOKEN_COVERAGE_THRESHOLD:
        logger.info("-------->>  Failed for prompt: \n"+str(payload['prompt']))
        logger.info("========>> Best description for failed prompt: \n"+str(description))
        raise HTTPException(status_code=500, detail="Could not generate the description for the given input.")


    description_copy = description
    try:
        cnt = 0
        modified = True
        while modified and cnt < FIXING_ITERATIONS:
            cnt += 1
            description_copy = re.sub(" +", " ", description_copy)
            description_copy, modified = encode_description_to_preserve_some_tokens(description_copy)
        
        description_copy = description_copy.replace("-", " ")
        description_copy = remove_encodings(description_copy)
        description_copy = description_copy.replace("bhk", " bhk")\
                                            .replace(" rs.", " Rs ")
    except:
        pass

    try:
        description_copy = re.sub(" +", " ", description_copy)
        modified = True
        cnt = 0
        #print(description_copy)
        while modified and cnt < FIXING_ITERATIONS:
            cnt += 1
            description_copy, modified = fix_description(description_copy, fine_tune_apartment)
    except:
        pass

    # Fixing for furnish
    # try:
    #     description_copy = fix_furnish(description_copy, listing_data.furnishing.replace("-", " "))
    # except:
    #     pass
    description_copy_before_furnish = description_copy
    try:
        # print(listing_data.furnishing)
        description_copy = re.sub(" +", " ", description_copy)
        modified = True
        cnt = 0
        # print("Before furnish fix", description_copy)
        while modified and cnt < 5:
            cnt += 1
            description_copy, modified = fix_furnish_2(description_copy)

        replace_val = fine_tune_apartment.furnishing
        if replace_val == "furnished":
            replace_val = "well furnished"
        description_copy = description_copy.replace(" furnished ", FURNISH_TOKEN)\
                                            .replace(FURNISH_TOKEN, replace_val)\
                                            .replace("_", "")
    except Exception as e:
        description_copy = description_copy_before_furnish
        #print("Furnish Exception ", e)

    description_copy = re.sub(" +", " ", description_copy).strip()
    description_copy = description_copy.replace(" rs ", " Rs ")
    description_copy = description_copy.replace(" rs. ", " Rs ")
    description_copy = description_copy.replace(" Rs. ", " Rs ")
    description_copy = description_copy.replace("fully semi-furnished", "semi-furnished")
    description_copy = description_copy.replace("fully unfurnished", "unfurnished")
    description_copy = description_copy.replace("Flats", "Flat")
    description_copy = description_copy.replace("flats", "flat")
    description_copy = description_copy.replace("sq ft", "sqft")
    description_copy = description_copy.replace("sq. ft.", "sqft")
    description_copy = description_copy.replace("Sq. Ft.", "sqft")
    description_copy = description_copy.replace("sq. Ft.", "sqft")
    description_copy = description_copy.replace("sq yd", "sqyd")
    description_copy = description_copy.replace("sq. yd.", "sqyd")
    description_copy = description_copy.replace("sq. mt.", "sqmt")
    
    
    

    if format:
        description_copy = format_description(description_copy)
    logger.info(dict(fine_tune_apartment))
    logger.info(description_copy)
    return description_copy



'''
def get_examples(property_type, listing_type):
    """
    Get all the examples from the JSON file for the specified
    property_type and listing_type
    """
    if os.path.isfile(f'prompts/{property_type}.json'):
        json_path = f'prompts/{property_type}.json'
    elif os.path.isfile(f'prompts/{property_type}_{listing_type}.json'):
        json_path = f'prompts/{property_type}_{listing_type}.json'
    else:
        raise HTTPException(
            status_code=400,
            detail="Listing of {listing_type} with {property_type} is not supported"
        )
    with open(json_path, 'rb') as json_file:
        examples = json.loads(json_file.read())
    return examples
'''

def get_examples(property_type, listing_type):
    """
    Get all the examples from the JSON file for the specified
    property_type and listing_type
    """
    generate_random_numbers = random.randint(1, 3)
    logger.info(generate_random_numbers)
    if os.path.isfile(f'prompts/{property_type}.json'):
        json_path = f'prompts/{property_type}.json'

    elif property_type.value == "apartment" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)
        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            print(json_path)

        elif generate_random_numbers == 2:
                os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
                json_path = f'prompts/{property_type}_{listing_type}1.json'

        elif generate_random_numbers == 3:
                os.path.isfile(f'prompts/{property_type}_{listing_type}2.json')
                json_path = f'prompts/{property_type}_{listing_type}2.json'
    
    elif property_type.value == "independent_house" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)

        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            print(json_path)

        elif generate_random_numbers == 2:
            os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
            json_path = f'prompts/{property_type}_{listing_type}1.json'
        
        elif generate_random_numbers == 3:
            os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
            json_path = f'prompts/{property_type}_{listing_type}1.json'

    elif property_type.value == "plot" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)

        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            print(json_path)

        elif generate_random_numbers == 2:
                os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
                json_path = f'prompts/{property_type}_{listing_type}1.json'

        elif generate_random_numbers == 3:
                os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
                json_path = f'prompts/{property_type}_{listing_type}1.json'

    elif property_type.value == "land" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)

        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            print(json_path)

        elif generate_random_numbers == 2:
                os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
                json_path = f'prompts/{property_type}_{listing_type}1.json'

        elif generate_random_numbers == 3:
                os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
                json_path = f'prompts/{property_type}_{listing_type}1.json'
    
    elif property_type.value == "builder_floor" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)

        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            print(json_path)

        if generate_random_numbers == 2:
            os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
            json_path = f'prompts/{property_type}_{listing_type}1.json'
            print(json_path)

        if generate_random_numbers == 3:
            os.path.isfile(f'prompts/{property_type}_{listing_type}2.json')
            json_path = f'prompts/{property_type}_{listing_type}2.json'
            print(json_path)    


    elif property_type.value == "office_space" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)

        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            #print(json_path)

        if generate_random_numbers == 2:
            os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
            json_path = f'prompts/{property_type}_{listing_type}1.json'
            #print(json_path)

        if generate_random_numbers == 3:
            os.path.isfile(f'prompts/{property_type}_{listing_type}2.json')
            json_path = f'prompts/{property_type}_{listing_type}2.json'
            #print(json_path)  

    elif property_type.value == "office_space_sez" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)

        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            #print(json_path)

        if generate_random_numbers == 2:
            os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
            json_path = f'prompts/{property_type}_{listing_type}1.json'
            #print(json_path)

        if generate_random_numbers == 3:
            os.path.isfile(f'prompts/{property_type}_{listing_type}2.json')
            json_path = f'prompts/{property_type}_{listing_type}2.json'
            #print(json_path)      

    elif property_type.value == "shop" and (listing_type.value =="sale" or listing_type.value == "rent"):
        logger.info(property_type)
        logger.info(listing_type)

        if generate_random_numbers == 1:
            os.path.isfile(f'prompts/{property_type}_{listing_type}.json')
            json_path = f'prompts/{property_type}_{listing_type}.json'
            #print(json_path)

        if generate_random_numbers == 2:
            os.path.isfile(f'prompts/{property_type}_{listing_type}1.json')
            json_path = f'prompts/{property_type}_{listing_type}1.json'
            #print(json_path)

        if generate_random_numbers == 3:
            os.path.isfile(f'prompts/{property_type}_{listing_type}2.json')
            json_path = f'prompts/{property_type}_{listing_type}2.json'
            #print(json_path)


    elif os.path.isfile(f'prompts/{property_type}_{listing_type}.json'):
        json_path = f'prompts/{property_type}_{listing_type}.json'     

    else:
        raise HTTPException(
            status_code=400,
            detail="Listing of {listing_type} with {property_type} is not supported"
        )
    with open(json_path, 'rb') as json_file:
        examples = json.loads(json_file.read())
    return examples

def format_listing_data(listing_data):
    """
    Formats the examples for usage in the prompt
    """
    prompt_string = ""
    if 'listing_type' in listing_data:
        prompt_string += f"Listing type: {listing_data['listing_type']}\n"

    if 'keywords' in listing_data:
        prompt_string += f"Keywords: {listing_data['keywords']}\n"

    
    if "project" in listing_data: 
        if "." in listing_data['project']:
            remove_dot = listing_data['project'].replace("."," ")
            prompt_string += f"Project: {remove_dot}\n"
        else:
            prompt_string += f"Project: {listing_data['project']}\n" 

    if "locality" in listing_data:
        prompt_string += f"Locality: {listing_data['locality']}\n"

    if "city" in listing_data:
        prompt_string += f"City: {listing_data['city']}\n"

    if "furnishing" in listing_data:
        prompt_string += f"Furnishing: {listing_data['furnishing']}\n"
    
    if "office_space_type" in listing_data:
        prompt_string += f"Office fitting: {listing_data['office_space_type']}\n"

    if "bedrooms" in listing_data:
        prompt_string += f"Bedrooms: {listing_data['bedrooms']}\n"
        
    if "available_for" in listing_data:
        prompt_string += f"Available for: {listing_data['available_for']}\n"

    if "suited_for" in listing_data:
        prompt_string += f"Suited for: {listing_data['suited_for']}\n" 

    if "room_type" in listing_data:
        prompt_string += f"Room type: {listing_data['room_type']}\n" 

    if "food_charges_included" in listing_data:
        prompt_string += f"food chargesincluded: {listing_data['food_charges_included']}\n"     

    if "bathrooms" in listing_data:
        if listing_data["bathrooms"] != 0:
            prompt_string += f"Bathrooms: {listing_data['bathrooms']}\n"
    
    if "pantry" in listing_data:
        prompt_string += f"Pantry: {listing_data['pantry']}\n"
    
    if "washroom_present" in listing_data:
        prompt_string += f"Washroom Present: {listing_data['washroom_present']}\n"

    if "parking" in listing_data:
        if listing_data["parking"] != 0:
            prompt_string += f"Parking: {listing_data['parking']}\n"
    
    if "price" in listing_data:
        formatted_price = format_currency(listing_data['price'], 'INR', locale='en_IN')[1:].split('.')[0]
        prompt_string += f"Price: {formatted_price}\n"
    
    # Concatenate area and area_unit and remove full stops, if any
    if "area" in listing_data and "area_unit" in listing_data:
        prompt_string += f"Area: {listing_data['area']} {listing_data['area_unit'].replace('.', '')}\n"
    
    if "facing" in listing_data:
        prompt_string += f"Facing: {listing_data['facing']}\n"
    
    if "property_age" in listing_data:
        prompt_string += f"Property Age: {listing_data['property_age']}\n"
    
    if "plot_number" in listing_data:
        prompt_string += f"Plot Number: {listing_data['plot_number']}\n"
    
    if "floor_number" in listing_data:
        if listing_data["floor_number"] != 0:
            prompt_string += f"Floor number: {listing_data['floor_number']}\n"
        
    if "total_floor_count" in listing_data:
        if listing_data["total_floor_count"] != 0:
            prompt_string += f"Total Floor Count: {listing_data['total_floor_count']}\n"

    if "amenities" in listing_data:
        prompt_string += f"Amenities: {listing_data['amenities']}\n"

    if "description" in listing_data:
        prompt_string += f"Description: {listing_data['description']}\n"

    return prompt_string


def create_prompt(listing_form_data):
    """
    Creates the prompt for a given listing data by adding examples followed by incoming
    data
    """
    listing_data = dict(listing_form_data)
    examples = get_examples(listing_data['property_type'], listing_data['listing_type'])
    prompt_string = ""
    for example in examples:
        prompt_string += format_listing_data(example)
        prompt_string += "\n\n-----\n\n"

    prompt_string += format_listing_data(listing_data)
    prompt_string += 'Description:'
    return prompt_string


def format_description(description):
    """
    Breaks descriptions into sentences and the creates format with first paragraph,
    body (bullet points array) and last paragraph
    """
    sentences = list(map(str.strip, description.split('. ')[:-1]))
    sentences = [f'{sentence}.' for sentence in sentences]
    formatted_description = {
        'first_paragraph': sentences[0],
        'body': sentences[1:-1],
        'last_paragraph': sentences[-1]
    }
    return formatted_description

