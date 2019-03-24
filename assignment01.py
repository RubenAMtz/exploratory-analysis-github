import requests
import json
from credentials import CREDENTIALS
import random
import pandas as pd
from tqdm import tqdm
import os
import numpy as np
import iso8601

# to remove:
from itertools import cycle


class GitHubAPI(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.response = None
        self.limit = False
        self.set_endpoints()
        # to remove:
        self.credentials = CREDENTIALS
        self.c = cycle(CREDENTIALS)
        self.remaining = None
        self.update_remaining()
        
    def get_users_since(self, since, per_page=100):
        self.response = self.request_get(self.endpoints[0].format(since=str(since), per_page=str(per_page)))
        return self.response.json()

    def get_user(self, user):
        self.response = self.request_get(self.endpoints[1].format(user=user))
        return self.response.json()
        
    def get_repos(self, user, per_page = 100):
        self.response = self.request_get(self.endpoints[2].format(user=user, per_page=str(per_page)))
        return self.response.json()
    
    def get_languages(self, user, repo):
        self.response = self.request_get(self.endpoints[3].format(user=user, repo=repo))
        return self.response.json()

    def check_limit(self):
        if self.remaining == 0:
            self.limit = True
        else:
            self.limit = False

    def update_remaining(self):
        response =  requests.get(self.endpoints[4], auth=(self.username, self.password))
        response = response.json()
        self.remaining = response['resources']['core']['remaining']

    def request_get(self, endpoint):
        self.check_limit()

        if self.limit:
            self.switch_user()
            self.update_remaining()
            return self.request_get(endpoint)
        
        self.remaining -= 1
        return requests.get(endpoint, auth=(self.username, self.password))
        
    def set_endpoints(self):
        self.endpoints = []
        self.endpoints.append('https://api.github.com/users?since={since}&per_page={per_page}')
        self.endpoints.append('https://api.github.com/users/{user}')
        self.endpoints.append('https://api.github.com/users/{user}/repos?per_page={per_page}')
        self.endpoints.append('https://api.github.com/repos/{user}/{repo}/languages')
        self.endpoints.append('https://api.github.com/rate_limit')

    # to remove:
    def switch_user(self):
        next_value = next(self.c)
        self.username = next_value[0]
        self.password = next_value[1]
        print("User switched")

if __name__ == "__main__":

    def get_users_from_gh(gh, save_path):
        """
        We know that the total amount of users in github, up today, is around 48M. As we are trying to find patterns in user
        behaviour we will try and sample users pseudo randomly and from the whole space, for that we will generate a spaced 
        list starting from 1 up to 48Million, the spacing will be set to steps of 48k, at each step we will generate a rand value
        that will be added to the current spacing value. This values will be used as an index to extract data.
        i.e. spacing value #1 + random value #1, spacing value #2 + random value #2 ..... up to spacing value #1k + rand value #1k
        
        For this request the github api allows us to get 100 consecutive users at each call, with a limit of 5k calls per hour per user.
        We will call 1k times * 100 users = 100k total users.
        """

        spacing = 48000
        random.seed(42)
        intervals = [spacing*i + x for i, x in enumerate(sorted(random.sample(range(0, spacing-100), 1000)))] #-100 so we dont overlap intervals

        # Create a placeholder dictionary to append all the users in a single structure
        users = {
            'login': [],
            'id': [],
            'type': [],
            'site_admin': [],
        }

        # do a call per interval value and pass it to the since parameter
        for since in tqdm(intervals):
            # this returns a list of 100 elements where each element is a github user
            response = gh.get_users_since(since=since, per_page=100)
            # iterate through each user and append the data into our structure
            for user in response:
                        
                users['login'].append(user['login'])
                users['id'].append(user['id'])
                users['type'].append(user['type'])
                users['site_admin'].append(user['site_admin'])

        pd.DataFrame(users).to_csv(save_path)

    def split_level_one(path_read):
        data = pd.read_csv(path_read)
        length = data.shape[0]
        chunk_size = length//len(CREDENTIALS)
        chunks = length//chunk_size
        for i in range(chunks):
            chunk = data.iloc[i * chunk_size : (i * chunk_size) + chunk_size]
            chunk.to_csv('first_level_' + str(i).zfill(2) + '.csv', index=False)

    def get_users_info(gh, path_read, path_write):

        """
        The GitHub API returns very few information about a user when calling for multiple users at once (get_users_from_gh(gh)),
        we have to access each individual user to extract more meaningful information.
        We will read our users_first_level.csv file to extract each login instance which corresponds to the username and call do
        a call per user.
        """
        #read csv, set first col as index
        users_data = pd.read_csv(path_read, index_col = 0)
        # we only care about usernames
        users = users_data['login']

        #Create a placeholder dictionary to store all the user info
        users_info = {
            'login': [],
            'id': [],
            'type': [],
            'site_admin': [],
            'company': [],
            'blog': [],
            'location': [],
            'hireable': [],
            'public_repos': [],
            'public_gists': [],
            'followers': [],
            'following': [],
            'created_at': [],
            'updated_at': []
        }

        # Interate through all users (100k), these are 100k calls.
        # NOTE: remember that the GitHub API only allows for 5k calls/hour per user, however, our wrapper has setup a strategy,
        # we have a list of credentials (username and password) we check the remaining calls per user at each call, once we hit the
        # limit we switch to another credential by means of switch_user() and we repeat the process. These credentials were provided
        # by close friends.

        for user_ in tqdm(users):
            # user_info is None when the request is None
            user_info = gh.get_user(user_)
            try:
                for key in users_info:
                    users_info[key].append(user_info[key])
            except KeyError:
                # save values as nan for when call returns None
                print("KeyError")
                for key in users_info:
                    users_info[key].append(np.nan)

        pd.DataFrame(users_info).to_csv(path_write)
    
    def get_repos_from_gh(gh, path_read, path_write):
        
        users_data = pd.read_csv(path_read, index_col = 0)
        
        # we only care about usernames
        users = users_data['login']
        # some rows are missing, drop them
        users = users.dropna()

        # Create a placeholder dictionary to store all the repos info, the info will have to be a summary of all the repos,
        # numeric values will be added, boolean values will be parsed to int and added together, for any other we will treat
        # them as boolean and parse them to int to add them again.

        # main placeholder dictionary
        repos = {
            # user:
            'login': [],
            # repos info (an auxiliary dictionary is created out of these)
            'stargazers_count': [],
            'watchers_count': [],
            'has_issues': [],
            'has_projects': [],
            'has_downloads': [],
            'has_wiki': [],
            'has_pages': [],
            'forks_count': [],
            'open_issues_count': [],
            'license': [],
            'forks': [],
            'open_issues': [],
            'watchers': [],
            # repos languages (an auxiliary dictionary is created out of these, these keys are not present in the upcoming data),
            # we will populate them by analysing each user's repo.
            'javascript': [],
            'python': [],
            'java': [],
            'ruby': [],
            'php': [],
            'c++': [],
            'css': [],
            'c#': [],
            'go': [],
            'c': [],
            'typescript': [],
            'shell': [],
            'swift': [],
            'scala': [],
            'objective-c': [],
            'r': [],
            'others': []
        }

        # for every user
        for user in tqdm(users):
            # get all the user repos (a max of 60 repos per user is used)
            user_repos = gh.get_repos(user)
            
            # auxiliary placeholder dictionary (this structure is similar to the upcoming data)
            summary = {
                'stargazers_count': [], # int
                'watchers_count': [], # int
                'has_issues': [], # bool
                'has_projects': [], # bool
                'has_downloads': [], # bool
                'has_wiki': [], # bool
                'has_pages': [], # bool
                'forks_count': [], # int
                'open_issues_count': [], # int
                'license': [], # str or None
                'forks': [], # int
                'open_issues': [], # int
                'watchers': [], # int
                'language': [] # str or None
            }

            # all summary keys without 'language'
            summary_keys_no_lg = list(summary.keys())[:-1]
            
            # auxiliary placeholder dictionary (will populate keys from our main placeholder dictionary)
            languages = {
                'javascript': 0,
                'python': 0,
                'java': 0,
                'ruby': 0,
                'php': 0,
                'c++': 0,
                'css': 0,
                'c#': 0,
                'go': 0,
                'c': 0,
                'typescript': 0,
                'shell': 0,
                'swift': 0,
                'scala': 0,
                'objective-c': 0,
                'r': 0,
                'others': 0
            }

            # all languages keys without 'others'
            languages_no_other = list(languages.keys())[:-1]

            # iterate through repos, analyse data and parse it. Populate auxiliary placeholders and after getting out of the loop
            # append results to main placeholder
            # if user has no repos, we will get an empty list, skipping the following loop and assigning 0's to all key elements.
           
            for repo in user_repos:
                for key in summary:
                    # parse values, languages will have to have their own column, so we will add all appeareances of a single 
                    # language over the whole set of repositories for a single user, then, pass this sum to the final dictionary.
                    # Some users have changed their username while we were running this step, meaning that when calling for them github
                    # returns an error message in the form of a dictionary, we will skip these users.
                    try:
                        value = repo[key] # fails if key does not exist in repo dict
                    except TypeError:
                        print("KeyError")
                        break
                    # print(value)
                    if key == 'language':
                        
                        if value is None:
                            value = "null"
                        value = value.lower()
                        
                        # if the value is in languages
                        if value in languages_no_other:
                            # iterate over every language ("others" is not included)
                            for language in languages_no_other:
                                if value == language:
                                    languages[language] += 1
                                    # once the language variable is incremented get out of loop
                                    break
                        else:
                            languages['others'] += 1                        
                    # if key is not language, parse values as following
                    else:
                        if type(value) is bool:
                            value = int(value)
                        elif type(value) is str or type(value) is dict:
                            value = 1
                        elif type(value) is type(None):
                            value = 0
                        
                        # once the value is parsed, append it to our auxiliary placeholder dictionary
                        summary[key].append(value)

            # After finishing collecting info from all the user's repos we pass it to our main placeholder dictionary
            
            # set instance user
            repos['login'].append(user)
            
            # set all the instance languages
            for language in languages:
                repos[language].append(languages[language])
            
            # set all the instance values from summary object
            for key in summary_keys_no_lg:
                repos[key].append(sum(summary[key]))
            
        pd.DataFrame(repos).to_csv(path_write, index=False)


    def read_and_merge(path_write):
        # create a placeholder dataframe to append all data
        all_data = pd.DataFrame()
        # load first level files
        file_count = len(os.listdir('first_level/'))-1 # does not count the original first level file
        print("Merging starts...")
        for count in range(file_count):
            f_lvl = pd.read_csv('first_level/first_level_'+ str(count).zfill(2) +'.csv', index_col=1)
            f_lvl = f_lvl.drop(columns=['Unnamed: 0']) # we previously saved our dataframe with indexes, we don't care about them
            # load second level files
            s_lvl = pd.read_csv('second_level/users_second_level_'+ str(count).zfill(2) +'.csv', index_col = 1)
            s_lvl = s_lvl.drop(columns=['Unnamed: 0']) # we previously saved our dataframe with indexes, we don't care about them
            # merge first and second level
            # avoid duplicated columns
            cols_to_use = s_lvl.columns.difference(f_lvl.columns)
            # use index from both df's as reference for merging
            merge_lvl_1_2 = f_lvl.merge(s_lvl[cols_to_use], left_index=True ,right_index=True)
            # # load third level files
            t_lvl = pd.read_csv('third_level/users_third_level_'+ str(count).zfill(2) +'.csv', index_col = 0)
            # # merge last merged files with third level files
            cols_to_use = t_lvl.columns.difference(merge_lvl_1_2)
            f_merge = merge_lvl_1_2.merge(t_lvl[cols_to_use], left_index=True, right_index=True)
            # print("Final merge shape: ", f_merge.shape)
            all_data = all_data.append(f_merge, ignore_index=False)

        if not os.path.isfile(path_write):
            all_data.to_csv(path_write)
        print(all_data.shape)
        print("Merging finished")
        return all_data

    def read_and_transform(data, path_write):
        # We will transform data as follows:
        """
        site_admin  = "Yes"/"No"
        blog        = "Yes"/"No"
        company     = "Yes"/"No"
        created_at  = DateTime
        hirable     = "Yes"/"No"
        location    = Just clean NA's
        updated_at  = DateTime
        """
        # inspect columns for NAs
        for column in data.columns:
            if data[column].isnull().values.any():
                print("There are nan values in {column}".format(column=column))
        
        columns_to_transform = ['site_admin','blog','company','hireable'] #Yes/No transformation

        # transform the columns to "Yes"/"No"
        for column in columns_to_transform:
            if  data[column].isnull().values.any():
                data[column] = data[data[column].notnull()]
            if type(data[column]) == bool:
                data[column] = data[column].apply(lambda x: "Yes" if x is True else "No")
            else:
                data[column] = data[column].apply(lambda x: "Yes" if x > 0 else "No")
        
        # Clean NAs in location
        data.location = data.location.fillna('Unkown')

        # Transform created_at and updated_at to dd/mm/yyyy hh:mm:ss
        date_columns = ['created_at', 'updated_at']

        for column in date_columns:
            data[column] = data[column].apply(iso8601.parse_date)

        print(data.head())
        
        #check if there are still nan values in df
        nan_values = 0
        for column in data.columns:
            if data[column].isnull().values.any():
                nan_values += 1, 
        print("Total nan values found: {nan_values}".format(nan_values=nan_values))

        if not os.path.isfile(path_write):
            data.to_csv(path_write)
        return data
    

    def run_analytics(path_read, path_write):
        # we will analyse each column
        data = pd.read_csv(path_read, index_col = 0)
        
        uniques = {}
        for column in data.columns:
            uniques[column] = len(data[column].unique())
        print(uniques)
        
        # lets analyse those values that are categorical, ie. those that have a low count of unique values:
        # type, site_admin, blog, company, hirable

        

        pass
    
    #instantiate our wrapper with credentials
    gh = GitHubAPI(username=CREDENTIALS[0][0], password=CREDENTIALS[0][1])


    if not os.path.isfile('./first_level/users_first_level.csv'):
        get_users_from_gh(gh, './first_level/users_first_level.csv')

    # split users_first_level.csv file into parts so that each credential can handle a full file for future callings
    # split_level_one('./first_level/users_first_level.csv')
    
    # Call each file and make the calls with a given credential
    # for i, credential in range(len(CREDENTIALS)):
    #     gh = GitHubAPI(username=CREDENTIALS[i][0], password=CREDENTIALS[i][1])
    #     get_users_info(gh, './first_level/first_level_' + str(i).zfill(2) + '.csv','./second_level/users_second_level_' + str(i).zfill(2) + '.csv')
    
    # Call each file and make the calls with a given credential
    # for i, credential in range(len(CREDENTIALS)):
    #     gh = GitHubAPI(username=CREDENTIALS[i][0], password=CREDENTIALS[i][1])
    #     get_repos_from_gh(gh, './first_level/first_level_'+ str(i).zfill(2) +'.csv', './third_level/users_third_level_' + str(i).zfill(2) + '.csv')

    
    # all_data = read_and_merge('all_levels/all_data.csv')

    # data_fixed = read_and_transform(all_data, 'all_levels/all_data_fixed.csv')

    run_analytics('all_levels/all_data_fixed.csv', 1)



    # i = 24
    # gh = GitHubAPI(username=CREDENTIALS[i][0], password=CREDENTIALS[i][1])
    # get_repos_from_gh(gh, './first_level/first_level_'+ str(6).zfill(2) +'.csv', './third_level/users_third_level_' + str(6).zfill(2) + '.csv')


    # for i in range(25):
    #     gh = GitHubAPI(username=CREDENTIALS[i][0], password=CREDENTIALS[i][1])
    #     gh.check_limit()
    #     print(i, gh.remaining)




    # gh = GitHubAPI(username=CREDENTIALS[0][0], password=CREDENTIALS[0][1])
    # reqs = 2
    # response = []
    # # response.append(gh.get_users_since(since=48000000))
    # # print(response[0])
    # # print(response[0][0])
    # # with open('data.json', 'w') as outfile:
    # #     json.dump(response[0], outfile)
    
    # fin = open("data.json","r")
    # s = fin.read()
    # fin.close()
    # data = json.loads(s)
    # print(data[1]['login'])
    # print(data[1]['id'])
    # print(data[1]['type'])
    # print(data[1]['site_admin'])









# with open('data.json', 'w') as outfile:
#    json.dump(data, outfile)

# fin = open("data.json","r")
# s = fin.read()
# fin.close()
# data = json.loads(s)
# # print(data)

# print(data[1])


# test cases for jsonStringA and jsonStringB according to your data input


# string dump of the merged dict
# jsonString_merged = json.dumps(merged_dict)