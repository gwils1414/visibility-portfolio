#--Placeholder to connect agent to obsidian for its brain--#
#--Should operate as an MCP , where it can read the .mds as skills--#
# !!Just for my memory, the reason I inject skills this way is it is determininstic
# Using only a manifest in the system prompt puts too much reliance on the agent to pick the right skill.
# and in the case of the brain, there will be hundreds of files, which is too expensive to store in a sys prompt
from pathlib import Path
from hermes.models.deps import Settings
from hermes.db.connections import get_read_connection
from hermes.db.obsidian_embeddings import ObsidianEmbeddings
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

import logging
from hermes.logs.logging_helper import log
logger = logging.getLogger(__name__)


#-init-#
deps = Settings()
obsidian = ObsidianEmbeddings()
VAULT = Path(deps.OBSIDIAN_VAULT_PATH)

#WIP

class ObsidianTool():
    def __init__(self, prompt):
        self.prompt = prompt
        self.data = None
        self._rerank_model = None


    @property
    def rerank_model(self):
        if self._rerank_model == None:
            from sentence_transformers import CrossEncoder
            self._rerank_model = CrossEncoder("Qwen/Qwen3-Reranker-0.6B")
            return self._rerank_model


    @log
    def embed_user_prompt(self):
        '''
        Uses hugging face embedding model to embed user prompt.

        Imported from hermes.db.obsidian_embeddings
        '''
        try:
            user_embedding = obsidian.embedding(self.prompt)
        except Exception as e:
            print(f"Failed to embded user prompt: {e}")

        #may need to convert to list , maybe can keep as an array
        return user_embedding #.tolist()

    @log
    def get_embeddings_from_db(self):
        '''
        Find similarity between user prompt and md descriptions
        '''
        try:
            conn = get_read_connection()
            descriptions = pd.read_sql(
                sql = 'SELECT * FROM obsidian_embeddings.obsidian_embeddings',
                con = conn
            )
        except Exception as e:
            print(f"Failed to retrieve embeddings from db: {e}")

        return descriptions

    @log
    def similarity_scores(self):
        '''
        Calculate similarity score between user prompt and file descriptions

        Currently only returns the top score

        Using cosine similarity, but we can make this more sophisticated.

        BM25 , rerank and so on

        TODO , expand this to top_k files
        '''
        try:
            user_prompt = self.embed_user_prompt()
        except Exception as e:
            print(f"Failed to embed user prompt: {e}")
        self.data = self.get_embeddings_from_db()

        scores = {}

        #if we change this to use pgvector, i think a lot of this becomes un-needed
        #pulls only the embedding and index from the dataset
        for ix, i in enumerate(self.data['embedding']):
            prompt = user_prompt.reshape(1, -1)
            #postgres jsonb is auto-deserialized by psycopg, so `i` is already a list (no json.loads needed)
            description = np.array(i)         # (n_docs, 1024)
            description = description.reshape(1,-1)
            score = cosine_similarity(prompt, description)[0][0]       # (n_docs,)
            scores[ix] = score

        #max_score_index = max(scores, key=scores.get)

        #top 5 indexs by score
        #first pass, filter to top 3 in the reranker
        top_5 = sorted(scores, key=scores.get, reverse=True)[0:5]

        #gate, score should be atleast 0.4 or above to consider.
        #we dont want to return max everytime
        filtered_top_5 = [index for index in top_5 if scores.get(index) > 0.4]
        return filtered_top_5

    @log  
    def reranker(self):
        '''
        TODO, incorporate into retrieval

        TODO
        Best path forward, pass top_5 from cosine simlarity.
        Pass those top 5 and user prompt through the reranker
        '''
        indexes = self.similarity_scores()
        if not indexes:
            return []
        
        #descriptions from the data
        descriptions = self.data['description'].iloc[indexes].tolist()

        #file names from the data
        files = self.data['file'].iloc[indexes].tolist()

        #pairs to rank
        pairs = [(self.prompt, description) for description in descriptions]
        
        #scores generated from the pairs
        scores = self.rerank_model.predict(pairs)

        #files, descriptions, scores as a tuple
        scored = list(zip(files, descriptions, scores))
        
        #top 3 scores
        top_3 = sorted(scored, key=lambda x: x[2], reverse=True)[:3]

        #file names from the top3
        files = [file for file, description, score in top_3]
        return files

    
    #on local model this may be expensive
    #need to keep obsidian notes clear , concise and normalized with a lot of links
    @log
    def read_files(self):
        '''
        Load text from file directly into agent context
        '''

        files = self.reranker()

        skills = {}
        if files:
            for file in files:
                #text = Path(file).read_text()
                skills[file] = Path(file).read_text()
            return skills
        else:
            return 'No relevant files'
