import os
import resend as r
import base64
from datetime import datetime
from dotenv import load_dotenv

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


#profanity package, if agent has access to email it should not have the ability to send profanity.
#claude reccomendation instead of maintaining a list of profanity

#emails will only be internal so removing for now
#from better_profanity import profanity
#TODO , PII scraper


r.api_key = os.getenv("RESEND_API_KEY")
domain = os.getenv("RESEND_DOMAIN")



#TODO , may have this read the html from a databse and send
    
@log
def send_plain_email(body:str):
    '''
    Send a plain text email
    '''
    #if profanity.contains_profanity(body):
        #return "Can't send this email because of profanity."
    #else:
    email = r.Emails.send({
        "from": domain,
        "to": "gwilson@aretecp.com",
        "subject": "Hello World",
        "html": f"<p>{body}</p>"
    }
    )

@log
def send_email_with_html(body:str, file_path):
    '''
    sending emails with html files
    '''
    with open("report.html", "rb") as f:
        html_bytes = f.read() 

    #if profanity.contains_profanity(body):
        #return "Can't send this email because of profanity."
    #else:  
    email = r.Emails.send(
        {
        "from": domain,
        "to": "gwilson@aretecp.com",
        "subject": "Hello World",
        "html": f"<p>{body}</p>",
        "attachments": [
        {
            "filename": "report.html",
            "content": list(html_bytes),  # resend expects a list of bytes
        }]
        })


#TODO resend inbox ???