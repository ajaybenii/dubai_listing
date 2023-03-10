import re
import locale

import inflect
from word2number import w2n
from fastapi import HTTPException
from nltk.stem import PorterStemmer

from matchers import nlp, matcher, specialMatcher, \
                     specialCharMatcher, numberMatcher, \
                     character_replacements, \
                     inverse_character_replacements, \
                     furnishMatcher

from utils import logger

UNIQUE_TOKEN_THRESHOLD = 0.43
TOKEN_THRESHOLD = 15
FURNISH_TOKEN = "__SPECIALTOKEN__"

ps = PorterStemmer()
inflect_engine = inflect.engine()
locale.setlocale(locale.LC_MONETARY, 'en_IN')

def replace_nth(str_):
    return str_.replace(",", "")\
                .replace("first", "one")\
                .replace("second", "two")\
                .replace("third", "three")\
                .replace("fourth", "four")\
                .replace("fifth", "five")\
                .replace("sixth", "six")\
                .replace("seventh", "seven")\
                .replace("eighth", "eight")\
                .replace("ninth", "nine")\
                .replace("st", "")\
                .replace("nd", "")\
                .replace("rd", "")\
                .replace("th", "")


def get_tokens(sentence_):
    """
    Custom function to tokenize the input sentence.
    """
    sentence_ = f"{sentence_}".lower().strip()
    sentence_ = sentence_.replace("-", " ")
    sentence_ = re.sub(" +", " ", sentence_)
    doc = nlp(sentence_)
    tokens = []
    for token in doc:
        cur = token.lemma_
        try:
            cur = str(int(replace_nth(cur)))
        except:
            pass
        cur = re.sub(r"[()\"/;:<>{}`+=~|!?']", "", cur)
        cur = re.sub(r"[.,']", " ", cur)
        cur = re.sub(" +", " ", cur)
        digit_to_eng = cur.replace("1", "one")\
                            .replace("2", "two")\
                            .replace("3", "three")\
                            .replace("4", "four")\
                            .replace("5", "five")\
                            .replace("6", "six")\
                            .replace("7", "seven")\
                            .replace("8", "eight")\
                            .replace("9", "nine")\
                            .replace("0", "zero")

        if len(digit_to_eng) == len(cur) and len(cur.strip()) >=2:
            tokens.append(ps.stem(cur))
        else:
            tokens.append(digit_to_eng)

    return tokens


def remove_duplicate_sentences(description):
    """
    This function removes the duplicate sentences from a string.
    """
    try:
        sents = description.lower().split(". ")

        sent_dict = {}
        for sent in sents:
            sent_dict[sent.strip()] = "."

        new_sents = []
        for k, _ in sent_dict.items():
            k = " " + k.strip().capitalize()
            new_sents.append(k)

        return_val = ". ".join(new_sents).strip()
        return return_val, return_val
    except Exception as e:
        print(e)
        print(description)
        
    return description, description


