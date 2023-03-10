 
import spacy
from spacy.matcher import Matcher

nlp = spacy.load("en_core_web_sm", disable=['parser', 'ner'])

numberMatcher = Matcher(nlp.vocab)
numberMatcher.add("like_num",[[{"LIKE_NUM":True}, {"LIKE_NUM":True, "OP": "?"}, {"LIKE_NUM":True, "OP": "?"}, \
                                {"LIKE_NUM":True, "OP": "?"}, {"LIKE_NUM":True, "OP": "?"}, \
                                {"LIKE_NUM":True, "OP": "?"}]])
numberMatcher.add("like_digit",[[{"LIKE_NUM":True}]])

matcher = Matcher(nlp.vocab)
matcher.add("bedroom", [[{"LIKE_NUM":True}, {"LEMMA":"bedroom"}], [{"LIKE_NUM":True},{"LEMMA":"bhk"}]])
matcher.add("total_floor_count", [[{"IS_DIGIT":True}, {"LOWER":"storied"}], \
                                    [{"IS_DIGIT":True}, {"LOWER":"story"}], \
                                    [{"IS_DIGIT":True},{"LOWER":"floors"}]])
matcher.add("floor_number", [[{"LIKE_NUM":True}, {"LIKE_NUM":True, "OP": "?"}, \
                                {"LIKE_NUM":True, "OP": "?"}, {"LIKE_NUM":True, "OP": "?"}, \
                                {"LIKE_NUM":True, "OP": "?"}, {"LIKE_NUM":True, "OP": "?"}, \
                                {"LOWER":"floor"}]])
matcher.add("price",[[{"LEMMA":"rs"}, {"LIKE_NUM":True}, {"LIKE_NUM":True, "OP": "?"}, {"LIKE_NUM":True, "OP": "?"}, \
            {"LIKE_NUM":True, "OP": "?"}, {"LIKE_NUM":True, "OP": "?"}, {"LIKE_NUM":True, "OP": "?"}]])

specialMatcher = Matcher(nlp.vocab)
specialMatcher.add("minus_bw", [[{"IS_DIGIT":True}, {"LOWER":"-"}, {"IS_DIGIT":True}]])
specialMatcher.add("plus_end", [[{"IS_DIGIT":True}, {"LOWER":"+"}]])

specialCharMatcher = Matcher(nlp.vocab)
specialCharMatcher.add("minus", [[{"LOWER":"-"}]])
specialCharMatcher.add("plus", [[{"LOWER":"+"}]])

character_replacements = {"-": "__minus__", "+":"__plus__"}
inverse_character_replacements = {"__minus__": "-", "__plus__":"+"}

furnishMatcher = Matcher(nlp.vocab)
furnishMatcher.add("furnish", [[{"LOWER":"unfurnish"}], [{"LOWER":"unfurnished"}], [{"LOWER":"un"}, {"LOWER":"furnish"}], \
                        [{"LOWER":"un"}, {"LOWER":"furnished"}] , [{"LOWER":"not"}, {"LOWER":"furnish"}], [{"LOWER":"not"}, {"LOWER":"furnished"}], \
                        [{"LOWER":"semi"}, {"LOWER":"furnish"}], [{"LOWER":"semi"}, {"LOWER":"furnished"}], \
                        [ {"LOWER":"semifurnish"}], [ {"LOWER":"semifurnished"}], [{"LOWER":"fully", "LOWER":"furnish"}], [{"LOWER":"fully", "LOWER":"furnished"}],\
                        [{"LOWER":"well"}, {"LOWER":"furnish"}], [{"LOWER":"well"}, {"LOWER":"furnished"}]])


