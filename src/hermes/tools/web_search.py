from bs4 import BeautifulSoup
import httpx
from ddgs import DDGS
from profanity_check import predict, predict_prob
from rich.console import Console
import questionary
from hermes.logs.logging_helper import log

import logging
logger = logging.getLogger(__name__)

console = Console()
from rich.panel import Panel
class WebSearch():
    def __init__(self):
        self._classifer = None

    #TODO , host this model

    #property turns a method into an attribute
    #keeps it from loading on start up
    #the property, attribute only firest on get.. self.classifier (runs prompt_injection_check)
    #self.classifier starts as None, when called it executed the method attribute below
    #self.classifier accesses the attibute, self._classifier sets it. _get , _set
    @property
    def classifier(self):
        '''
        Would be cool to have a neural net for this as well

        Validate prompt injection on the reponse from Page Fetch

        #TODO , these may need to fall into their own guardrrails file
        '''
        if self._classifer == None:
            try:
                from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline, logging as transformers_logging
                import torch
                transformers_logging.set_verbosity_error()


                tokenizer = AutoTokenizer.from_pretrained("ProtectAI/deberta-v3-base-prompt-injection-v2")
                model = AutoModelForSequenceClassification.from_pretrained("ProtectAI/deberta-v3-base-prompt-injection-v2")

                self._classifier = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                truncation=True,
                max_length=512,
                device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
                )
                return self._classifier
            except Exception as e:
                print("Failed to create PII Pipeline {e}")

    @log
    def profanity_check(self,
                        query:str = None,
                        response:str = None):
        '''
        #TODO , may need to lazy load this if it is an API call to a model
        Validate query or response does not contain profanity
        '''
        
        if query:
            prediction = predict_prob([query])
            if prediction > 0.5:
                return "Failed profanity check"

        if response:
            prediction = predict_prob([response])
            if prediction > 0.5:
                return "Failed profanity check"
        
        else:
            return None 
    
    @log
    def query_validation(self,
                         query:str):
        '''
        Validate query before passing it into search 
        '''

        #length check
        if len(query) > 50:
            return "Query too long"
        #profanity check
        else:
            return None 

    @log
    def ddgs_search(self,
                    query:str):
        '''
        DuckDuckGo Search

        Parameters:
            Query - populate with relevant question or topic based on the users request
        '''
        #can switch backend to brave, google, bing
        pc = self.profanity_check(query = query)
        qv = self.query_validation(query = query)
        if pc:
            return "Failed profanity check"
        
        if qv:
            return "Failed query validation check"

        else:
            console.print(Panel(
            f"[dim]{' '.join(query)}[/dim]",
            title="[yellow]🔍 Pending ddgs search command[/yellow]",
            border_style="yellow"
                ))
            approval = questionary.select(
                        "Approve?",
                        choices=["Yes", "No"]
                    ).ask()
            if approval != "Yes":
                return "Cancelled"
            else:
                search = DDGS(timeout=20)
                results = search.text(
                    query=query,
                    max_results=5)
                return results

    @log
    def fetch_page(self,
                   url: str) -> str:
        """Fetch full page content when snippets aren't enough.
        
        Pass in href link from ddgs search
        """
        console.print(Panel(
        f"[dim]{' '.join(url)}[/dim]",
        title="[yellow]🔍 Pending fetch page command[/yellow]",
        border_style="yellow"
            ))
        
        approval = questionary.select(
                    "Approve?",
                    choices=["Yes", "No"]
                ).ask()
        if approval != "Yes":
            return "Cancelled"
        else:
            response = httpx.get(url, follow_redirects=True, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            # strip nav/footer/scripts
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()

            text = soup.get_text(separator="\n", strip=True) 

            pc = self.profanity_check(response= text)
            #this may be super expensive with a large page
            #should self limit to 512
            pic = self.classifier(text)

            if pc:
                return "Failed profanity check"
            if str(pic[0].get('label')).lower() != 'safe':
                if pic[0].get('score') > 0.5:
                    return "Failed prompt injection check"
            #limit to first 500 words ?
            else:
                return text 
