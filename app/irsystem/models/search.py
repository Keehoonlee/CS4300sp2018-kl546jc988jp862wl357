from collections import defaultdict
#import sentiment_analysis
import json
from datetime import datetime
import os
import re
from collections import Counter
from nltk.tokenize import TreebankWordTokenizer
import numpy as np
from query_expand import *


##########################################HELPERS#################################################
DEFAULT = 0
POS_SCORE_LIMIT = 0.4
NEG_SCORE_LIMIT = - 0.025
REVIEW = 0
SCORE = 1
MIN_POS_SCORE = 0.08
MIN_NEG_SCORE = - 0.005

LIMIT = 0.05

def format_percentage_for_html(percentages):
    """Normalizing the percentages so we take out categories that are lower than LIMIT"""
    others = 0
    labels = []
    data = []

    for category, percentage in percentages:
        if percentage >= LIMIT:
            formatted_category = category[0].capitalize() + category[1:]
            labels.append(formatted_category)
            data.append(percentage)
        else:
            others += percentage

    #Normalize each percentage by the number of others
    normalize = (1-others)

    for idx, percentage in enumerate(data):
        data[idx] = round((percentage/normalize)*100)

    return (labels,data)

def load_json(cityname):
    MYDIR = os.path.dirname(__file__)
    file_name = cityname.lower()+".json"
    with open(os.path.join(MYDIR,file_name)) as json_file:
        json_data = json.load(json_file)

    return json_data

def apply_delta(date,delta):
    """Returns datetime object after applying delta on date"""
    month = (date.month+delta)%12
    year = date.year + (date.month+delta-1)//12

    if month == 0: month = 12

    day = min(date.day, [31,29 if year%4==0 and not year%400==0 else 28,31,30,31,30,31,31,30,31,30,31][month-1])

    return date.replace(year=year, month=month, day=day)

def compare_timelimit_timeposted(time_limit, time_posted):
    """Returns true if the review's time posted satisfies the user input's time limit

    time_posted: 'yyyy-mm-dd hh:mm:ss'"""
    today = datetime.now()

    #Expressing the today - time_limit in form of datetime object
    time_limit_date = apply_delta(today, -time_limit)

    #Expressing the time_posted in form of datetime object
    time_posted_yr = int(time_posted[:4])
    time_posted_m = int(time_posted[5:7])
    time_posted_d = int(time_posted[8:10])
    time_posted_date = datetime(time_posted_yr, time_posted_m, time_posted_d)

    if time_limit_date <= time_posted_date:
        return True
    else:
        return False

#######################################FILTERING REVIEWS############################################
def filter_reviews(reviews, neighborhood, credibility, time_limit):
    """Filter the reviews that match with user inputs.

    Returns a list of reviews"""
    filtered_out_reviews = []

    time_limit = int(time_limit)

    USEFUL = 5

    for review in (reviews):
        if (review["business"]["neighborhood"].lower() == neighborhood.lower()):
            cond1 = ((credibility != "All Users") and (int(review["useful"]) >= USEFUL)) or (credibility == "All Users")
            cond2 = ((time_limit != DEFAULT) and (compare_timelimit_timeposted(time_limit, review["date"]))) or (time_limit == DEFAULT)

            if (cond1 and cond2):
                filtered_out_reviews.append(review)

    return filtered_out_reviews

