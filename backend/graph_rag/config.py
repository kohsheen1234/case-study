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
    "part": "Represents a specific part or component of a product, such as a 'Silverware Basket' or 'Detergent Dispenser'. Attributes include 'partSelectNumber', 'manufacturerPartNumber', 'price', 'rating', 'reviewCount', 'description', 'fixPercentage', 'partPrice', 'availability', 'name'.",
    "manufacturer": "Represents the manufacturer of a part. Examples include 'GE' and 'Whirlpool'. Attributes include 'name'.",
    "model": "Represents the model of an appliance or device, such as 'FPHD2491KF0' or 'Dishwasher Model XYZ'. Attributes include 'modelId', 'modelNumber', 'brand', 'modelType', 'description'.",
    "section": "Represents different sections of a model, for example, 'Door Assembly' or 'Motor'. Attributes include 'name' and 'url'.",
    "manual": "Represents user or repair manuals for a model. Attributes include 'name' and 'url'.",
    "review": "Represents user reviews or feedback for a part. Attributes include 'reviewText', 'rating', 'reviewerName', 'date', 'title'.",
    "symptom": "Represents a symptom or issue associated with a model. Attributes include 'name', 'fixPercentage', 'partNumber', 'partPrice', 'availability'.",
    "repair_story": "Represents customer repair stories detailing repairs involving parts. Attributes include 'instruction', 'difficulty', 'time', and 'helpfulness'.",
    "question": "Represents questions related to parts or models. Attributes include 'question', 'questionDate', 'helpfulness', 'modelNumber'.",
    "answer": "Represents answers to questions. Attributes include 'answer'.",
    "instruction": "Represents installation instructions related to models. Attributes include 'modelNumber', 'title', 'description', 'difficulty', 'repairTime', 'helpfulVotes'.Be sure to use only 'installation' as the name of the entity"
}

GRAPH_RELATIONSHIPS = {
    "MANUFACTURED_BY": "Represents that a part is manufactured by a specific manufacturer.",
    "COMPATIBLE_WITH": "Represents that a part is compatible with a specific model.",
    "HAS_REVIEW": "Represents that a part has a related review.",
    "HAS_SYMPTOM": "Represents that a model has a specific symptom or issue.",
    "FIXED_BY": "Represents that a symptom is resolved by a specific part.",
    "HAS_REPAIR_STORY": "Represents that a part has an associated customer repair story.",
    "HAS_QUESTION": "Represents that a part or model has an associated question.",
    "HAS_ANSWER": "Represents that a question has an associated answer.",
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



