from pathlib import Path
import os
from hermes.models.deps import Settings
import frontmatter
import pandas as pd

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)

deps = Settings()
VAULT = Path(deps.OBSIDIAN_VAULT_PATH)


class ObsidianEmbeddings():
    def __init__(self):
        #lazy: only load the HF model on first embedding call so importing this module is cheap
        self._model = None

    #@property turns a method into an attribute
    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            #this model caches once , after that embedding is very quick
            self._model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B")
        return self._model

    @log
    def embedding(self, descriptions:list | str):
        #batch embeddings
        embeddings = self.model.encode(descriptions)
        return embeddings

    #TODO , may need this: ollama pull mxbai-embed-large
    @log
    def embed_descriptions(self):

        #rglob search in the vault directory
        md_files = list(VAULT.rglob("*.md"))
        #gather a list of files
        md_files = [str(file) for file in md_files]
        storage = {
                "file": [], 
                "description": [],
                "embedding": []}
        
        #this is key, frontmatter has to be set up with a description for each file
        for file in md_files:
            try:
                post = frontmatter.load(file)
                description = post.metadata.get("description")
                if description:
                    storage['file'].append(file)
                    storage['description'].append(description)
            except Exception as e:
                print({e})

        #batch embeddings
        embeddings = self.embedding(storage['description'])  # returns numpy array (3, 1024)
        for i in embeddings:
            storage['embedding'].append(i.tolist())
        data = pd.DataFrame(storage)

        return data