###############################COMPUTING RESTAURANTS AND PERCENTAGES PER RESTAURANTS##################################
def filter_reviews_calc_percentage_by_category(reviews):
    """Filter [reviews] by category and Compute percentage for each category of [reviews].
    Returns a dictionary in format {\category: list of reviews} and
    a list of tuples [(category, percentage)] in a decreasing order

    ***NOTE: Single restaurant can be assigned multiple categories.
    ***NOTE: Review might not have a category key."""

    n_reviews = 0
    percentage_per_category_dict = defaultdict(float)
    reviews_per_category = defaultdict(list)

    for review in reviews:
        try:
            #Creating a lst of reviews per category
            rest_category_lst = review["business"]["category"]
            for category in rest_category_lst:
                reviews_per_category[category] += [review]

            #Computing percentages
            n_reviews += len(rest_category_lst)
            for category in rest_category_lst:
                percentage_per_category_dict[category] += 1.0

        except KeyError:
            pass

    #Computing percentages
    for rest_category in percentage_per_category_dict.keys():
        percentage_per_category_dict[rest_category] = (percentage_per_category_dict[rest_category]/n_reviews)

    srted_category_percentages_lst = sorted(percentage_per_category_dict.items(), key=lambda x: x[1], reverse=True)

    return reviews_per_category, srted_category_percentages_lst

