from TravSHACL import ShapeSchema
from rdflib import Graph

def shacl_validation(kg_access_method, constraint_path, kg_path, sparql_access_url, output_dir):
    """
    Validates a SHACL shape schema against a given enriched knowledge graph with constraints
    and prioritization heuristics.

    This function uses the `ShapeSchema` class and its methods to perform validation.
    The prioritization is determined based on target definitions, in-degree, or constraints size.

    Args:

    Returns:
        Validation results as provided by the `ShapeSchema.validate` method.
    """
    match kg_access_method:
        case "memory" | "memory-numerical":
            if kg_path is None:
                raise ValueError("No knowledge graph provided")
            knowledge_graph = Graph()
            knowledge_graph.parse(kg_path, format='nt')
        case "hybrid" | "sparql":
            knowledge_graph = sparql_access_url
            if knowledge_graph is None:
                raise ValueError("No knowledge graph provided")
        case _:
            raise ValueError("Invalid argument for --kg-access-method")

    shape_schema = ShapeSchema(
        schema_dir=constraint_path,
        endpoint=knowledge_graph,
        endpoint_user=None,  # username if validating a private endpoint
        endpoint_password=None,  # password if validating a private endpoint
        use_selective_queries=True,
        save_outputs=True,
        output_dir=output_dir
    )
    shape_schema.validate()