def strip_repeating_phrases(description):
    """
    This function strips the repeating phrases from the end of a string to some extent.
    """
    original_string = description.strip()
    original_splitted = original_string.lower().strip().split()

    phrase = ""
    size = len(original_splitted)
    for idx in range(size-1, (size//2)-1, -1):
        phrase = original_splitted[idx] + " " + phrase
        if phrase.strip() == " ".join(original_splitted[(2*idx) - size:idx]).strip():
            phrase = phrase.strip()
            break
        
    phrase_found = False
    if phrase != "":
        phrase_len = len(phrase)
        original_string = original_string.strip()
        while original_string.lower().endswith(phrase):
            original_string = original_string[:-phrase_len].strip()
            phrase_found = True
    
    if phrase_found:
        original_string = " ".join([original_string, phrase]).strip()

    return original_string, original_string


def get_scores(data, keywords):
    """
    This function takes a list of descriptions, scores them, sorts them according to  score and returns them.
    This function also does some text processing like- repeat phrase removal and repeat sentence removal before scoring.
    """
    scores_token_coverage = []
    scores_unique_tokens = []
    
    for idx in range(len(data['choices'])):
        description = data['choices'][idx]['text'].strip()

        # For the case where we get prompt appended before description.
        if description.count(":") >= 3 and (("description:" in description.lower()) or ("description :" in description.lower())):
            try:
                description = description[description.lower().rindex("description")+len("description"):]
                if ":" in description:
                    try:
                        idx_ = description.lower().find(":")
                        if idx_ != -1:
                            description = description[:idx_]
                            try:
                                description = description[:description.lower().rindex(" ")]
                            except:
                                pass
                    except:
                        pass
                description = description.replace(":", "").strip()
            except:
                pass
            data['choices'][idx]['text'] = description
        
        try:
            description, data['choices'][idx]['text'] = remove_duplicate_sentences(description)
        except Exception as e:
            print("Error in removing dup sentences", e)

        try:
            description, data['choices'][idx]['text'] = strip_repeating_phrases(description)
        except Exception as e:
            print("Error in removing dup phrases", e)

        description_keywords_list = get_tokens(description)
        description_keywords_set = set(description_keywords_list)
        common_keywords_set = keywords.intersection(description_keywords_set)
        s1 = 0
        s2 = 0
        if len(keywords) > 0:
            s1 = len(common_keywords_set) / len(keywords)
        if len(description_keywords_list) > 0:
            s2 = len(description_keywords_set) / len(description_keywords_list)
        scores_token_coverage.append(s1)
        scores_unique_tokens.append(s2)

    scores = [(y, x, idx) for y, x, idx in sorted(zip(scores_token_coverage,\
                                                        scores_unique_tokens,\
                                                        list(range(len(scores_unique_tokens)))),\
                                                        key=lambda pair: pair[0])]

    return scores, data


def get_best_description(data, description_scores):
    """
    This function takes list of description and description scores and returns the best description based on our criteria.
    If none of the descriptions match our criteria, then the description with max coverage score is returned.
    """
    correct_description_found = False
    description = None
    for i in range(len(description_scores)-1, -1, -1):
        cur_description = data['choices'][description_scores[i][2]]['text'].strip()
        if description_scores[i][1] >= UNIQUE_TOKEN_THRESHOLD and\
             len(get_tokens(cur_description)) >= TOKEN_THRESHOLD and\
             cur_description.count(":") <= 3:
            description = cur_description
            correct_description_found = True 
            return description, correct_description_found, description_scores[i][1], description_scores[i][0]

    max_coverage= max(description_scores, key=lambda x:x[1])
    description = data['choices'][max_coverage[2]]['text'].strip()
    
    return description, correct_description_found, max_coverage[1], max_coverage[0]


def encode_description_to_preserve_some_tokens(description):
    """
    This function encodes the strings to encode tokens like- `2-4 years`. It is done to preserve the naturalness of description.
    """
    doc = nlp(description)
    matches = specialMatcher(doc)

    for match_id, start, end in matches:
        matched_span = doc[start:end]
        match_category = nlp.vocab.strings[match_id]
        if match_category == "minus_bw":
            inner_doc = nlp(matched_span.text)
            for inner_match_id, inner_start, inner_end in specialCharMatcher(inner_doc):
                if nlp.vocab.strings[inner_match_id] == "minus":
                    inner_span = inner_doc[inner_start:inner_end]
                    replace_start_ = matched_span.start_char + inner_span.start_char
                    replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char )
                    description = " ".join([description[:replace_start_], str(character_replacements["-"]), description[replace_end_:]])
                    return description, True

        if match_category == "plus_end":
            inner_doc = nlp(matched_span.text)
            for inner_match_id, inner_start, inner_end in specialCharMatcher(inner_doc):
                if nlp.vocab.strings[inner_match_id] == "plus":
                    inner_span = inner_doc[inner_start:inner_end]
                    replace_start_ = matched_span.start_char + inner_span.start_char
                    replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char)
                    description = " ".join([description[:replace_start_], str(character_replacements["+"]), description[replace_end_:]])
                    return description, True
    
    return description, False


def remove_encodings(description_copy):
    """
    Function that removes the encodings of `encode_description_to_preserve_some_tokens` function.
    """
    description_copy = description_copy.replace(" __minus__ ", inverse_character_replacements["__minus__"])\
                                        .replace("__minus__ ", inverse_character_replacements["__minus__"])\
                                        .replace(" __minus__", inverse_character_replacements["__minus__"])\
                                        .replace(" __plus__", inverse_character_replacements["__plus__"] + " ")\
                                        .replace("__plus__", inverse_character_replacements["__plus__"] + " ")\

    return description_copy


