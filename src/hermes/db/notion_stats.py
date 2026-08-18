#--Placeholder for notion API calls--#
#--WIP--#


import requests
import os
from dotenv import load_dotenv

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

load_dotenv()
import pandas as pd

class NotionApiCalls():
    def __init__(self):
        self.database_id:str = os.getenv("NOTION_DATABASE_ID")
        self.token:str = os.getenv("NOTION_API_KEY")

    @log
    def get_datasource_id(self):
        #switch to query endpoing
        endpoint = f"https://api.notion.com/v1/databases/{self.database_id}"

        headers = {"Authorization": f"Bearer {self.token}",
                    "Notion-Version": '2026-03-11'}
        #params

        try:
            result = requests.get(
                url = endpoint,
                headers=headers
                                )
        except Exception as e:
            print("error reaching notion API")

        if result.status_code != 200:
            print(f"Failed to reach API, {result.status_code}")

        #TODO
        #.get to get datasource id from result
        result = result.json()
        datasource_id = result.get('data_sources')[0].get('id')

        return datasource_id


    @log
    def get_database_tasks(self):
        #data source id = 365bbf8b-ff1a-8185-904d-000b9c826427
        datasource_id = self.get_datasource_id()

        #tasks end point
        endpoint = f"https://api.notion.com/v1/data_sources/{datasource_id}/query"

        headers = {"Authorization": f"Bearer {self.token}",
                    "Notion-Version": '2026-03-11'}
        result = requests.post(
            url = endpoint,
            headers=headers,
            json={"page_size": 100},
                            )
        result = result.json()
        result = result.get('results', [])
        result = pd.json_normalize(result)
        result = result.rename(columns = 
                            {"properties.Task name.title": "Task Details",
                            "properties.Description.rich_text": "Task Description",
                            "properties.Status.status.name": "Task Status",
                            "properties.Assignee.people": "Assignee",
                            "properties.Task type.select.name": "Task Type",
                            "properties.Due date.date": "Due Date",
                            "properties.Effort level.select.name": "Effort Level",
                            "properties.Priority.select.name": "Priority"}, errors = "ignore") 
        #subset
        #TODO , pull out nested dictionaries from these columns.
        #reindex (not subset) so a task missing a property like Due Date becomes NaN instead of KeyError
        result = result.reindex(columns=['id', 'created_time', 'last_edited_time','Task Details',
                        'Task Description', 'Task Status',
                        'Assignee','Task Type','Due Date', 'Effort Level', 'Priority'])
        return result
    
    #take this one step further
    @log
    def get_task_content():
        '''
        Take a list of page ids from the previously api call , pass them through here in bulk to get the contents
        '''
        #GET  /v1/blocks/:page_id/children → body content for each task

        pass