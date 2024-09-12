"""Module to perform similarity search in a graph database using embeddings."""

import json

from graph_rag.config import  GRAPH_ENTITIES, GRAPH_RELATIONSHIPS, EMBEDDING_MODELS, client, neo4j_graph


SEMANTIC_SEARCH_PROMPT = f'''

    You are a helpful agent designed to fetch information from a graph database. 

    These are distinct brands in this dataset: "Frigidaire","Kenmore","Crosley","Electrolux","Tappan","Kelvinator","Gibson","General Electric",
    "Whirlpool","Maytag","LG","Amana","Litton","Admiral","Magic Chef","Jenn-Air","Hoover","KitchenAid","Roper","Haier","Samsung","Bosch",
    "Thermador","Inglis","Uni","Hotpoint","Norge","Speed Queen","Caloric"

    
    The graph database links models, parts, symptoms, instructions, reviews, question ans answers to the following entity types:
    {json.dumps(GRAPH_ENTITIES, indent=4)}
    
    Each link has one of the following relationships:
    {json.dumps(GRAPH_RELATIONSHIPS, indent=4)}

    Depending on the user prompt, determine if it is possible to answer with the graph database.

    If there is an symptom you can use `HAS_SYMPTOM` relationship to find the model with the issue 
    Model - `HAS_SYMPTOM` -> Symptom, Part - `HAS_QUESTION` -> Question ,  Question - `HAS_ANSWER` -> Answer, Symptom - `FIXED_BY` -> Part, 
    Instruction - `USED_IN` -> Part
    Dont forget to refer to question and answers realted to any part/ instructions related to any model, you'll mostly find all answers there.
    
        
    Sometimes the 'description' of the part contains the installation installation instructions, be sure to read fully,pickup anything relevant. The graph database can match models, parts, symptoms, and other entities with multiple relationships to several entities.
    
    Example user input:
    "Which parts are compatible with the FPHD2491KF0 model?"
    
    There are two relationships to analyze:
    1. The mention of the FPHD2491KF0 model means we will search for a model with that name or model number.
    2. The mention of parts means we will search for parts associated with that model.

    when theres a confusion between 2 cases , dont choose 1 over the other, rather try for both 
    
    Return a JSON object following the following rules:
    For each relationship to analyze, add a key-value pair with the key being an exact match for one of the entity types provided, and the value being the value relevant to the user query.
   
    For the example provided, the expected output would be:
    {{
        "model": "FPHD2491KF0",
        "part": "all"  # Indicating we want to find all parts associated with the model
    }}

    There can be more than 2 relationships too. Example- "why ice maker is not working in my fridge?" {{question:"contains ice","answer":"contains ice","review":"contains ice","instruction":"contains ice"}}

     
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


def similarity_search(prompt: str, threshold: float = 0.7):  # pylint: disable=too-many-branches, too-many-statements
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

    for entity_type, entity_value in query_data.items():
        # Check if the value is "all"
        if entity_value.lower() == "all":
            # Match all nodes of the specified type
            entity_label = {
                "part": "Part",
                "model": "Model",
                "symptom": "Symptom",
                "manufacturer": "Manufacturer",
                "review": "Review",
                "repair_story": "RepairStory",
                "instruction": "Instruction",
                "question": "Question",
                "answer": "Answer",
            }.get(entity_type.lower(), "Part")  # Default to 'Part' if not recognized

            query = f'''
                MATCH (e:{entity_label})
                RETURN e
                LIMIT 10
            '''
            while True:
                try:  # Attempt to query the graph
                    result = neo4j_graph.query(query)
                    break
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(f"An error occurred with the Neo4j graph query: {e}")

        else:
            # Perform cosine similarity search
            embedding = create_embedding(entity_value)

            entity_label = {
                "part": "Part",
                "model": "Model",
                "symptom": "Symptom",
                "manufacturer": "Manufacturer",
                "review": "Review",
                "repair_story": "RepairStory",
                "instruction": "Instruction",
                "question": "Question",
                "answer": "Answer",
            }.get(entity_type.lower(), "Part")  # Default to 'Part' if not recognized

            query = f'''
            WITH $embedding AS inputEmbedding
            MATCH (e:{entity_label})
            WHERE size(inputEmbedding) = size(e.embedding)  // Ensure vectors are the same size
            WITH e, 
                 reduce(s = 0, i IN range(0, size(e.embedding)-1) | s + inputEmbedding[i] * e.embedding[i]) AS dot_product,
                 reduce(s = 0, i IN range(0, size(e.embedding)-1) | s + inputEmbedding[i] * inputEmbedding[i]) AS input_norm,
                 reduce(s = 0, i IN range(0, size(e.embedding)-1) | s + e.embedding[i] * e.embedding[i]) AS embedding_norm
            WITH e, dot_product / (sqrt(input_norm) * sqrt(embedding_norm)) AS cosine_similarity
            WHERE cosine_similarity > $threshold
            RETURN e
            LIMIT 10
            '''

            while True:
                try:  # Attempt to query the graph
                    result = neo4j_graph.query(query, params={'embedding': embedding, 'threshold': threshold})
                    break
                except Exception as e:  # pylint: disable=broad-exception-caught
                    print(f"An error occurred with the Neo4j graph query: {e}")

        # Process results
        for r in result:
            for _, value in r.items():
                entity_data = value
                if not entity_data:
                    continue
                if not isinstance(entity_data, dict):
                    entity_data = json.loads(entity_data)
                match = {"type": entity_label}
                # Process entity attributes relevant to your dataset
                if "partSelectNumber" in entity_data:
                    match["partSelectNumber"] = entity_data["partSelectNumber"]
                if "partName" in entity_data:
                    match["partName"] = entity_data["partName"]
                if "manufacturerPartNumber" in entity_data:
                    match["manufacturerPartNumber"] = entity_data["manufacturerPartNumber"]
                if "price" in entity_data:
                    match["price"] = entity_data["price"]
                if "rating" in entity_data:
                    match["rating"] = entity_data["rating"]
                if "reviewCount" in entity_data:
                    match["reviewCount"] = entity_data["reviewCount"]
                if "description" in entity_data:
                    match["description"] = entity_data["description"]
                if "id" in entity_data:
                    match["id"] = entity_data["id"]
                if "modelNum" in entity_data:
                    match["modelNum"] = entity_data["modelNum"]
                if "brand" in entity_data:
                    match["brand"] = entity_data["brand"]
                if "name" in entity_data:
                    match["name"] = entity_data["name"]
                if "url" in entity_data:
                    match["url"] = entity_data["url"]
                if "status" in entity_data:
                    match["status"] = entity_data["status"]
                if "difficulty" in entity_data:
                    match["difficulty"] = entity_data["difficulty"]
                if "repairTime" in entity_data:
                    match["repairTime"] = entity_data["repairTime"]
                if "helpfulness" in entity_data:
                    match["helpfulness"] = entity_data["helpfulness"]
                if "question" in entity_data:
                    match["question"] = entity_data["question"]
                if "answer" in entity_data:
                    match["answer"] = entity_data["answer"]
                if "date" in entity_data:
                    match["date"] = entity_data["date"]

                matches.append(match)

    return matches


if __name__ == "__main__":
    USER_QUERY = "Which parts are compatible with the FPHD2491KF0 model?"
    print(similarity_search("Which parts are compatible with the FPHD2491KF0 model?", threshold=0.9))
