import requests
import json
from credentials import USERNAME, PASSWORD


# response = requests.get('https://api.github.com/users?since=135&per_page=100', auth=(username, password))
# response = requests.get('https://api.github.com/users?since=135')

# data = json.loads(response.content)

"""
https://api.github.com/users/technicalpickles:

"type": "User",
"site_admin": false,
"company": null,
"blog": "http://sjjdev.com",
"location": "Oxford, UK",
"email": null,
"hireable": null,
"public_repos": 70,
"public_gists": 48,
"followers": 18,
"following": 3,
"created_at": "2008-02-03T21:35:34Z",
"updated_at": "2019-03-12T13:47:35Z"

languages:


javascript
python
java
ruby
php
c++
css
c#
go
c
typescript
shell
swift
scala
obj-c

from list of repos:
(create summary)

"stargazers_count": 1,
Repository Starring is a feature that lets users bookmark repositories. Stars are shown next to 
repositories to show an approximate level of interest. Stars have no effect on notifications or the activity feed. 
For that, see Repository Watching.

"watchers_count": 1,
Watching a Repository registers the user to receive notifications on new discussions, 
as well as events in the user's activity feed. See Repository Starring for simple repository bookmarks.


"has_issues": true,

"has_projects": true, relate this with succcess

"has_downloads": true,

"has_wiki": true,

"has_pages": false,

"forks_count": 1,

"open_issues_count": 0,

"license": null,

"forks": 1,

"open_issues": 0,

"watchers": 1,

"default_branch": "master"

"""
class GitHubAPI(object):

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.response = None
        self.limit = False
        self.set_endpoints()
        
    def get_users_since(self, since, per_page=100):
        self.response = self.request_get(self.endpoints[0].format(since=str(since), per_page=str(per_page)))
        return self.response.json()

    def get_user(self, user):
        self.response = self.request_get(self.endpoints[1].format(user=user))
        return self.response.json()

    def get_repos(self, user):
        self.response = self.request_get(self.endpoints[2].format(user=user))
        return self.response.json()
    
    def get_languages(self, user, repo):
        self.response = self.request_get(self.endpoints[3].format(user=user, repo=repo))
        return self.response.json()

    def check_limit(self):
        response =  requests.get(self.endpoints[4], auth=(self.username, self.password))
        response = response.json()
        
        if response['resources']['core']['remaining'] == 0:
            self.limit = True
        else:
            self.limit = False


    def request_get(self, endpoint):
        self.check_limit()

        if self.limit:
            return
        
        return requests.get(endpoint, auth=(self.username, self.password))
        
    def set_endpoints(self):
        self.endpoints = []
        self.endpoints.append('https://api.github.com/users?since={since}&per_page={per_page}')
        self.endpoints.append('https://api.github.com/users/{user}')
        self.endpoints.append('https://api.github.com/users/{user}/repos')
        self.endpoints.append('https://api.github.com/repos/{user}/{repo}/languages')
        self.endpoints.append('https://api.github.com/rate_limit')


gh = GitHubAPI(username=USERNAME, password=PASSWORD)
reqs = 2
data = []
for req in range(reqs):
    data.append(gh.get_users_since(10000000, 1))

print(data)





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