def extract_number(text_):

    extracted_number = None
    number_text = replace_nth(text_.replace(",", ""))
    try:
        extracted_number = int(number_text)
    except Exception as e:
        try:
            extracted_number = w2n.word_to_num(number_text)
            print(e)
        except Exception as e:
            print("Inner exception", e)

    return extracted_number


def fix_description(description, listing_data):
    """
    Function that tries to fix the mistakes in description using spacy matchers.
    """
    description_orig = description
    doc = nlp(description)
    matches = matcher(doc)

    for match_id, start, end in matches:
        try:
            matched_span = doc[start:end]
            match_category = nlp.vocab.strings[match_id]

            # Fix bedroom numbers
            if match_category == "bedroom":
                try:
                    listing_data.bedrooms
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_num":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)
                        try:
                            if float(inner_span.text) != float(listing_data.bedrooms):
                                description = " ".join([description[:replace_start_], str(listing_data.bedrooms), description[replace_end_:]])
                                return description, True
                        except Exception as e:
                            print(e)
                if " bhk " in matched_span.text and "bedroom" not in description:
                    if "1" in matched_span.text or "one" in matched_span.text:
                        description = description.replace("bhk", "bedroom")
                    else:
                        description = description.replace("bhk", "bedrooms")
                    return description, True

            # Fix floor count
            elif match_category == "total_floor_count":
                try:
                    listing_data.total_floor_count
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_digit":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)
                        try:
                            if int(inner_span.text) != listing_data.total_floor_count:
                                description = " ".join([description[:replace_start_], str(int(listing_data.floor_number + 2)), description[replace_end_:]])
                                return description, True
                        except Exception as e:
                            print(e)
            
            # Fix floor number
            elif match_category == "floor_number":
                try:
                    listing_data.floor_number
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_num":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)

                        extracted_floor_number = extract_number(inner_span.text)
                        
                        if extracted_floor_number != None and extracted_floor_number != listing_data.floor_number:
                            floor_number_to_display = None
                            if listing_data.floor_number == 0:
                                floor_number_to_display = "ground"
                            else:
                                floor_number_to_display = inflect_engine.ordinal(listing_data.floor_number)

                            description = " ".join([description[:replace_start_], str(floor_number_to_display), description[replace_end_:]])
                            
                            return description, True

                        elif listing_data.floor_number == extracted_floor_number and listing_data.floor_number == 0:
                            floor_number_to_display = "ground"
                            description = " ".join([description[:replace_start_], str(floor_number_to_display), description[replace_end_:]])
                            
                            return description, True
            
            # Fix price
            elif match_category == "price":
                try:
                    listing_data.price
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_num":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)

                        extracted_price = extract_number(inner_span.text)
                        
                        if extracted_price != None and extracted_price != listing_data.price:
                            price_to_display = locale.currency(listing_data.price, grouping=True)[1:]

                            description = " ".join([description[:replace_start_], str(price_to_display), description[replace_end_:]])
                            
                            return description, True
        except Exception as e:
            print(e)

    return description, False

