import os
import logging

from openai import OpenAI
from langchain_community.graphs import Neo4jGraph

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig()

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

neo4j_graph = Neo4jGraph(
    url=os.environ.get("NEO4J_URI"),
    username=os.environ.get("NEO4J_USERNAME"),
    password=os.environ.get("NEO4J_PASSWORD"),
)

# Constants
EMBEDDING_MODELS = {
    "small": "text-embedding-3-small",
    "medium": "text-embedding-3-medium",
    "large": "text-embedding-3-large"
}


GRAPH_ENTITIES = {
    "part": """
    Represents a specific part or component of a product, such as a 'Silverware Basket' or 'Detergent Dispenser'. 
    Parts may come in different types with varying sets of properties, defined as follows:

    a.  Part:
        - `partSelectNumber`: Unique identifier for the part.
        - `partName`: Name of the part.
        - `manufacturerPartNumber`: Manufacturer's part number.
        - `price`: Price of the part.
        - `rating`: User rating for the part.
        - `reviewCount`: Number of user reviews.
        - `description`: A brief description of the part.


    b.  Part linked to `Model` through `COMPATIBLE_WITH` relationship:
        - `name`: Name of the part.
        - `id`: Unique ID for the part.
        - `url`: The URL of the part.
        - `price`: Price of the part.
        - `status`: Status of the part (e.g., available, discontinued).

    c.  Part Linked to `symptom` entity through `HAS_SYMPTOM` relationship:
        - `partPrice`: Price of the part.
        - `partNumber`: Manufacturer's part number.
        - `fixPercentage`: Percentage of cases where the part resolves an issue.
        - `availability`: Availability status.
        - `partName`: Name of the part.

    d.  Part linked to  `instruction` entity through `HAS_INSTRUCTION`:
        - `partUrl`: URL of the part.
        - `partName`: Name of the part.
    """,

    "manufacturer": "Represents the manufacturer of a part. Examples include 'GE' and 'Whirlpool'. Attributes include 'name'.",
    "model": """
    Represents a specific model of an appliance or device. Different types of models are defined with varying sets of properties as follows:

    a. Model (General Model Information):
        - `modelNum`: Unique number identifying the model (e.g., "FPHD2491KF0").
        - `name`: Name of the model (e.g., "Frigidaire Professional Dishwasher").
        - `brand`: Brand associated with the model (e.g., "Frigidaire").
        - `modelType`: Type of the model (e.g., "Dishwasher").
        - `description`: Brief description of the model (e.g., "A professional dishwasher model with advanced cleaning technology.").
        - `modelNumber`: Another unique identifier for the model (e.g., "FPHD2491KF0").

    **Example Query**:
    MATCH (m:Model {modelNumber: 'FPHD2491KF0'})
    RETURN m;

    b. `Model` connected to `Instruction` entity:
        - `description`: Description of the model (e.g., "Frigidaire Dishwasher Model with advanced tech.").
        - `modelNumber`: Model number identifying the appliance (e.g., "FPHD2491KF0").
        - `brand`: Brand associated with the model (e.g., "Frigidaire").
        - Related to: `Instruction` (e.g., Installation instructions specific to the model).

    **Example Query**:
    MATCH (m:Model)-[:HAS_INSTRUCTION]->(i:Instruction)
    WHERE m.modelNumber = 'FPHD2491KF0'
    RETURN m, i;

    c. `Model` :
        - `modelNum`: Unique identifier for the model , synonymous with `modelNumber`(e.g., "12345").
        - `name`: Name of the model (e.g., "Frigidaire Dishwasher").
        - `modelType`: Type of the model (e.g., "Dishwasher","Refrigerator").

    **Example Query**:
    MATCH (m:Model {modelNum: '12345'})
    RETURN m;

    d. Model connected to `Symptom` entity through `HAS_SYMPTOM`:
        - `modelId`: Unique identifier for the model, synonymous with modelNum and modelNumber (e.g., "98765").
    Related to: `Symptom` (e.g., Symptoms associated with this model, such as "Water leakage").

    **Example Query**:
    MATCH (m:Model {modelId: '98765'})-[:HAS_SYMPTOM]->(s:Symptom)
    RETURN m, s;
    """,

    "section": "Represents different sections of a model, for example, 'Door Assembly' or 'Motor'. Attributes include 'name' and 'url'.",
    "manual": "Represents user or repair manuals for a model. Attributes include 'name' and 'url'.",
    "review": 
    """Represents user reviews or feedback for a part. Attributes include 'reviewText', 'rating', 'reviewerName', 'date', 'title'.
     This feedback includes the following details:
    - Date: "July 5, 2023"
    - Reviewer Name: "David M"
    - Rating: "100%"
    - Title: "David M"
    - Review Text: 
        "The part was a perfect match. Moisture was leaking, also steam. Replaced the gasket, fits snug as a bug in a rug. 
        Took care of the problem on a 15-year-old dishwasher. Still runs good.""",

    "symptom": 
    """Represents a symptom or issue associated with a model. 
        Attributes include 'name' which could be like 'leaking','Fridge too warm','Ice maker not making ice','Door Sweating','Clicking sound',
        'Fridge and Freezer are too warm','Fridge runs too long','Frost buildup', 'Won’t start', 'Touchpad does not respond', 
        "Ice maker won’t dispense ice", etc""",
        
    "repair_story": 
    """Represents customer repair stories detailing repairs involving parts. Attributes include 'instruction', 'difficulty', 'time', and 'helpfulness'.
    Example :
        {
            "difficulty": "Difficult",
            "instruction": "Well, I actually was unable to make a repair. Initially I inspected the door gasket and it appeared to be hardened, so I thought a new gasket would fix the issue. However, after replacing the gasket, the leak persisted. I then checked the spray arms and found no blockages. Finally, I realized that the door hinges were misaligned, causing the door not to seal properly. I will need to replace the hinges next.",
            "time": "More than 2 hours",
            "title": "Leaking water under door",
            "customer": "John from PEABODY, MA",
            "helpfulness": "2 of 2 people found this instruction helpful."
        }
    """,

    "question": 
    """Represents questions related to parts or models. Attributes include 'question', 'questionDate', 'helpfulness', 'modelNumber'.
            Example:
            {
                "questionDate": "July 8, 2019",
                "question": "When trying to install the part for the upper arm spray, the inside part goes up in the machine, so we are unable to screw it in. Any ideas?",
                "helpfulness": "4",
                "modelNumber": "For model number gld2445rfbo"
            }
    """,
    "answer": """Represents answers to questions. Attributes include 'answer'.
        {
            "answer": "Hello Kathy, thank you for writing. We do have an installation video for this replacement on your model. Here is a link: https://www.youtube.com/watch?v=OWFBZZEFB3E. We hope this helps."
        }
    """,
    "instruction": "Represents installation instructions related to models. Attributes include 'modelNumber', 'title', 'description', 'difficulty', 'repairTime', 'helpfulVotes'.Be sure to use only 'installation' as the name of the entity"
}

