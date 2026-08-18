# Obsidian as a harness plan

The plan is to build an cosine similarity against a user prompt and the frontmatter description in my obsidian.md files.

* This is not a full rag , this is only embedding the descriptions, and reading the full file for the best match. This is a skill implemntation.



1. Embed the descriptions
    - How do we embed the descriptions
    - If i have 100's of files , it is expensive and time consuming to run an embedding on every single decription for each run.
    - Do we have to use a frontier models embedding api ? (cost)

### Solutions:

We can embed with something like the following or some time of free hugging face embedder.

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")  # fast, small, good quality
```

!!!!Better idea, lets use an ollama embedding model since we are already hooked in.

```python
ollama pull mxbai-embed-large
```

```python
import ollama

response = ollama.embeddings(
    model="mxbai-embed-large",
    prompt="create a word doc from this data"
)
embedding = response["embedding"]  # 1024-dim v
```

This can run as part of our daily DTL pipeline, reading what has changed from obsidian.md , embedding it , and storing it in duckdb.
    - we dont need this to run all the time, descriptions shouldnt change that much.
    - from that point, we compare the embedded prompt against the saved embeddings. Way faster.

* How do we check what has changed ?

File change time for the vault can be used and stored alongside the embedding , to tell if the file changed since the last embedding.
```python
# cheaper than hashing the full content
last_modified = os.path.getmtime(filepath)
```


Storage will look something like this
```sql
CREATE TABLE skill_embeddings (
    skill_path VARCHAR PRIMARY KEY,  -- e.g. /mnt/skills/public/docx/SKILL.md
    description TEXT,
    description_hash VARCHAR,
    embedding FLOAT[384],
    updated_at TIMESTAMP
);
```

Once everything is embedded , we will query the db to pull embeddings in our function , calculate the cosine similarity , maybe implement some other algorthims, and then pass the agent the top 3. 

From there it can decide which to read.

This will be the only tool we use for obsidian , in the future we may extend to RAG.