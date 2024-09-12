"""Script to generate Cypher queries based on user input and query a Neo4j graph database."""

import json
from openai import OpenAIError
import sys
import re
sys.path.append('/Users/kohsheentiku/Desktop/Open-source/case-study/backend')

from graph_rag.config import client, neo4j_graph

CYPHER_PROMPT = """
You are an advanced assistant specializing in generating precise Cypher queries for a Neo4j graph database. Use `Question` and `Answer` and `Instruction` along with relationships as much as possible. These are the ONLY relationships and entities that exist, donthing else, you can make cypher queries using this only!The database consists of the following entities and relationships:

**Entities:**
1.a    Part(Properties: `partSelectNumber`, `partName`, `manufacturerPartNumber`, `price`, `rating`, `reviewCount`, `description`) 
1.b    Part(Properties: `name`,`id`,`url`,`price`,`status`) - related to `model`
1.c    Part(Properties: `partPrice`,`partNumber`,`fixPercentage`,`availability`,`partName`) - related to `symptoms`
1.d    Part(Properties: `partUrl`, `partName`) - related to `instruction`


2. Manufacturer(Properties: `name`)

3.a   Model (Properties: `modelNum`, `name`, `brand`, `modelType`, `description`, `modelNumber`)
3.b   Model (Properties: `description`,`modelNumber`, `brand`) - related to `instruction`
3.c   Model ( Properties: `modelNum`, '`name`,'`modelType` )
3.d   Model (Properties: `modelId`) - related to `symptom`

comment - modelId, modelNum, modelNumber are all the same!

4. Review (Properties: `reviewerName`, `date`, `rating`, `title`, `reviewText`)


5. Symptom (Properties: `name`)

6. RepairStory (Properties: `title`, `customer`, `instruction`, `difficulty`, `time`, `helpfulness`)

7. Instruction (Properties :`title`, `description`, `difficulty`, `repairTime`, `helpfulVotes`)
   Instruction for installation are for models, not for Parts.

8. Question( Properties: `question`, `questionDate`, `helpfulness`, `modelNumber`)

9. Answer (Properties: `answer`)

10. Manual (Properties: `manualName`, `manualUrl`)

11. Section (Properties: `name`, `url`)


**Relationships:**
1. Part(1.a) - `MANUFACTURED_BY` -> Manufacturer
   Part (1.a)  - `HAS_REVIEW` -> Review 
   Part(1.a) - `COMPATIBLE_WITH` -> Model(description,modelNumber, brand) (3.b)
   Part (1.a) - `HAS_REPAIR_STORY` -> RepairStory 
   Part - `HAS_QUESTION` -> Question 
   Part(Properties: `partUrl`, `partName`) - `USED_IN` -> Instruction 
   Part(Properties: `partPrice`,`partNumber`,`fixPercentage`,`availability`,`partName`) <- `FIXED_BY` - Symptom 

2. Model
   Model (Properties: `modelNum`, '`name`,'`modelType` ) - `HAS_SECTION` → Section
   Model - `HAS_MANUAL` -> Manual
   Model (Properties: `modelId`) - `HAS_SYMPTOM` -> Symptom
   Model (Properties: `description`,`modelNumber`, `brand`) - `HAS_INSTRUCTION` -> Instruction

3. Review - `HAS_REVIEW` -> Part

4. Symptom - `FIXED_BY` -> Part(Properties: `partPrice`,`partNumber`,`fixPercentage`,`availability`,`partName`)

5. Question - `HAS_ANSWER` -> Answer

6. Instruction - `USED_IN` -> Part


### Query Rules:

1. Firstly understand the NER in the query fed, try to map it to the correct entity,properties in the graph.
    Example - The ice maker on my Whirlpool fridge is not working. How can I fix it?
    MATCH (p:Part), (m:Model)
    WHERE toLower(p.description) CONTAINS "ice maker" OR toLower(m.description) CONTAINS "ice maker"
    RETURN p,m;

    may be run another query on this answer - match (n:Model{brand:'Whirlpool'}) return n
    may be innovative queries like - 
    MATCH (q:Question)-[r:HAS_ANSWER]->(a:Answer)
    WHERE toLower(a.answer) CONTAINS "ice maker"
    OR toLower(a.answer) CONTAINS "whirlpool"
    RETURN q, r, a;



2. **Detect Entity Filters**: Identify specific attributes (e.g., `partSelectNumber`, `manufacturerPartNumber`, `modelNumber`) and apply `WHERE` clauses to filter results. Sometimes the 'description' of the part contains the installation installation instructions, be sure to read fully.
   - Example: "Find the part with manufacturerPartNumber 5304506533" should generate:
     `MATCH (p:Part {manufacturerPartNumber: '5304506533'}) RETURN p`
  - Example: "How can I install part number PS11752778?" should generate:
     `MATCH (p:Part {partSelectNumber: 'PS11752778'}) RETURN p`

3 . Query to return all distinct brands 
    MATCH (n) 
    WHERE n.brand IS NOT NULL
    RETURN DISTINCT "node" as entity, n.brand AS brand
    UNION ALL 
    MATCH ()-[r]-() 
    WHERE r.brand IS NOT NULL
    RETURN DISTINCT "relationship" AS entity, r.brand AS brand;

    These are distinct brands in this dataset: "Frigidaire","Kenmore","Crosley","Electrolux","Tappan","Kelvinator","Gibson","General Electric",
    "Whirlpool","Maytag","LG","Amana","Litton","Admiral","Magic Chef","Jenn-Air","Hoover","KitchenAid","Roper","Haier","Samsung","Bosch",
    "Thermador","Inglis","Uni","Hotpoint","Norge","Speed Queen","Caloric"


2. **Reflect Relationships**: If the user mentions relationships (e.g., "Find parts compatible with model M12345"), structure the query to match the relationship.
   - Example: "Find parts compatible with model M12345" should generate:
     `MATCH (m:Model {modelNumber: 'M12345'})<-[:COMPATIBLE_WITH]-(p:Part) RETURN p`


4. **Return Entity-Specific Fields**: If the user requests a specific field (e.g., "name"), return that field instead of the entire node.
   - Example: "Find the name of parts with manufacturerPartNumber 5304506533" should generate:
     `MATCH (p:Part {manufacturerPartNumber: '5304506533'}) RETURN p.name`

5. **Return entity, relationship and entitity**
  - Example: Is this part, speaking about PS11752778 compatible with my 10640262010 model?
  MATCH (p:Part {partSelectNumber: 'PS11752778'})-[r:COMPATIBLE_WITH]->(m:Model) where m.modelNumber='10640262010' RETURN p,r,m

6. be able to match with other attributes in the node and answer generic queries
    Example - "The ice maker on fridge is not working. How can I fix it?"
    
    MATCH (m:Model)
    WITH m
    OPTIONAL MATCH (m)-[:HAS_SYMPTOM]->(s:Symptom)
    WHERE s.name CONTAINS 'ice maker'
    OPTIONAL MATCH (m)-[:HAS_INSTRUCTION]->(i:Instruction)
    WHERE i.description CONTAINS 'ice maker'
    OPTIONAL MATCH (m)-[:HAS_MANUAL]->(man:Manual)
    OPTIONAL MATCH (m)<-[:COMPATIBLE_WITH]-(p:Part)
    OPTIONAL MATCH (p)-[:HAS_REVIEW]->(r:Review)
    WHERE r.reviewText CONTAINS 'ice maker'
    OPTIONAL MATCH (p)-[:HAS_QUESTION]->(q:Question)-[:HAS_ANSWER]->(a:Answer)
    WHERE q.question CONTAINS 'ice maker' OR a.answer CONTAINS 'ice maker'
    RETURN m, s.name, i.description, r.reviewText, q.question, a.answer


7.example - "How do I replace the door seal on my LG dishwasher?"
    MATCH (m:Model {brand: 'LG'})
    WHERE m.modelType = 'Dishwasher'
    WITH m
    OPTIONAL MATCH (m)-[:HAS_INSTRUCTION]->(i:Instruction)
    WHERE i.title CONTAINS 'door seal' OR i.description CONTAINS 'door seal'
    RETURN m.modelNumber, i.title, i.description

8. example -"What are the most common issues with a Kenmore refrigerator?"
    MATCH (m:Model)
    WHERE m.brand = 'Kenmore' AND m.modelType = 'Refrigerator'
    WITH m
    OPTIONAL MATCH (m)-[:HAS_SYMPTOM]->(s:Symptom)
    RETURN m.modelNumber, s.symptomName, COUNT(s.symptomName) AS frequency
    ORDER BY frequency DESC

9. example - "Can I find a review for part PS11752778?"
    MATCH (p:Part {partSelectNumber: 'PS11752778'})-[:HAS_REVIEW]->(r:Review)
    RETURN p, r
10. "Is this part  PS11752778 compatible with my WDT780SAEM1 model?"
    MATCH p=(n:Part{partSelectNumber:'PS11752778'})-[x:COMPATIBLE_WITH]->(m:Model{modelNumber:"WDT780SAEM1"}) RETURN m



### Response Format:
- Output only the Cypher query, without any additional text.

### Examples:

**User Prompt**: "Find the part with partSelectNumber PS12345"
- **Cypher Query**: `MATCH (p:Part {partSelectNumber: 'PS12345'}) RETURN p`

**User Prompt**: "Find the installation instructions for a part with partSelectNumber PS12345"
- **Cypher Query**: `MATCH (p:Part {partSelectNumber: 'PS12345'}) RETURN p`
Read description and understand

**User Prompt**: "Find parts compatible with model M12345"
- **Cypher Query**: `MATCH (m:Model {modelNumber: 'M12345'})<-[:COMPATIBLE_WITH]-(p:Part) RETURN p`

**User Prompt**: "Find the name of parts with manufacturerPartNumber 5304506533"
- **Cypher Query**: `MATCH (p:Part {manufacturerPartNumber: '5304506533'}) RETURN p.name`

Respond with the Cypher query only and after that complete following all the prompt instrcutions of confidence interval
"""



