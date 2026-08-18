from hermes.db.connections import get_read_connection
import pandas as pd
import json

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


#TODO build out query for needed data
@log
def query_notion_tasks()-> json:
    '''
    This function is here to pull github related stats
    '''
    conn = get_read_connection()

    try:
        data = pd.read_sql(
            sql = """select nt.created_time, 
            nt.last_edited_time,
            nt.task_status,
            nt.task_type,
            nt.priority,
            tt.plain_text as "title",
            tt.text__content as "content",
            ttd.plain_text as "description",
            ttd.text__content as "description_details"
            from notion.notion_tasks nt  --dM2Uz26nQytK9Q
            left join notion.notion_tasks__task_details tt
            on nt._dlt_id  = tt._dlt_parent_id
            left join notion.notion_tasks__task_description ttd
            on nt._dlt_id = ttd._dlt_parent_id""",
            con = conn
        )
    except Exception as e:
        print(f"Failed to query github stats. {e}")

    #pass json
    data = data.to_json()
    return data