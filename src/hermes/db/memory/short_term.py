#placeholder to write agent correspondence to duckdb for memory
#seperate db for memory to help with parallel read/write requests on the same db?

from hermes.models.deps import Settings
import psycopg
import uuid
import json
from pydantic_ai.messages import ModelMessagesTypeAdapter

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


#TODO , create a purge option
deps = Settings()

class ShortTermMemory():
    def __init__(self):
        self.conn = psycopg.connect(deps.DB_URL, autocommit=True)

    @log
    def generate_session_id(self):
        #create uuid identifier once at CLI start
        session_id = uuid.uuid4()
        return session_id
    

    #create short term memory schema
    #this probably moves to the db directory
    #TODO , migrations
    @log
    def create_st_schema(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS short_term_memory (
                id SERIAL PRIMARY KEY,
                session_id uuid,
                user_prompt text,
                response text,
                tool_calls text[],
                messages text[],
                created_at  TIMESTAMP DEFAULT NOW()
                )
                """)
        except Exception as e:
            print(f"Failed to create table short_term_memory: {e}")
        
        #self.conn.close()
        return "Table created"


    @log
    def store_st_memory(self,
                        session_id:uuid,
                        user_prompt:str,
                        response:str,
                        tool_calls:list,
                        messages):
        #write results to st memory table
        try:
            #TODO, add usage, the agent can monitor its own usage and try to accomodate for limits
            cursor = self.conn.cursor()
            cursor.execute(
                f"""
                INSERT INTO short_term_memory (
                session_id, user_prompt, response, tool_calls, messages)
                VALUES (%s,%s,%s,%s,%s)""",
                (session_id,user_prompt, response, tool_calls, messages)
            )
        except Exception as e:
            print(f"Failed to insert records to short term memory: {e}")

        #self.conn.close()
        return "short term memory stored"

    @log
    def retrieve_st_memory(self,
                           session_id:uuid):
        #retrieve based on current session_id
        try:
            cursor = self.conn.cursor()
            history = cursor.execute(
                f"""
                SELECT user_prompt, response, tool_calls FROM short_term_memory st
                WHERE st.session_id = %s
                """,
                (session_id,)
            ).fetchall()

            #truncating result for context limits
                #there should be a better way to do this
                #probably reverse for the most recent info
                #if length is over 60,000 , the last 60,000
                #you still have to have a limit in reverse, so from end to -60000, 60000 is still your limit
            if history:
                total_length = sum([len(str(i)) for i in history])
                if total_length > 60000:
                    #returns the last 60,000 strs
                    history = str(history)[-60000:0]
                    return history
                else:
                    return history

            #may have to ModelTypeAdapter here to pass into message history
        except Exception as e:
            print(f"Failed to insert records to short term memory: {e}")
        
        #self.conn.close()
        return history
    
    @log
    def get_message_history(self,
                            session_id):
        '''
        extract ONLY messages from history to load into agent
        '''
        cursor = self.conn.cursor()

        #need to figure out a way to subset this to my own columns , instead of pydantic modeltypeadapter
        #I could select prompt/response/tools calls and append them as a list
        try:
            result = cursor.execute("""
            SELECT messages FROM short_term_memory 
            WHERE session_id = %s
            """,
            (session_id,))
            result = cursor.fetchall()
            if result:
                #TODO , would need to be iterated through of using multiple rows and pushing into pydantic ai
                result = ModelMessagesTypeAdapter.validate_json(result[0][0]) #Model message type adapter must be used when passing message history back to a pydantic agent
                return result
            else:
                return []
        except Exception as e:
            print(f"Error retrieving message history {e}")
            return []



#!!! We want to accumulate these short term memory on the posgres table
# about once a week, we can have an llm judge analyze them, and determine what becomes a long term memory
# and write that to the long term memory file
# lets keep this in obsidian
# long term memory is things like user preferences, name, styles