def compute_rest_infos(reviews, time_limit, sorting):
    """Computes the top popular restaurants and respective stars and address and
    other infos for [reviews]."""

    ranked_rest_infos_dict = defaultdict(float)
    review_count_per_business = defaultdict(int)
    address_dict = defaultdict()
    sentiment_sim_review_dict = defaultdict(list)
    n_reviews = len(reviews)
    category_stars = 0.0

    #Counting the stars and otheri nfos given to the business
    for review in reviews:
        ranked_rest_infos_dict[review["business"]["name"]] += float(review["stars"])
        review_count_per_business[review["business"]["name"]] += 1
        address_dict[review["business"]["name"]] = review["business"]["address"]
        parsed_review = re.sub(r'[\n\r]+', '', review['sentiment_sentence'])
        #parsed_review = '.'.join(review["sentiment_sentence"].split("\n")) #Required as newline characters cause error in html
        sentiment_sim_review_dict[review["business"]["name"]] += [(review["sentiment_score"]*review["sim_score"], parsed_review)]
        category_stars += float(review["stars"])

    if n_reviews == 0:
        category_stars = 0
    else:
        category_stars = round(category_stars/n_reviews,1)

    #Only using the top reviews that have the highest sentiment score and lowest sentiment score
    for restaurant, lst_of_reviews in sentiment_sim_review_dict.items():
        srted_reviews = []
        for score, review in sorted(lst_of_reviews,key=lambda x: x[0]):
            srted_reviews.append((review, score))

        sentiment_sim_review_dict[restaurant] = srted_reviews

    #Normalizing the stars
    for restaurant, stars in ranked_rest_infos_dict.items():
        ranked_rest_infos_dict[restaurant] = round(ranked_rest_infos_dict[restaurant]/review_count_per_business[restaurant],1)

    top_rest_infos_lst = []

    #Creating a list of (restaurant, star, and other infos) for top restaurants in the order of [sorting]
    #Error checking in case of there are not enough reviews to display
    if sorting == "rating":
        srted_restaurants = sorted(ranked_rest_infos_dict, key=ranked_rest_infos_dict.get, reverse=True)

    else:
        srted_restaurants = sorted(review_count_per_business, key=review_count_per_business.get, reverse=True)

    for num, rest in enumerate(srted_restaurants,1):
        if len(sentiment_sim_review_dict[rest]) >= 2:
            #Setting up positive Reviews
            first_pos_review = sentiment_sim_review_dict[rest][-1]
            second_pos_review = sentiment_sim_review_dict[rest][-2]
            i = 3
            #Taking care of duplicates
            while (first_pos_review[REVIEW] == second_pos_review[REVIEW]) and (i<=len(sentiment_sim_review_dict[rest])):
                second_pos_review = sentiment_sim_review_dict[rest][-i]
                i+=1

            if first_pos_review[REVIEW] == second_pos_review[REVIEW]:
                second_pos_review = ("No significant matching review", second_pos_review[SCORE])
            #Checking if top reviews are actually positive
            if first_pos_review[SCORE] < MIN_POS_SCORE:
                first_pos_review = ("No significant matching review", first_pos_review[SCORE])
                second_pos_review = ("No significant matching review", second_pos_review[SCORE])
            elif second_pos_review[SCORE] < MIN_POS_SCORE:
                second_pos_review = ("No significant matching review", second_pos_review[SCORE])

            #Setting up negative reviews
            first_neg_review = sentiment_sim_review_dict[rest][0]
            second_neg_review = sentiment_sim_review_dict[rest][1]
            i = 2
            #Taking care of duplicates
            while (first_neg_review[REVIEW] == second_neg_review[REVIEW]) and (i<=len(sentiment_sim_review_dict[rest])):
                second_neg_review = sentiment_sim_review_dict[rest][-i]
                i+=1

            if first_neg_review[REVIEW] == second_neg_review[REVIEW]:
                second_neg_review = ("No significant matching review", second_neg_review[SCORE])
            #Checking if bot reviews are actually negative
            if first_neg_review[SCORE] >= MIN_NEG_SCORE:
                first_neg_review = ("No significant matching review", first_neg_review[SCORE])
                second_neg_review = ("No significant matching review", second_neg_review[SCORE])
            elif second_neg_review[SCORE] >= MIN_NEG_SCORE:
                second_neg_review = ("No significant matching review", second_neg_review[SCORE])

            #If positive review == negative review, choose the appropriate one depending on the score
            if first_pos_review[REVIEW] == first_neg_review[REVIEW]:
                if first_pos_review[SCORE] >= MIN_POS_SCORE:
                    first_neg_review = ("No significant matching review", first_neg_review[SCORE])
                    second_neg_review = ("No significant matching review", second_neg_review[SCORE])
                elif first_pos_review[SCORE] <= MIN_NEG_SCORE:
                    first_pos_review = ("No significant matching review", first_pos_review[SCORE])
                    second_pos_review = ("No significant matching review", second_pos_review[SCORE])
                else:
                    first_neg_review = ("No significant matching review", first_neg_review[SCORE])
                    second_neg_review = ("No significant matching review", second_neg_review[SCORE])
                    first_pos_review = ("No significant matching review", first_pos_review[SCORE])
                    second_pos_review = ("No significant matching review", second_pos_review[SCORE])

            elif second_pos_review[REVIEW] == second_neg_review[REVIEW]:
                if second_pos_review[SCORE] >= 0:
                    second_neg_review = ("No significant matching review", second_neg_review[SCORE])
                else:
                    second_pos_review = ("No significant matching review", second_pos_review[SCORE])

            top_rest_infos_lst.append((str(num)+". "+rest, ranked_rest_infos_dict[rest], address_dict[rest], \
                                       first_pos_review[REVIEW], second_pos_review[REVIEW], \
                                       first_neg_review[REVIEW], second_neg_review[REVIEW], \
                                       review_count_per_business[rest]))

        elif len(sentiment_sim_review_dict[rest]) == 1:
            if sentiment_sim_review_dict[rest][0][SCORE] >= MIN_POS_SCORE:
                first_pos_review = sentiment_sim_review_dict[rest][0]
                first_neg_review = ("No significant matching review", sentiment_sim_review_dict[rest][0][SCORE])
            elif sentiment_sim_review_dict[rest][0][SCORE] <= MIN_NEG_SCORE:
                first_neg_review = sentiment_sim_review_dict[rest][0]
                first_pos_review = ("No significant matching review", sentiment_sim_review_dict[rest][0][SCORE])
            else:
                first_pos_review = ("No significant matching review", sentiment_sim_review_dict[rest][0][SCORE])
                first_neg_review = ("No significant matching review", sentiment_sim_review_dict[rest][0][SCORE])

            top_rest_infos_lst.append((str(num)+". "+rest, ranked_rest_infos_dict[rest], address_dict[rest], first_pos_review[REVIEW], \
                                       "No significant matching review", first_neg_review[REVIEW], "No significant matching review", review_count_per_business[rest]))
        else:
            top_rest_infos_lst.append((str(num)+". "+rest, ranked_rest_infos_dict[rest], address_dict[rest], \
                                       "No review", "No review", "No significant matching review", "No significant matching review", \
                                       review_count_per_business[rest]))
    if len(top_rest_infos_lst) >= 17:
        top_rest_infos_lst_1 = top_rest_infos_lst[:len(top_rest_infos_lst)/2]
        top_rest_infos_lst_2 = top_rest_infos_lst[len(top_rest_infos_lst)/2:]
    elif len(top_rest_infos_lst) >= 15 and len(top_rest_infos_lst) <=16:
        top_rest_infos_lst_1 = top_rest_infos_lst[:8]
        top_rest_infos_lst_2 = top_rest_infos_lst[8:16]
    elif len(top_rest_infos_lst) >= 13 and len(top_rest_infos_lst) <=14:
        top_rest_infos_lst_1 = top_rest_infos_lst[:7]
        top_rest_infos_lst_2 = top_rest_infos_lst[7:]
    elif len(top_rest_infos_lst) >= 11 and len(top_rest_infos_lst) <=12:
        top_rest_infos_lst_1 = top_rest_infos_lst[:6]
        top_rest_infos_lst_2 = top_rest_infos_lst[6:]
    elif len(top_rest_infos_lst) >= 9 and len(top_rest_infos_lst) <=10:
        top_rest_infos_lst_1 = top_rest_infos_lst[:5]
        top_rest_infos_lst_2 = top_rest_infos_lst[5:]
    elif len(top_rest_infos_lst) >= 7 and len(top_rest_infos_lst) <=8:
        top_rest_infos_lst_1 = top_rest_infos_lst[:4]
        top_rest_infos_lst_2 = top_rest_infos_lst[4:]
    elif len(top_rest_infos_lst) >= 5 and len(top_rest_infos_lst) <=6:
        top_rest_infos_lst_1 = top_rest_infos_lst[:3]
        top_rest_infos_lst_2 = top_rest_infos_lst[3:]
    elif len(top_rest_infos_lst) >= 3 and len(top_rest_infos_lst) <=4:
        top_rest_infos_lst_1 = top_rest_infos_lst[:2]
        top_rest_infos_lst_2 = top_rest_infos_lst[2:]
    elif len(top_rest_infos_lst) == 2:
        top_rest_infos_lst_1 = top_rest_infos_lst[:1]
        top_rest_infos_lst_2 = top_rest_infos_lst[1:]
    else:
        top_rest_infos_lst_1 = top_rest_infos_lst
        top_rest_infos_lst_2 = []

    return (top_rest_infos_lst_1, top_rest_infos_lst_2, category_stars)

