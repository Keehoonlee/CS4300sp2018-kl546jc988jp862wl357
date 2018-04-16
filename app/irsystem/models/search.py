from collections import defaultdict
#import sentiment_analysis
import json
from datetime import datetime
import os


##########################################HELPERS#################################################
DEFAULT = 0
LIMIT = 0.05

def format_percentage_for_html(percentages):
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
def filter_reviews(j, neighborhood, credibility, time_limit):
    """Filter the reviews that match with user inputs.
    ***ASSUMES THAT JSON OBJECT HAS SAME TYPE AS THE INPUTS***

    Returns a list of reviews"""
    filtered_out_reviews = []

    time_limit = int(time_limit)

    for review in j["reviews"]:
        #if neighborhood.lower()
        if (review["business"]["neighborhood"].lower() == neighborhood.lower()):
            #credibility = DEFAULT if credibility == 0 else 1
            #cond1 = ((credibility != "All Users") and (review["elite_years"]["year"] >= (how YELP does it))) or (credibility == "All Users")
            #NEEDS TO HAVE A FUNCTION THAT COMPARES THIS TWO
            cond2 = ((time_limit != DEFAULT) and (compare_timelimit_timeposted(time_limit, review["date"]))) or (time_limit == DEFAULT)
            #cond3 = ((price_range != None) and (review["restaurant_price_range"] == price_range)) or (price_range == None)

            if (cond2):
                filtered_out_reviews.append(review)

    return filtered_out_reviews

def filter_pos_reviews(reviews):
    """Filter the reviews that are positive from [reviews].
    Review is considered positive if its sentiment intensity is >=0.1

    [reviews]: list of JSON objects"""

    pos_reviews = []
    for review in reviews:
        if (review["sentiment_score"]>=0.75):
            pos_reviews.append(review)

    return pos_reviews

def filter_neg_reviews(reviews):
    """Filter the reviews that are negative from [reviews].
    Review is considered negative if its sentiment intensity is <=-0.1

    [reviews]: list of JSON objects"""

    neg_reviews = []
    for review in reviews:
        if (review["sentiment_score"]<=-0.2):
            neg_reviews.append(review)

    return neg_reviews

###############################COMPUTING PERCENTAGES OF EACH category##################################
def filter_category(category_lst):
    """Returns a list of categories of a restaurant that are accepted"""

    african = ["african", "senegalese", "south african"]
    american = ["american (new)", "american (traditional)", "chicken wings", "soul food", "comfort food"]
    dessert = ["creperies", "waffles"]
    central_american = ["honduran", "nicaraguan"]
    east_european = ["hungarian", "polish", "russian", "ukrainian", "slovakian", "german", "bulgarian"]
    asian_fusion = ["asian fusion", "pan asian"]
    brunch_diners = ["breakfast & brunch", "diners"]
    british = ["british", "fish & chips"]
    cafes = ["cafes", "themed cafes", "cafeteria", "hong kong style cafe"]
    caribbean = ["caribbean", "dominican", "haitian", "puerto rican", "trinidadian"]
    chinese = ["chinese", "dim sum", "hot pot", "cantonese", "hainan", "shanghainese", "szechuan"]
    fast_food = ["hot dogs", "food stands", "burgers", "pizza"]
    french = ["french", "mauritius", "reunion"]
    italian = ["italian", "calabrian", "sardinian", "sicilian", "tuscan"]
    japanese = ["japanese", "sushi bars", "izakaya", "japanese curry", "ramen", "teppanyaki"]
    latin_american = ["latin american", "colombian", "salvadoran", "venezuelan"]
    mediterranean = ["mediterranean", "falafel"]
    mexican = ["mexican", "tacos", "new mexican cuisine", "tex-mex"]
    middle_eastern = ["middle eastern", "egyptian", "lebanese", "turkish"]
    sandwiches = ["sandwiches", "wraps", "delis"]
    spanish = ["spanish", "catalan"]
    steakhouses = ["steakhouses", "cheesesteaks", "game meat"]
    tapas = ["tapas bars", "tapas/small plates"]
    thai = ["thai", "laotian"]
    vegan = ["vegan", "vegetarian", "salad"]
    others = ["afghan", "arabian", "argentine", "armenian", "australian", "austrian", "bangladeshi", \
              "barbeque", "cajun/creole", "cambodian", "cuban", "czech", "ethiopian", "filipino", "gastropubs", \
              "gluten-free", "greek", "guamanian", "halal", "hawaiian", "himalayan/nepalese", "iberian", "indian", \
              "indonesian", "irish", "kebab", "korean", "kosher", "malaysian", "modern european", "mongolian", \
              "moroccan", "noodles", "pakistani", "persian/iranian", "peruvian", "portuguese", "poutineries", \
              "scandinavian", "scottish", "seafood", "singaporean", "soup", "southern", "syrian", "taiwanese", "vietnamese"]

    categories = [african, american, dessert, central_american, east_european, asian_fusion, brunch_diners, british, cafes, \
                  caribbean, chinese, fast_food, french, italian, japanese, latin_american, mediterranean, mexican, middle_eastern, \
                  sandwiches, spanish, steakhouses, tapas, thai, vegan, others]
    category_names = ["african", "american", "dessert", "central american", "east european", "asian fusion", "brunch/diners", "british", \
                      "cafes", "caribbean", "chinese", "fast food", "french", "italian", "japanese", "latin american", "mediterranean", \
                      "mexican", "middle eastern", "sandwiches", "spanish", "steakhouses", "tapas", "thai", "vegan", "others"]
    output = []
    #for each t in category_lst
    for t in category_lst:
        #go through possible categories to see which category t fits into
        for idx,category in enumerate(categories):
            if t.lower() in category:
                #If t belongs in [other], t keeps its category name
                if category_names[idx] == "others":
                    output.append(t.lower())
                #If t does not belong in [other], grouped name is added
                else:
                    output.append(category_names[idx])

    return output

