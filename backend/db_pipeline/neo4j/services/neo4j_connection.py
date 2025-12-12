from neo4j import GraphDatabase

from backend.db_pipeline.common.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# neo4j 접속
def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