ENHANCED_CYPHER_PROMPT = """
You are an advanced Neo4j Cypher and graph database expert. Your task is to validate and optimize the following Cypher query. Please ensure the following:
1. Correct any syntax errors.
2. Check for logical issues, such as inefficiencies, missing indexes, or incorrect relationships.
3. Improve the query’s performance wherever possible, using best practices for Cypher.
4. If no changes are needed, return the original query.

Please respond with only the corrected or optimized Cypher query without any additional text. The output should be formatted as a complete and ready-to-execute query and after that complete following all the prompt instrcutions of confidence interval, dont just return and think job is done.
"""



def generate_cypher_query(user_input: str, model: str = "gpt-4o"):
    """Function to generate a Cypher query based on user input using OpenAI's API."""
    
    try:
        print(' in generate_cypher_query')
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
    try:
        print('in correct_cypher_query')
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[{"role": "system", "content": ENHANCED_CYPHER_PROMPT}, {"role": "user", "content": query}]
        )

        # Extract and clean Cypher query using regular expressions to remove code block markers
        corrected_query = response.choices[0].message.content.strip()
        corrected_query = re.sub(r"```(?:cypher)?", "", corrected_query).strip()  # Remove ```cypher and ```

        return corrected_query

    except OpenAIError as e:
        print(f"An error occurred with the OpenAI API: {e}")
        return query