def compute_percentage_per_category(reviews):
    """Computes the percentages of the reviews for each category.
    ***NOTE: Single restaurant can be assigned multiple categories.
    ***NOTE: Review might not have a category key.

    Returns a dictionary in format {\ category: percentage}

    [reviews]: list of JSON objects"""

    n_reviews = 0
    percentage_dict = defaultdict(float)

    #Iterating through every review and see which category the review belongs to
    for review in reviews:
        #Single restaurant can be assigned multiple categories
        #Review might not have a category key
        try:
            rest_category_lst = filter_category(review["business"]["category"])
            n_reviews += len(rest_category_lst)
            for t in rest_category_lst:
                percentage_dict[t] += 1.0
        except KeyError:
            pass

    for rest_category in percentage_dict.keys():
        percentage_dict[rest_category] = (percentage_dict[rest_category]/n_reviews)

    output = sorted(percentage_dict.items(), key=lambda x: x[1], reverse=True)
    return output

###############################COMPUTING TOP RESTAURANTS PER category##################################
def filter_reviews_category(reviews,category):
    """Filter [reviews] by [category].
    Returns a list of JSON objects."""

    reviews_of_category = []
    for review in reviews:
        #Review might not have a category key
        try:
            rest_category_lst = filter_category(review["business"]["category"])
            if (category in rest_category_lst):
                reviews_of_category.append(review)
        except KeyError:
            pass

    return reviews_of_category

def compute_top_rest(reviews, neg):
    """Computes the top restaurant for [reviews].
    Returns a sorted list of 5 restaurants in the order of decreasing popularity."""

    rest_stars_dict = defaultdict(int)

    for review in reviews:
        rest_stars_dict[review["business"]["name"]] += int(review["stars"])

    #normalizing
    for restaurant, stars in rest_stars_dict.items():
        rest_stars_dict[restaurant] /= len(reviews)

    ranked_rest_lst = []
    srted_lst = (sorted(rest_stars_dict, key=rest_stars_dict.get) if neg else sorted(rest_stars_dict, key=rest_stars_dict.get, reverse=True))
    for k in srted_lst:
        try:
            ranked_rest_lst.append(k.encode('ascii'))
        except:
            pass

    return ranked_rest_lst[:5]

def compute_top_rest_per_category(reviews, neg):
    """Computes the top restaurant list for each category in [reviews] that has
    review percentage over 1%

    Returns a dicitonary in format {\cuisine category: lst of top 5 restaurants}

    If neg == True, then finding the bottom 5 restaurants"""

    rest_per_category_dict = defaultdict(list)
    percentages = compute_percentage_per_category(reviews)

    for category,percentage in percentages:
        if percentage >= LIMIT:
            reviews_of_category = filter_reviews_category(reviews,category)
            top_rest_list = compute_top_rest(reviews_of_category,neg)
            rest_per_category_dict[category] = top_rest_list

    return rest_per_category_dict

# j = load_json("pittsburgh")
# all_reviews = filter_reviews(j, "shadyside", 0, 0)
# percentages_all_reviews = compute_percentage_per_category(all_reviews)
# top_rest_all_reviews = compute_top_rest_per_category(all_reviews)
#
# label, data = format_for_html(percentages_all_reviews, top_rest_all_reviews)
# print(percentages_all_reviews)
# print(top_rest_all_reviews)
# print(label)
# print(data)
