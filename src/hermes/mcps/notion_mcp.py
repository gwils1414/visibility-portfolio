from fastmcp import FastMCP
from notion_client import Client as NotionClient
from notion_client.api_endpoints import DataSourcesEndpoint as data_sources, PagesEndpoint, PagesPropertiesEndpoint
import os
from hermes.models.deps import Settings
from typing import Literal
import pandas as pd
import json
from rich.console import Console

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

deps = Settings()
console = Console()

#TODO FileUploadsEndpoint

#TODO , look into incorporating this into the notion pipelin: this is a lot cleaner than the raw api calls
#Need to make all of this dynamic
notion = NotionClient(auth=deps.NOTION_API_KEY, notion_version="2026-03-11")
sources = data_sources(parent=notion)
pages = PagesEndpoint(parent=notion) 

#TODO , this will become a class
class NotionMCP():
    def __init__(self):
        #may have to replace with 365bbf8b-ff1a-8185-904d-000b9c826427
        self.data_source_id = deps.NOTION_DATASOURCE_ID
        self.mcp = FastMCP("notion")       # must be before _register_tools
        self._register_tools()

    #TODO , inject these dynamically into instructions
    #include them in the typing of the below functions
    @log
    def _get_property_options(self, *prop_types: str) -> dict[str, list[str]]:
        '''
        Retrieve the data source schema and return {property_name: [option names]}
        for every status/select/multi_select property. Pass one or more types
        (e.g. 'status', 'select') to restrict to those property kinds.
        '''
        ds = sources.retrieve(data_source_id=self.data_source_id)
        wanted = prop_types or ('status', 'select', 'multi_select')
        options: dict[str, list[str]] = {}
        for name, prop in ds['properties'].items():
            ptype = prop.get('type')
            if ptype in wanted:
                options[name] = [o['name'] for o in prop[ptype].get('options', [])]
        return options

    @log
    def get_status_options(self) -> list[str]:
        '''
        Return statuses available for the database
        '''
        return self._get_property_options('status').get('Status', [])

    @log
    def get_priority_options(self) -> list[str]:
        '''
        Return priority levels available for the database
        '''
        return self._get_property_options('select').get('Priority', [])

    @log
    def get_options(self) -> dict[str, list[str]]:
        '''
        Pull all available select/status options for the datasource.
        Pass them into the functions below
        '''
        return self._get_property_options()

    def get_pages(self)->json:
        '''
        Get all pages/tasks and id's from a database to pass into update tasks
        '''
        result = sources.query(data_source_id = self.data_source_id)
        #result = result.json()
        result = result.get('results')
        result = pd.json_normalize(result)
        result = result.rename(columns = 
                            {"properties.Task name.title": "Task Details",
                            "properties.Description.rich_text": "Task Description",
                            "properties.Status.status.name": "Task Status",
                            "properties.Assignee.people": "Assignee",
                            "properties.Task type.select.name": "Task Type",
                            "properties.Due date.date": "Due Date",
                            "properties.Effort level.select.name": "Effort Level",
                            "properties.Priority.select.name": "Priority"}) 
        #subset
        #TODO , pull out nested dictionaries from these columns.
        result = result[['id', 'created_time', 'last_edited_time','Task Details',
                        'Task Description', 'Task Status',
                        'Assignee','Task Type','Due Date', 'Effort Level', 'Priority']]                
        result = result.to_json()
        return result


    #create a function for all literals here that load available values from datasource
    def create_task(self,
                    task_title:str, 
                    description:str | None = None,
                    content:str | None = None,
                    status:Literal['Backlog','In progress','On hold', 'Not started', 'Done', 'Cancelled', 'Blocked', 'Waiting on others'] | None = None,#need to get all available statuses
                    due_date:str | None = None,
                    task_type:Literal['Admin', 'Internal ops', 'Client Work', 'Finance', 'Other'] | None = None,
                    priority:Literal['P0 Critical', 'P1 High', 'P2 Medium', 'P3 Low', 'P4 Someday'] | None = None,
                    effort_level:Literal['S (1-4h)'] | None = None) -> str:
        '''
        Create Task

        Parameters:
        - task_title: task title
            title of the task
        - description (optional): description of task
            String description of task
        - content body of the task
            - this is where we add additional supporting context on the task
            - this is the main body of the task.
        - status (optional): current status
            One of the following: ['Backlog','In progress','On hold', 'Not started', 'Done', 'Cancelled', 'Blocked', 'Waiting on others'] or null
        - due_date (optional): task due date - due_date needs to be an ISO 8601 string (YYYY-MM-DD).
        - task_type (optional): type of task . Internal ops, Admin, Client work.
            - default to 'Other' if unsure
        - priority (optional): priority level of task
            One of the following: ['P0 Critical', 'P1 High', 'P2 Medium', 'P3 Low', 'P4 Someday'] or null
        - effort_level (optional): estimate of how much work it will be
            One of the following: ['S (1-4h)']

        Always prompt the user for parameters!
         - If the user does not provide the given parameters, do not pass them in.

        Partial Example:
            {"task_title": "Fix issue xyz",
            "description": "Fixing a bug that was found"}

        Full Example:
        create_task(
        task_title="Fix login bug",
        content= "this bug is about x y and z, it relates to b."
        description="Users are unable to login with Google SSO",
        status="In progress",
        due_date="2026-05-25",
        priority="P1 High",
        task_type="Internal Ops",
        effort_level="S (1-4h)"
        )

        '''
        #Dont even need this piece , can just pass in the datasource_id since we know it
        #data_source = sources.query(data_source_id='365bbf8b-ff1a-8185-904d-000b9c826427')
        #results = data_source.get('results')[0]
        console.print("[bold yellow]Running create_task()[/bold yellow]")
        properties = {}

        if task_title is not None:
            properties["Task name"] = {"title": [{"text": {"content": task_title}}]}
        if description is not None:
            properties["Description"] = {"rich_text": [{"text": {"content": description}}]}
        if status is not None:
            properties["Status"] = {"status": {"name": status}}
        if due_date is not None:
            properties["Due date"] = {"date": {"start": due_date}}
        if priority is not None:
            properties["Priority"] = {"select": {"name": priority}}
        if task_type is not None:
            properties["Task type"] = {"select": {"name": task_type}}
        if effort_level is not None:
            properties["Effort level"] = {"select": {"name": effort_level}}
        
        # Notion expects `content` as an array of block objects, not a string.
        # Notion caps each rich_text `content` at 2000 chars, so chunk long content.
        content_blocks = None
        if content is not None:
            chunks = [content[i:i + 2000] for i in range(0, len(content), 2000)] or [""]
            content_blocks = [{
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [
                    {"type": "text", "text": {"content": chunk}} for chunk in chunks
                ]},
            }]

        try:
            pages.create(
                parent={"data_source_id": self.data_source_id},  # required
                properties=properties,
                **({"children": content_blocks} if content_blocks else {})
            )
        except Exception as e:
            print(f"Error creating task: {e}")
        # ...
        return 'page created'

    def update_task(
        self,
        page_id: str,
        task_title: str | None = None,
        description: str | None = None,
        status: Literal['Backlog', 'In progress', 'On hold', 'Not started', 'Done', 'Cancelled', 'Blocked', 'Waiting on others'] | None = None,
        due_date: str | None = None,
        priority: Literal['P0 Critical', 'P1 High', 'P2 Medium', 'P3 Low', 'P4 Someday'] | None = None,
        effort_level: Literal['S (1-4h)'] | None = None,
        archived: bool = False #set to True to archive
    ) -> str:
        '''
        Update an existing task in Notion.
        Only pass the fields you want to update — all parameters except page_id are optional.

        Parameters:
        - page_id: the Notion page ID of the task to update
            - all pages can be found from get_pages()
        - task_title: new title
        - description: new description
        - status: new status
        - due_date: new due date (YYYY-MM-DD)
        - priority: new priority level
        - effort_level: new effort estimate
        '''
        console.print("[bold yellow]Running update_task()[/bold yellow]")
        properties = {}

        if task_title is not None:
            properties["Task name"] = {"title": [{"text": {"content": task_title}}]}
        if description is not None:
            properties["Description"] = {"rich_text": [{"text": {"content": description}}]}
        if status is not None:
            properties["Status"] = {"status": {"name": status}}
        if due_date is not None:
            properties["Due date"] = {"date": {"start": due_date}}
        if priority is not None:
            properties["Priority"] = {"select": {"name": priority}}
        if effort_level is not None:
            properties["Effort level"] = {"select": {"name": effort_level}}
        

        #TODO : make a new tool just for archived
        try:
            pages.update(
            page_id=page_id,
            properties=properties
        )
        except Exception as e:
            print(f"Failed to update task {e}")
        
        return 'task updates'
    
    #TODO , delete task tool
    def delete_task(self,
                    page_id:str,
                    in_trash: bool):
        '''
        use to delete task
        page_id: for task (required)
        in_trash: pass in True to delete the task
        '''
        try:
            pages.update(
            page_id=page_id,
            in_trash=in_trash
        )
        except Exception as e:
            print(f"Failed to update task {e}")

        return 'task archived'

    
    @log
    def _register_tools(self):
        self.mcp.add_tool(self.get_pages)
        self.mcp.add_tool(self.create_task)
        self.mcp.add_tool(self.update_task)
        self.mcp.add_tool(self.delete_task)


if __name__ == "__main__":
    server = NotionMCP()
    server.mcp.run()  # not server.run()