def query_graph(user_input: str, threshold: float = 0.7):
    
    """Function to query the Neo4j graph database based on user input."""
    print('in query graph')
    query = generate_cypher_query(user_input)
    print('this is the generated cypher query: ',query)

    reviewed_query = correct_cypher_query(query)

    print('this is the correct_cypher_query : ',reviewed_query)

    attempt = 0
    max_retries = 3
    while attempt < max_retries:
        try:  
            print("we are running the query in neo4j")
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
    print("in query db")
    matches = []
    # Update the Cypher query as per your schema
    result = query_graph(query)
    print(result)

    for r in result:
        for _, value in r.items():
            entity_data = value
            if not entity_data:
                continue
            match = {}
            # Map the schema fields appropriately for Part
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

            # Map the schema fields appropriately for Manufacturer
            if "manufacturer" in entity_data:
                match["manufacturer"] = entity_data["manufacturer"]

            # Map the schema fields appropriately for Model
            if "modelNumber" in entity_data:
                match["modelNumber"] = entity_data["modelNumber"]
            if "brand" in entity_data:
                match["brand"] = entity_data["brand"]
            if "modelType" in entity_data:
                match["modelType"] = entity_data["modelType"]
            if "description" in entity_data:
                match["description"] = entity_data["description"]

            # Map the schema fields appropriately for Review
            if "reviewerName" in entity_data:
                match["reviewerName"] = entity_data["reviewerName"]
            if "date" in entity_data:
                match["date"] = entity_data["date"]
            if "rating" in entity_data:
                match["rating"] = entity_data["rating"]
            if "title" in entity_data:
                match["title"] = entity_data["title"]
            if "reviewText" in entity_data:
                match["reviewText"] = entity_data["reviewText"]

            # Map the schema fields appropriately for Symptom
            if "symptomName" in entity_data:
                match["symptomName"] = entity_data["symptomName"]
            if "fixPercentage" in entity_data:
                match["fixPercentage"] = entity_data["fixPercentage"]
            if "partNumber" in entity_data:
                match["partNumber"] = entity_data["partNumber"]
            if "partPrice" in entity_data:
                match["partPrice"] = entity_data["partPrice"]
            if "availability" in entity_data:
                match["availability"] = entity_data["availability"]

            # Map the schema fields appropriately for RepairStory
            if "title" in entity_data:
                match["title"] = entity_data["title"]
            if "customer" in entity_data:
                match["customer"] = entity_data["customer"]
            if "instruction" in entity_data:
                match["instruction"] = entity_data["instruction"]
            if "difficulty" in entity_data:
                match["difficulty"] = entity_data["difficulty"]
            if "time" in entity_data:
                match["time"] = entity_data["time"]
            if "helpfulness" in entity_data:
                match["helpfulness"] = entity_data["helpfulness"]

            # Map the schema fields appropriately for Question and Answer
            if "question" in entity_data:
                match["question"] = entity_data["question"]
            if "questionDate" in entity_data:
                match["questionDate"] = entity_data["questionDate"]
            if "helpfulness" in entity_data:
                match["helpfulness"] = entity_data["helpfulness"]
            if "modelNumber" in entity_data:
                match["modelNumber"] = entity_data["modelNumber"]

            if "answer" in entity_data:
                match["answer"] = entity_data["answer"]

            # Add the match to the list
            matches.append(match)
    
    return matches




if __name__ == "__main__":

    USER_QUERY = "Which parts are compatible with the FPHD2491KF0 Frigidaire Dishwasher?"
    print(query_db(USER_QUERY))
