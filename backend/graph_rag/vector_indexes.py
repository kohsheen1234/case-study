import os
import argparse
import logging
from langchain_community.vectorstores import Neo4jVector
from langchain_community.embeddings import OpenAIEmbeddings
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# Constants
EMBEDDING_MODELS = {
    "small": "text-embedding-3-small",
    "medium": "text-embedding-3-medium",
    "large": "text-embedding-3-large"
}

# Logger configuration
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ENTITY_EMBEDDINGS = {
    "Part": ["partName", "description", "manufacturerPartNumber", "price", "rating", "reviewCount", "manufacturer"],
    "Model": ["modelNum", "brand", "modelType", "name", "description"],
    "Review": ["reviewerName", "date", "rating", "title", "reviewText"],
    "Symptom": ["name"],
    "RepairStory": ["title", "customer", "instruction", "difficulty", "time", "helpfulness"],
    "Question": ["question", "questionDate", "helpfulness", "modelNumber"],
    "Answer": ["answer"],
    "Section": ["name", "url"],
    "Manual": ["name", "url"],
}


def configure_logger(verbose):
    """Configure logger level based on verbosity"""
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

def create_vector_index(entity, properties):
    """Create vector index for a given entity, removing collection dependency"""
    try:
        # Using OpenAI's small embedding model as default
        vector_store = Neo4jVector.from_existing_graph(
            OpenAIEmbeddings(model=EMBEDDING_MODELS["small"]),
            url=os.environ.get("NEO4J_URI"),  # Collection parameter removed
            username=os.environ.get("NEO4J_USERNAME"),
            password=os.environ.get("NEO4J_PASSWORD"),
            index_name=entity,
            node_label=entity,
            text_node_properties=properties,
            embedding_node_property='embedding',
        )
        logger.info(f"Vector index created for {entity}")
    except Exception as e:
        logger.error(f"Error creating vector index for {entity}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Embed entities in Neo4j graph")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    configure_logger(args.verbose)

    # Loop through all entities in ENTITY_EMBEDDINGS
    for entity, properties in tqdm(ENTITY_EMBEDDINGS.items(), desc="Embedding entities"):
        create_vector_index(entity, properties)  # No need for collection argument


if __name__ == "__main__":
    main()