GRAPH_RELATIONSHIPS = {
    "MANUFACTURED_BY": "Represents that a part is manufactured by a specific manufacturer.",
    "COMPATIBLE_WITH": "Represents that a part is compatible with a specific model.",
    "HAS_REVIEW": "Represents that a part has a related review.",
    "HAS_SYMPTOM": "Represents that a model has a specific symptom or issue.",
    "FIXED_BY": "Represents that a symptom is resolved by a specific part.",
    "HAS_REPAIR_STORY": "Represents that a part has an associated customer repair story. Example - MATCH (p:Part)-[r:HAS_REPAIR_STORY]->(n:RepairStory) RETURN p,r,n",
    "HAS_QUESTION": "Represents that a part has an associated question. Example - MATCH (q:Question) <-[r:HAS_QUESTION]-> (n:Answer) RETURN n,r,q",
    "HAS_ANSWER": "Represents that a question about the part has an associated answer. Example - MATCH (q:Question) -[r:HAS_ANSWER]-> (n:Answer) RETURN n,r,q ",
    "HAS_SECTION": "Represents that a model has a section related to its structure.",
    "HAS_MANUAL": "Represents that a model has an associated manual.",
    "HAS_INSTRUCTION": "Represents that a model has associated instructions."
}

ENTITY_RELATIONSHIP_MAP = {
    "part": ["MANUFACTURED_BY", "HAS_REVIEW", "COMPATIBLE_WITH", "HAS_REPAIR_STORY", "HAS_QUESTION"],
    "manufacturer": ["MANUFACTURED_BY"],
    "model": ["COMPATIBLE_WITH", "HAS_SYMPTOM", "HAS_SECTION", "HAS_MANUAL", "HAS_INSTRUCTION"],
    "symptom": ["FIXED_BY", "HAS_SYMPTOM"],
    "review": ["HAS_REVIEW"],
    "repair_story": ["HAS_REPAIR_STORY"],
    "question": ["HAS_ANSWER", "HAS_QUESTION"],
    "answer": ["HAS_ANSWER"],
    "section": ["HAS_SECTION"],
    "manual": ["HAS_MANUAL"],
    "instruction": ["HAS_INSTRUCTION"]
}



