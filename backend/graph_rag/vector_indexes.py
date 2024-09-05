"""Module to create vector indexes for entities in the Neo4j graph."""

import os
import argparse
import time
from langchain_community.vectorstores import Neo4jVector
from langchain_community.embeddings import OpenAIEmbeddings
from tqdm import tqdm

from dotenv import load_dotenv

from graph_rag.config import EMBEDDINGS_MODEL, logging

load_dotenv()


ENTITIES_TO_EMBED = {
    "Part": ["name", "description"],
    "Model": ["name", "url"],
    "Video": ["name"],
    "Symptom": ["name"],
    "Story": ["title", "content"],
    "QnA": ["question", "answer"],
    "RelatedPart": ["name"],
    "Section": ["name"],
    "Manual": ["name"],
    "InstallationInstruction": ["title", "content"],
    "Manufacturer": ["name"],
    "Brand": ["name"],
    "ProductType": ["name"],
}


def embed_entities(entity_type: str, text_properties: list[str], collection: str, verbose: bool = False):
    """Embed entities of a specific type and create a vector index for them."""
    _ = Neo4jVector.from_existing_graph(
        OpenAIEmbeddings(model=EMBEDDINGS_MODEL),
        url=os.environ.get(f"NEO4J_{collection.upper()}_URI"),
        username=os.environ.get(f"NEO4J_{collection.upper()}_USERNAME"),
        password=os.environ.get(f"NEO4J_{collection.upper()}_PASSWORD"),
        index_name=entity_type,
        node_label=entity_type,
        text_node_properties=text_properties,
        embedding_node_property='embedding',
    )
    time.sleep(5)
    if verbose:
        logging.info(f"Vector index created for {entity_type}")


def main(collection: str, verbose: bool = False):
    """Create vector indexes for all entities."""
    for entity_type, text_properties in tqdm(ENTITIES_TO_EMBED.items()):
        embed_entities(entity_type, text_properties, collection, verbose)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Embed entities in the Neo4j graph")
    parser.add_argument("--collection", type=str, help="The collection to embed entities from")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging", default=False)
    args = parser.parse_args()

    main(args.collection, args.verbose)