def compute_rest_infos_and_pos_neg_per_category(reviews, percentages, reviews_per_category, time_limit, sorting):
    """Computes the top  restaurants  for each category in [reviews]
    that has review percentage over [LIMIT]. Returns lst of (rest, stars, address, (later chosen)).

    Computes percentage of positive/negative/neutral reviews per category (if its percentage >= LIMIT).
    Returns a list in format [[pos percentage, neg percentage]]. """

    top_rest_infos_per_category_1 = []
    top_rest_infos_per_category_2 = []
    pos_neg_percentages_per_category = []
    top_stars = 0
    top_category = ""
    top_category_percentages = [0,0]

    for category, percentage in percentages:
        pos = 0.0
        neg = 0.0
        neutral = 0.0
        if percentage >= LIMIT:
            #Computing sorted top restaurants per category
            reviews_of_category = reviews_per_category[category]
            top1,top2, category_stars = compute_rest_infos(reviews_of_category, time_limit, sorting)
            top_rest_infos_per_category_1.append(top1)
            top_rest_infos_per_category_2.append(top2)

            #Counting how many of the reviews are positive or negative
            for review in reviews_of_category:
                if (review["sentiment_score"]>=POS_SCORE_LIMIT):
                    pos += 1.0
                elif (review["sentiment_score"]<NEG_SCORE_LIMIT):
                    neg += 1.0
                else:
                    neutral += 1.0

            #Normalizing by number of neutral
            neutral = round((neutral / len(reviews_of_category))*100,0)
            pos_percentage = round((pos / len(reviews_of_category))*100,0)
            neg_percentage = round((neg / len(reviews_of_category))*100,0)

            pos_neg_percentages_per_category.append([pos_percentage, neg_percentage, neutral])

            #Calculating the top category with highest average ratings overall
            if category_stars >= top_stars:
                top_stars = category_stars
                top_category = category
                top_category_percentages = [pos_percentage, neg_percentage, neutral]

    return top_rest_infos_per_category_1, top_rest_infos_per_category_2, top_category, top_stars, top_category_percentages, pos_neg_percentages_per_category


