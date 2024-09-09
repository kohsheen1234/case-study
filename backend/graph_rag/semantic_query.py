"""Module to perform similarity search in a graph database using embeddings."""

import json

from graph_rag.config import  GRAPH_ENTITIES, GRAPH_RELATIONSHIPS, EMBEDDING_MODELS, client, neo4j_graph


SEMANTIC_SEARCH_PROMPT = f'''
    You are a helpful agent designed to fetch information from a graph database. 
    
    The graph database links models, parts, symptoms, brands, product types, videos, installation instructions, stories, and Q&A to the following entity types:
    {json.dumps(GRAPH_ENTITIES, indent=4)}
    
    Each link has one of the following relationships:
    {json.dumps(GRAPH_RELATIONSHIPS, indent=4)}

    Depending on the user prompt, determine if it is possible to answer with the graph database.
        
    Sometimes the 'description' of the part contains the installation installation instructions, be sure to read fully,pickup anything relevant. The graph database can match models, parts, symptoms, and other entities with multiple relationships to several entities.
    
    Example user input:
    "Which parts are compatible with the FPHD2491KF0 model?"
    
    There are two relationships to analyze:
    1. The mention of the FPHD2491KF0 model means we will search for a model with that name or model number.
    2. The mention of parts means we will search for parts associated with that model.
    
    Return a JSON object following the following rules:
    For each relationship to analyze, add a key-value pair with the key being an exact match for one of the entity types provided, and the value being the value relevant to the user query.
    
    For the example provided, the expected output would be:
    {{
        "model": "FPHD2491KF0",
        "part": "all"  # Indicating we want to find all parts associated with the model
    }}

    Do not include any # comments in the JSON object.
    
    If there are no relevant entities in the user prompt, return an empty JSON object.
'''


def define_query(prompt: str, model: str = "gpt-4o"):
    """Function to generate a query based on the user input using OpenAI's API."""
    completion = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "system", "content": SEMANTIC_SEARCH_PROMPT}, {"role": "user", "content": prompt}],
    )
    print('define_query')
    print(completion.choices[0].message.content)
    return completion.choices[0].message.content


def create_embedding(text: str):
    """Function to create an embedding for a given text using OpenAI's API."""
    result = client.embeddings.create(model=EMBEDDING_MODELS["small"], input=text)
    return result.data[0].embedding


def similarity_search(prompt: str, threshold: float = 0.7):
    """Function to perform similarity search in a graph database using embeddings."""
    matches = []

    # Generate the entity type mapping from the user's prompt
    query_data = define_query(prompt)

    try:
        query_data = json.loads(query_data)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        query_data = {}

    if not query_data:
        print("No relevant entities found in the user prompt.")
        return []

    entity_mapping = {
        "part": "Part",
        "model": "Model",
        "symptom": "Symptom",
        "brand": "Brand",
        "review": "Review",
        "manufacturer": "Manufacturer",
    }

    for entity_type, entity_value in query_data.items():
        if entity_value.lower() == "all":
            entity_label = entity_mapping.get(entity_type.lower(), "Part")

            # Query to match all nodes of the specified type
            query = f'''
                MATCH (e:{entity_label})
                RETURN e
                LIMIT 3
            '''
            while True:
                try:
                    result = neo4j_graph.query(query)
                    break
                except Exception as e:
                    print(f"An error occurred with the Neo4j graph query: {e}")

        else:
            embedding = create_embedding(entity_value)
            entity_label = entity_mapping.get(entity_type.lower(), "Part")

            # Similarity search query using cosine similarity
            query = f'''
            WITH $embedding AS inputEmbedding
            MATCH (e:{entity_label})
            WHERE size(inputEmbedding) = size(e.embedding)
            WITH e, 
                 reduce(s = 0, i IN range(0, size(e.embedding)-1) | s + inputEmbedding[i] * e.embedding[i]) AS dot_product,
                 reduce(s = 0, i IN range(0, size(e.embedding)-1) | s + inputEmbedding[i] * inputEmbedding[i]) AS input_norm,
                 reduce(s = 0, i IN range(0, size(e.embedding)-1) | s + e.embedding[i] * e.embedding[i]) AS embedding_norm
            WITH e, dot_product / (sqrt(input_norm) * sqrt(embedding_norm)) AS cosine_similarity
            WHERE cosine_similarity > $threshold
            RETURN e
            LIMIT 3
            '''

            while True:
                try:
                    result = neo4j_graph.query(query, params={'embedding': embedding, 'threshold': threshold})
                    break
                except Exception as e:
                    print(f"An error occurred with the Neo4j graph query: {e}")

        # Process results
        for r in result:
            for _, value in r.items():
                entity_data = value
                if not entity_data:
                    continue
                if not isinstance(entity_data, dict):
                    entity_data = json.loads(entity_data)

                match_data = {"type": entity_label}
                attributes = [
                    "id", "name", "description", "url", "price", "status", "difficulty",
                    "repair_time", "works_with_products", "web_id", "model_num",
                    "partselect_num", "manufacturer_part_num", "content", "tools",
                    "question", "answer", "date"
                ]

                for attr in attributes:
                    if attr in entity_data:
                        match_data[attr] = entity_data[attr]

                matches.append(match_data)

    return matches


if __name__ == "__main__":
    USER_QUERY = "Which parts are compatible with the FPHD2491KF0 model?"
    print(similarity_search("Which parts are compatible with the FPHD2491KF0 model?", threshold=0.9))
