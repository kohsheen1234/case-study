"""Script to generate Cypher queries based on user input and query a Neo4j graph database."""

import json
from openai import OpenAIError

from graph_rag.config import client, neo4j_graph

CYPHER_PROMPT = """
You are an advanced assistant specializing in generating precise Cypher queries for a Neo4j graph database. The database consists of the following entities and relationships:

**Entities:**
- Part (`partSelectNumber`, `manufacturerPartNumber`, `name`, `price`)
- Manufacturer (`name`)
- Model (`modelNumber`, `name`)
- Review (`rating`, `reviewText`)

**Relationships:**
- Part is `MANUFACTURED_BY` Manufacturer
- Part is `COMPATIBLE_WITH` Model
- Part `HAS_REVIEW` Review

### Query Rules:

1. **Detect Entity Filters**: Identify specific attributes (e.g., `partSelectNumber`, `manufacturerPartNumber`, `modelNumber`) and apply `WHERE` clauses to filter results.
   - Example: "Find the part with manufacturerPartNumber 5304506533" should generate:
     `MATCH (p:Part {manufacturerPartNumber: '5304506533'}) RETURN p`

2. **Reflect Relationships**: If the user mentions relationships (e.g., "Find parts compatible with model M12345"), structure the query to match the relationship.
   - Example: "Find parts compatible with model M12345" should generate:
     `MATCH (m:Model {modelNumber: 'M12345'})<-[:COMPATIBLE_WITH]-(p:Part) RETURN p`

3. **Correct Attribute Usage**: Ensure the correct attributes are used in the query:
   - `manufacturerPartNumber` for part numbers from manufacturers.
   - `partSelectNumber` for parts based on their select number.
   - `modelNumber` for filtering based on models.

4. **Return Entity-Specific Fields**: If the user requests a specific field (e.g., "name"), return that field instead of the entire node.
   - Example: "Find the name of parts with manufacturerPartNumber 5304506533" should generate:
     `MATCH (p:Part {manufacturerPartNumber: '5304506533'}) RETURN p.name`

### Response Format:
- Output only the Cypher query, without any additional text.

### Examples:

**User Prompt**: "Find the part with partSelectNumber PS12345"
- **Cypher Query**: `MATCH (p:Part {partSelectNumber: 'PS12345'}) RETURN p`

**User Prompt**: "Find parts compatible with model M12345"
- **Cypher Query**: `MATCH (m:Model {modelNumber: 'M12345'})<-[:COMPATIBLE_WITH]-(p:Part) RETURN p`

**User Prompt**: "Find the name of parts with manufacturerPartNumber 5304506533"
- **Cypher Query**: `MATCH (p:Part {manufacturerPartNumber: '5304506533'}) RETURN p.name`

Respond with the Cypher query only.
"""



ENHANCED_CYPHER_PROMPT = """
You are an advanced Neo4j Cypher and graph database expert. Your task is to validate and optimize the following Cypher query. Please ensure the following:
1. Correct any syntax errors.
2. Check for logical issues, such as inefficiencies, missing indexes, or incorrect relationships.
3. Improve the query’s performance wherever possible, using best practices for Cypher.
4. If no changes are needed, return the original query.

Please respond with only the corrected or optimized Cypher query without any additional text. The output should be formatted as a complete and ready-to-execute query.
"""



def generate_cypher_query(user_input: str, model: str = "gpt-4o"):
    """Function to generate a Cypher query based on user input using OpenAI's API."""
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[{"role": "system", "content": CYPHER_PROMPT}, {"role": "user", "content": user_input}],
        )
        print("whats this response in generate_cypher_query ")
        print(response)

        cypher_query = response.choices[0].message.content
        print(f"Generated Cypher Query: {cypher_query}")

    except OpenAIError as e:
        print(f"An error occurred with the OpenAI API: {e}")
        print('we are here!')
        return user_input
    
    return response.choices[0].message.content


def correct_cypher_query(query: str, model: str = "gpt-4o") -> str:
    """Function to use OpenAI's API to correct a Cypher query if needed."""
    # Prompt to send to OpenAI for Cypher query correction
    try:
        # Generate the correction using OpenAI
        response = client.chat.completions.create(model=model, temperature=0, messages=[{"role": "system", "content": ENHANCED_CYPHER_PROMPT}, {"role": "user", "content": query}])

        # Return the corrected query
        return response.choices[0].message.content

    except OpenAIError as e:
        print(f"An error occurred with the OpenAI API: {e}")
        return query  # Return the original query if there's an error


def query_graph(user_input: str, threshold: float = 0.8):
    """Function to query the Neo4j graph database based on user input."""
    query = generate_cypher_query(user_input)
    print('this is the generated cypher query: ',query)

    reviewed_query = correct_cypher_query(query)

    print('this is the correct_cypher_query : ',reviewed_query)

    attempt = 0
    max_retries = 10
    while attempt < max_retries:
        try:  
            result = neo4j_graph.query(reviewed_query, params={"threshold": threshold})
            if result:
                return result
            else:
                print(f"Attempt {attempt + 1}: No results found, retrying...")
        except Exception as e:
            print(f"An error occurred on attempt {attempt + 1}: {e}")
        attempt += 1

    # If we reach here, retries were unsuccessful
    return [{"error": "We were unable to retrieve results for your query. Please refine your request."}]


def query_db(query: str) -> list:
    """Function to query the Neo4j graph database based on user input."""
    matches = []
    # Update the Cypher query as per your schema
    result = query_graph(query)

    for r in result:
        for _, value in r.items():
            entity_data = value
            if not entity_data:
                continue
            match = {}
            # Map the schema fields appropriately
            if "partSelectNumber" in entity_data:
                match["partSelectNumber"] = entity_data["partSelectNumber"]
            if "partName" in entity_data:
                match["partName"] = entity_data["partName"]
            if "manufacturerPartNumber" in entity_data:
                match["manufacturerPartNumber"] = entity_data["manufacturerPartNumber"]
            if "manufacturer" in entity_data:
                match["manufacturer"] = entity_data["manufacturer"]
            # Other fields related to the Part, Review, Model
            matches.append(match)
    return matches



if __name__ == "__main__":

    USER_QUERY = "Which parts are compatible with the FPHD2491KF0 Frigidaire Dishwasher?"
    print(query_db(USER_QUERY))
