import requests
import os
from dotenv import load_dotenv
from hermes.models.deps import Settings
import json
import pandas as pd
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


deps = Settings()



class GithubError(Exception):
    pass

class GithubStatistics():
    '''
    This class exists to retrieve github statistics in a way that is useful for the beginning of day summary.

    Functions:
        - get_repos
        - get_commits
        - get_issues
        - get_pull requests

    Parameters:
        - token
        - org
        - login (user names)
        - yesterday (we only want to load yesterdays statistics one a morning for yesterdays brief)
    '''
    def __init__(self):
        self.token:str = deps.GITHUB_PAT_TOKEN
        self.org:str = 'aretecp'
        self.owner:str = 'aretecp'
        self.login:list = ['gwils1414', 'GarettWilson']
        #TODO : Implement this date logic
        self.yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date() #we want todays date to filter for just yesterdays commits if any
        self.params ={
        "per_page": 100,
        }

    @log
    def get_repos(self):
        '''
        Get all Org Repos
        '''

        #repos endpoint
        endpoint = f'https://api.github.com/orgs/{self.org}/repos'

        #pass in PAT
        headers = {
        "Authorization": f"Bearer {self.token}"}

        #pull all repos for og
        try:
            result = requests.get(
                url = endpoint,
                headers = headers,
                params = self.params
            )
            #raise creates the error.
            if result.status_code != 200:
                raise GithubError(result.status_code, result.json().get("message"))
        #except handles the raised error.
        #Without except, raise would crash your entire program. Without raise, except would never trigger for your custom error.
        except GithubError as e:
            print(f'{e}, error calling repos')
            return None

        #return as a json
        result = result.json()

        return result

    @log
    def get_repo_names(self):
        '''
        Distinct list of repo names
        '''
        #get repos
        stats = self.get_repos()

        #extract names
        repo_names = [i.get('name') for i in stats]

        return repo_names


    @log
    def get_commits(self, repo):
        '''
        Get commit sha by user

        Make repo into a list so we can do it for a number of repos

        Will need to make this one call instead of many for each repo

        Only filtering for yesterday

        #TODO: Should this be expanded to include semantic bot / take in a list of repos (threadpooling)
            - Can this return just import information , we really dont need a lot of it to be persistent.
            - We want to use the minimum amount of tokens, data is expensive.
            - This may need to expand to the whole team , so I can get a summary of what they did yesterday as well.
        '''

        #commits endpoints
        endpoint =  f'https://api.github.com/repos/{self.owner}/{repo}/commits'

        #PAT token
        headers = {
        "Authorization": f"Bearer {self.token}"}

        #retrieve all commits
        try:
            result = requests.get(
                url = endpoint,
                headers = headers,
                params = self.params
            )
            if result.status_code != 200:
                raise GithubError(result.status_code, result.json().get("message"))
        except GithubError as e:
            print(f'{e}, error calling repos')
            return None
        
        #return results
        result = result.json()

        #filter for user and yesterdays commits
        filtered = [commit for commit in result 
            if commit.get('author') 
            and commit['author']['login'] in self.login]
                        #and datetime.strptime(commit['commit']['author']['date'], "%Y-%m-%dT%H:%M:%SZ").date() == self.yesterday]

        #if there were any commits yeterday
        if filtered:
            result = pd.json_normalize(filtered) #using this to unest columns
            result = result[['sha', 'commit.author.name', 'commit.author.email', 'commit.author.date', 'commit.message', 'commit.comment_count', 'author.repos_url']] #subset

            #add a repo column from the input
            result['repo'] = repo
            return result #shas
        else:
            return 'No commits yesterday'
        

    @log
    def get_commits_bulk(self):
        '''
        Threadpooling for multiple repos.
        '''

        #all repo names
        repo_list = self.get_repo_names()

        #results store
        results = []

        #threadpool with 5 workes
        with ThreadPoolExecutor(max_workers=5) as executor:
            #tickets to be executed
            #executres get_commits for each repo and stores as futures
            futures = [executor.submit(self.get_commits, repo)
                for repo in repo_list
            ]
            #This is the async/simulataneous runs
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        results.append(result)
                except Exception as e:
                    print(f'Error fetching commit detail: {e}')

        # step 3 - flatten and return
        results = pd.concat(results, ignore_index=True)

        return results
    

    @log
    def get_commit_details(self, repo, sha):
        '''
        This function is set up to return file changes / line counts and so on to get details of commits

        Parameters:
            - repo
            - sha (single sha)
        Threadpooling based on SHA in get_commits_details_bulk for a list of Shas
        '''

        endpoint = f'https://api.github.com/repos/{self.owner}/{repo}/commits/{sha}'

        headers = {
        "Authorization": f"Bearer {self.token}"}
        try:
            result = requests.get(
                url = endpoint,
                headers = headers
            )
            if result.status_code != 200:
                raise GithubError(result.status_code, result.json().get("message"))
        except GithubError as e:
            print(f'{e}, error calling repos')
            return None
        

        result = result.json()
        result = pd.json_normalize(result)

        #subset
        result = result[['sha','files','commit.author.name','commit.author.date','commit.committer.date','commit.message','stats.additions','stats.deletions']]
        #TODO , filter for yesterday here:
        #Maybe if filtering for yesterday every where here, we merge instead of replace in dlt , and let the agent query for inserted at
        result['repo'] = repo
        return result
        
    @log
    def get_commits_details_bulk(self):

        '''
        Threadpooling the get commit details
        '''
        data = self.get_commits_bulk()
        if isinstance(data, str):  # handles 'No commits yesterday'
            return data
        
        results = []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self.get_commit_details, row['repo'], row['sha'])
                for _, row in data.iterrows()
            ]
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        results.append(result)
                except Exception as e:
                    print(f'Error fetching commit detail: {e}')

        # step 3 - flatten and return
        #TODO , need to work on this return
        # Too many uneccessary columns, go back and filter where they are coming from.
        results = pd.concat(results, ignore_index=True)
        results = results[['sha','files','commit.author.name','commit.author.date','commit.committer.date','commit.message','stats.additions','stats.deletions', 'repo']]


        return results


    @log
    def get_issues(self, repo):
        '''
        Get all issues assigned to me for single repo

        Rolls into bulk
        '''
        endpoint = f'https://api.github.com/repos/{self.owner}/{repo}/issues'
        headers = {
        "Authorization": f"Bearer {self.token}"}
        try:
            result = requests.get(
                url = endpoint,
                headers=headers,
                params=self.params
            )
            if result.status_code != 200:
                raise GithubError(result.status_code, result.json().get("message"))
        except GithubError as e:
            print(f'{e}, error calling issues')
            return None  

        #filter to assigned to me     
        result = result.json()
        result = pd.json_normalize(result)

        #API call may return empty results
        if result.empty:
            return None

        #TODO , labels are expensive, may have to drop.
        #subsetting and filtering based on if closed or not
        filtered = result[['number', 'title', 'state','assignees','comments','created_at','user.login', 'body','closed_at']]
        filtered = filtered[filtered['user.login'].isin(self.login) | filtered['assignees'].isin(self.login)]
        filtered['repo'] = repo

        #only want open issues for where to start
        filtered = filtered[filtered['closed_at'].isna()]
        return filtered
    
    @log
    def get_issues_bulk(self):
        '''
        Threadpool issues retrieval for all repos
        '''

        repo_list = self.get_repo_names()

        #results store
        results = []

        #threadpool with 5 workes
        with ThreadPoolExecutor(max_workers=5) as executor:
            #tickets to be executed
            #executres get_commits for each repo and stores as futures
            futures = [executor.submit(self.get_issues, repo)
                for repo in repo_list
            ]
            #This is the async/simulataneous runs
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if isinstance(result, pd.DataFrame) and not result.empty:
                        results.append(result)
                except Exception as e:
                    print(f'Error fetching commit detail: {e}')

        # step 3 - flatten and return
        results = pd.concat(results, ignore_index=True)

        return results


    @log
    def get_pull_requests():
        '''
        Probably wont use this.
        '''
        pass