def fix_description_fine_tune(description, listing_data):
    """
    Function that tries to fix the mistakes in description using spacy matchers.
    """
    description_orig = description
    doc = nlp(description)
    matches = matcher(doc)

    for match_id, start, end in matches:
        try:
            matched_span = doc[start:end]
            match_category = nlp.vocab.strings[match_id]

            # Fix bedroom numbers
            if match_category == "bedroom":
                try:
                    listing_data.bedrooms
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_num":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)
                        try:
                            if float(inner_span.text) != float(listing_data.bedrooms):
                                description = " ".join([description[:replace_start_], str(listing_data.bedrooms), description[replace_end_:]])
                                return description
                        except Exception as e:
                            print(e)
                if " bhk " in matched_span.text and "bedroom" not in description:
                    if "1" in matched_span.text or "one" in matched_span.text:
                        description = description.replace("bhk", "bedroom")
                    else:
                        description = description.replace("bhk", "bedrooms")
                    return description

            # Fix floor count
            elif match_category == "total_floor_count":
                try:
                    listing_data.total_floor_count
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_digit":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)
                        try:
                            if int(inner_span.text) != listing_data.total_floor_count:
                                description = " ".join([description[:replace_start_], str(int(listing_data.floor_number + 2)), description[replace_end_:]])
                                return description
                        except Exception as e:
                            print(e)
            
            # Fix floor number
            elif match_category == "floor_number":
                try:
                    listing_data.floor_number
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_num":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)

                        extracted_floor_number = extract_number(inner_span.text)
                        
                        if extracted_floor_number != None and extracted_floor_number != listing_data.floor_number:
                            floor_number_to_display = None
                            if listing_data.floor_number == 0:
                                floor_number_to_display = "ground"
                            else:
                                floor_number_to_display = inflect_engine.ordinal(listing_data.floor_number)

                            description = " ".join([description[:replace_start_], str(floor_number_to_display), description[replace_end_:]])
                            
                            return description

                        elif listing_data.floor_number == extracted_floor_number and listing_data.floor_number == 0:
                            floor_number_to_display = "ground"
                            description = " ".join([description[:replace_start_], str(floor_number_to_display), description[replace_end_:]])
                            
                            return description
            
            # Fix price
            elif match_category == "price":
                try:
                    listing_data.price
                except:
                    continue
                inner_doc = nlp(matched_span.text)
                for inner_match_id, inner_start, inner_end in numberMatcher(inner_doc):
                    if nlp.vocab.strings[inner_match_id] == "like_num":
                        inner_span = inner_doc[inner_start:inner_end]
                        replace_start_ = matched_span.start_char + inner_span.start_char
                        replace_end_ = replace_start_ + (inner_span.end_char - inner_span.start_char + 1)

                        extracted_price = extract_number(inner_span.text)
                        
                        if extracted_price != None and extracted_price != listing_data.price:
                            price_to_display = locale.currency(listing_data.price, grouping=True)[1:]

                            description = " ".join([description[:replace_start_], str(price_to_display), description[replace_end_:]])
                            
                            return description
        except Exception as e:
            print(e)

    return description

def fix_furnish(description, furnishing_val):
    """
    The function that tries to fix the furnishing information using simple conditions and rules.
    """
    furnishing_val = re.sub(" +", " ", furnishing_val)
    if (("not furnished" in furnishing_val) or ("unfurnished" in furnishing_val) or \
        ("un furnished" in furnishing_val)) and (("not furnished" not in description) and \
        ("unfurnished" not in description) and ("un furnished" not in description)):
        if "semi furnished" in description:
            description = description.replace("semi furnished", "not-furnished")
        elif " furnished " in description:
            description = description.replace("furnished", "not-furnished")

    elif (("not furnished" not in furnishing_val) and ("unfurnished" not in furnishing_val) and ("un furnished" not in furnishing_val)):
        if "not furnished" in description:
            description = description.replace("not furnished", furnishing_val)
        elif "unfurnished" in description:
            description = description.replace("unfurnished", furnishing_val)
        elif "un furnished" in description:
            description = description.replace("un furnished", furnishing_val)

    elif "semi furnished" in furnishing_val and "semi furnished" not in description:
        if "not furnished" in description:
            description = description.replace("not furnished", "semi-furnished")
        elif "unfurnished" in description:
            description = description.replace("unfurnished", "semi-furnished")
        elif "un furnished" in description:
            description = description.replace("unfurnished", "semi-furnished")
    
    return description


def fix_furnish_2(description):
    """
    The function that tries to fix the furnishing information using simple conditions and rules.
    """
    doc = nlp(description)
    matches = furnishMatcher(doc)
    tmp_token = FURNISH_TOKEN
    for match_id, start, end in matches:
        try:
            matched_span = doc[start:end]
            replace_start_ = matched_span.start_char
            replace_end_ = replace_start_ + len(matched_span.text)
            new_ = description.replace(matched_span.text, tmp_token)
            print("Furnish *******", new_)
            return new_, True
        except Exception as e:
            print("Furnish Exception")
            print(e)
    
    return description, False


if __name__ == "__main__":
    modified = True
    cnt = 0
    description_copy = "This is a very good builder floor for sale at an affordable price of rs 9,99,00,000. The property is located in sector 46 in gurgaon which is a prime location in delhi and is close to public transportation. The property is fully furnished and it has 2 bedrooms, 3 bathrooms and 2 parking slots. The property is 2-4 years old and is in an area of 1400 square feet. There are numerous amenities available here including a jogging cum cycling track, power backup, visitors’ parking, power backup and more."
    while modified and cnt < 3:
        cnt += 1
        description_copy, modified  = fix_furnish_2(description_copy)
        print(modified)