######################COMPUTING SIMILARITY BETWEEN THE FILTERED REVIEWS AND THE QUERY#####################
def compute_similarity(j, query, tf, idf, doc_norm, review_idx_mapping, neighborhood):
    """Calculates similarity score bewteen query and each review. Returns a list of review objects with
    similarity score attached"""
    if query == "":
        new_reviews = []
        for review in j["reviews"]:
            new_review = review
            new_review["sim_score"] = 1
            new_reviews.append(new_review)
        return new_reviews

    tokenizer = TreebankWordTokenizer()
    doc_scores = np.zeros(len(doc_norm)) # Initialize D

    query = query.lower()
    tokenized_query = tokenizer.tokenize(query)
    counter = Counter(tokenized_query)
    counter = {token: count for (token, count) in counter.items() if token in idf}
    query_token_to_idx = {token: idx for idx, (token, _) in enumerate(counter.items())}

    for token, count in counter.items():
        cur_token_idx = query_token_to_idx[token]
        q_tfidf = count * idf[token] # Construct q

        for doc_id, freq in tf[token]:
            doc_scores[doc_id] += q_tfidf * freq * idf[token] # Construct D

    for idx in range(len(doc_norm)):
        doc_scores[idx] = doc_scores[idx]/(doc_norm[idx]+1)

    neighborhood = neighborhood.lower()

    output = [(review_idx_mapping[neighborhood][i], doc_scores[i]) for i in range(len(doc_scores))]
    new_reviews = []
    for idx, score in output:
        new_review = j["reviews"][idx]
        new_review["sim_score"] = score
        new_reviews.append(new_review)
    return new_reviews

# j = load_json("pittsburgh")
# tf = load_json("tf")
# idf = load_json("idf")
# doc_norm = load_json("doc_norm")
# neigh_idx_lst = load_json("neighborhood_idx_dict")
# query = "food"
# neighborhood = "downtown"
# result_list = compute_similarity(j, query,tf[neighborhood],idf[neighborhood],doc_norm[neighborhood], neigh_idx_lst, neighborhood)
# #all_reviews = filter_reviews(result_list, "downtown", "All Users", 6)
# print(result_list)

# reviews_per_category, percentages_per_category = filter_reviews_calc_percentage_by_category(all_reviews)
# labels,_ = format_percentage_for_html(percentages_per_category)
# pos_neg_percentages_per_category = compute_pos_neg_percentages(reviews_per_category, percentages_per_category)
# top_restaurants_infos_per_category, bot_restaurants_infos_per_category = compute_rest_infos_per_category(all_reviews, percentages_per_category, reviews_per_category, 6)
# top_restaurants_infos_per_category_1, top_restaurants_infos_per_category_2 = compute_rest_infos_per_category(all_reviews, percentages_per_category, reviews_per_category, 6)


# print("Positive and Negative Percentages by Category:")
# print(pos_neg_percentages_per_category)
# print("\n")
# print("Restaurants with Infos by Category:")
# print(top_restaurants_infos_per_category)
# print("\n")
