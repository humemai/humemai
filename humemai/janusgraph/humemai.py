"""Humemai class"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import nest_asyncio
from gremlin_python.driver.driver_remote_connection import \
    DriverRemoteConnection
from gremlin_python.driver.serializer import GraphSONSerializersV3d0
from gremlin_python.process.anonymous_traversal import traversal
from gremlin_python.process.graph_traversal import GraphTraversalSource, __
from gremlin_python.process.traversal import Direction, P, T, TextP
from gremlin_python.structure.graph import Edge, Graph, Vertex

from humemai.janusgraph.utils.docker import (copy_file_from_docker,
                                             copy_file_to_docker,
                                             remove_docker_compose,
                                             start_docker_compose,
                                             stop_docker_compose)
from humemai.utils import is_iso8601_datetime, read_json, write_json

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Humemai:
    def __init__(
        self,
        compose_file_path: str = None,
        warmup_seconds: int = 30,
        container_prefix: str = "jce",
        janusgraph_public_port: int = 8182,
        cassandra_port_9042: int = 9042,
        cassandra_port_9160: int = 9160,
        elasticsearch_public_port: int = 9200,
        visualizer_port_1: int = 3000,
        visualizer_port_2: int = 3001,
    ) -> None:
        """
        Initialize a Humemai object for connecting to JanusGraph and in-memory graph.

        Args:
            compose_file_path (str): Path to the Docker Compose file. Default is None,
                in which case the path is resolved relative to the script's directory.
            warmup_seconds (int): Seconds to wait after starting containers.
            container_prefix (str): Prefix for Docker container names.
            janusgraph_public_port (int): Host port for JanusGraph (default 8182).
            cassandra_port_9042 (int): Host port for Cassandra's 9042 (default 9042).
            cassandra_port_9160 (int): Host port for Cassandra's 9160 (default 9160).
            elasticsearch_public_port (int): Host port for Elasticsearch (default 9200).
            visualizer_port_1 (int): Host port for JanusGraph Visualizer (default 3000).
            visualizer_port_2 (int): Host port for JanusGraph Visualizer admin (default 3001).
        """
        # Logging configuration
        self.logger = logger

        # Resolve default path relative to this script's directory
        if compose_file_path is None:
            current_dir = Path(__file__).parent  # Directory of this script
            compose_file_path = current_dir / "docker-compose-cql-es.yml"

        # Convert to absolute path to avoid issues in production
        self.compose_file_path = os.path.abspath(compose_file_path)

        # Set environment variables for Docker Compose variable substitution
        os.environ["CONTAINER_PREFIX"] = container_prefix
        os.environ["JANUSGRAPH_PUBLIC_PORT"] = str(janusgraph_public_port)
        os.environ["CASSANDRA_PORT_9042"] = str(cassandra_port_9042)
        os.environ["CASSANDRA_PORT_9160"] = str(cassandra_port_9160)
        os.environ["ELASTICSEARCH_PUBLIC_PORT"] = str(elasticsearch_public_port)
        os.environ["VISUALIZER_PORT_1"] = str(visualizer_port_1)
        os.environ["VISUALIZER_PORT_2"] = str(visualizer_port_2)

        # Store project name
        self.project_name = container_prefix

        # Start containers
        self.start_docker_compose(warmup_seconds)

    def start_docker_compose(self, warmup_seconds: int) -> None:
        """
        Start the Docker Compose services specified in the given compose file.

        Args:
            warmup_seconds (int): Number of seconds to wait for the containers to warm up.
        """
        try:
            start_docker_compose(
                compose_file_path=self.compose_file_path,
                project_name=self.project_name,
                warmup_seconds=warmup_seconds,
            )
            # Reset connections or graph instances if necessary
            self.connection = None
            self.g = None
        except Exception as e:
            logger.error(f"Failed to start Docker Compose services: {e}")
            raise e

    def stop_docker_compose(self) -> None:
        """
        Stop the Docker Compose services specified in the given compose file.
        """
        try:
            stop_docker_compose(
                compose_file_path=self.compose_file_path, project_name=self.project_name
            )
        except Exception as e:
            logger.error(f"Failed to stop Docker Compose services: {e}")
            raise e

    def remove_docker_compose(self) -> None:
        """
        Remove the Docker Compose services specified in the given compose file along with orphans.
        """
        try:
            remove_docker_compose(
                compose_file_path=self.compose_file_path, project_name=self.project_name
            )
        except Exception as e:
            logger.error(f"Failed to remove Docker Compose services: {e}")
            raise e

    def connect(self) -> None:
        """Establish a connection to the Gremlin server."""
        try:
            if self.connection is None:
                self.logger.debug(
                    "Attempting to establish a new connection to the Gremlin server."
                )

                # Apply nest_asyncio to allow nested event loops (useful in Jupyter notebooks)
                nest_asyncio.apply()

                # Construct the Gremlin server URL dynamically based on environment variables
                gremlin_host = "localhost"  # Assuming connection from host machine
                gremlin_port = os.getenv("JANUSGRAPH_PUBLIC_PORT", "8182")
                gremlin_url = f"ws://{gremlin_host}:{gremlin_port}/gremlin"

                self.logger.debug(f"Gremlin server URL: {gremlin_url}")

                # Initialize Gremlin connection using GraphSON 3.0 serializer
                self.connection = DriverRemoteConnection(
                    gremlin_url,
                    "g",
                    message_serializer=GraphSONSerializersV3d0(),
                )

                # Set up the traversal source
                self.g = Graph().traversal().withRemote(self.connection)

                self.logger.info("Successfully connected to the Gremlin server.")

        except Exception as e:
            self.logger.error(f"Failed to connect to the Gremlin server: {e}")
            raise

    def disconnect(self) -> None:
        """Close the connection to the Gremlin server."""
        if self.connection:
            try:
                self.connection.close()
                self.logger.debug("Disconnected from the Gremlin server.")
            except Exception as e:
                self.logger.error(f"Failed to disconnect from the Gremlin server: {e}")
            finally:
                self.connection = None
                self.g = None

    def remove_all_data(self) -> None:
        """Remove all vertices and edges from the JanusGraph graph."""
        if self.g:
            self.g.V().drop().iterate()
        else:
            self.logger.warning("Graph traversal source (g) is not initialized.")

    def write_vertex(self, label: str, properties: dict = {}) -> Vertex:
        """Create a vertex with the given properties.

        Note that this does not check if the vertex already exists.

        Args:
            label (str): Label of the vertex.
            properties (dict): Dictionary of properties for the vertex. Defaults to {}.

        """
        vertex = self.g.addV(label)
        for key, value in properties.items():
            vertex = vertex.property(key, value)

        return vertex.next()

    def remove_vertex(self, vertex: Vertex) -> None:
        """
        Remove a vertex from the graph.

        Args:
            vertex (Vertex): The vertex to be removed.
        """
        if self.g.V(vertex.id).hasNext():
            self.g.V(vertex.id).drop().iterate()
        else:
            raise ValueError(f"Vertex with ID {vertex.id} not found.")

    def remove_vertex_properties(self, vertex: Vertex, property_keys: list) -> Vertex:
        """Remove specific properties from an existing vertex and return the updated.

        Args:
            vertex (Vertex): Vertex to update.
            property_keys (list): List of property keys to remove.
        """
        for key in property_keys:
            self.g.V(vertex.id).properties(key).drop().iterate()

        # Fetch and return the updated vertex
        updated_vertex = self.g.V(vertex.id).next()
        return updated_vertex

    def update_vertex_properties(self, vertex: Vertex, properties: dict) -> Vertex:
        """Update the properties of an existing vertex and return the updated vertex.

        Args:
            vertex (Vertex): Vertex to update.
            properties (dict): Dictionary of properties to update.

        Returns:
            Vertex: The updated vertex.
        """

        # Update the properties of the existing vertex
        for key, value in properties.items():
            self.g.V(vertex.id).property(key, value).iterate()

        # Fetch and return the updated vertex
        updated_vertex = self.g.V(vertex.id).next()

        return updated_vertex

    def get_vertices_by_properties(
        self, include_keys: list[str], exclude_keys: list[str] = []
    ) -> list[Vertex]:
        """Find vertices based on included and excluded properties.

        Args:
            include_keys (list of str): List of properties that must be included.
            exclude_keys (list of str, optional): List of properties that must be
                excluded.

        Returns:
            list of Vertex: List of vertices matching the criteria.
        """
        traversal = self.g.V()

        # Add filters for properties to include
        for key in include_keys:
            traversal = traversal.has(key)

        # Add filters for properties to exclude
        if exclude_keys:
            for key in exclude_keys:
                traversal = traversal.hasNot(key)

        return traversal.toList()

    def get_vertices_by_label_and_properties(
        self, label: str, include_keys: list[str] = [], exclude_keys: list[str] = []
    ) -> list[Vertex]:
        """
        Find vertices by label and filter them based on included and excluded
        properties.

        Args:
            label (str): The label to search for.
            include_keys (list of str, optional): List of properties that must be
                included.
            exclude_keys (list of str, optional): List of properties that must be
                excluded.

        Returns:
            list of Vertex: List of vertices matching the criteria.
        """
        traversal = self.g.V().hasLabel(label)

        # Add filters for properties to include
        if include_keys:
            for key in include_keys:
                traversal = traversal.has(key)

        # Add filters for properties to exclude
        if exclude_keys:
            for key in exclude_keys:
                traversal = traversal.hasNot(key)

        return traversal.toList()

    def get_vertices_by_partial_label(self, partial_label: str) -> list[Vertex]:
        """Retrieve vertices with partial label matching.

        Args:
            partial_label (str): Partial label to match.

        Returns:
            list of Vertex: List of vertices with partial label matching.
        """
        vertices = self.g.V().hasLabel(TextP.containing(partial_label)).toList()

        return vertices

    def get_all(self) -> tuple[list[Vertex], list[Edge]]:
        """Retrieve all vertices and edges from the graph.

        Returns:
            tuple: List of vertices and edges.
        """

        return self.g.V().toList(), self.g.E().toList()

    def write_edge(
        self, head: Vertex, label: str, tail: Vertex, properties: dict = {}
    ) -> Edge:
        """Create an edge between two vertices.

        Note that this does not check if the edge already exists.

        Args:
            head (Vertex): Vertex where the edge originates.
            label (str): Label of the edge.
            tail (Vertex): Vertex where the edge terminates.
            properties (dict): Dictionary of properties for the edge. Defaults to {}.

        """
        # Create a new edge with the provided properties
        edge = self.g.V(head.id).addE(label).to(__.V(tail.id))  # GraphTraversal object
        for key, value in properties.items():
            edge = edge.property(key, value)
        return edge.next()  # Return the newly created edge

    def remove_edge(self, edge: Edge) -> None:
        """
        Remove an edge from the graph.

        Args:
            edge (Edge): The edge to be removed.
        """

        if self.g.E(edge.id["@value"]["relationId"]).hasNext():
            self.g.E(edge.id["@value"]["relationId"]).drop().iterate()
        else:
            raise ValueError(f"Edge with ID {edge.id} not found.")

    def remove_edge_properties(self, edge: Edge, property_keys: list) -> Edge:
        """Remove specific properties from an existing edge and return the updated edge.

        Args:
            edge (Edge): Edge whose properties are to be removed.
            property_keys (list): List of property keys to remove.
        """
        for key in property_keys:
            # Drop the property if it exists
            self.g.E(edge.id["@value"]["relationId"]).properties(key).drop().iterate()

        # Fetch and return the updated edge
        updated_edge = self.g.E(edge.id["@value"]["relationId"]).next()

        return updated_edge

    def update_edge_properties(self, edge: Edge, properties: dict) -> Edge:
        """Update the properties of an existing edge and return the updated edge.

        Args:
            edge (Edge): Edge to update.
            properties (dict): Dictionary of properties to update.
        """

        # Update the properties of the existing edge
        for key, value in properties.items():
            self.g.E(edge.id["@value"]["relationId"]).property(key, value).iterate()

        # Fetch and return the updated edge
        updated_edge = self.g.E(edge.id["@value"]["relationId"]).next()

        return updated_edge

    def get_edges_by_vertices_and_label(
        self, head: Vertex, label: str, tail: Vertex
    ) -> list[Edge]:
        """Find an edge by its label and property.

        Args:
            head (Vertex): Head vertex of the edge.
            label (str): Label of the edge.
            tail (Vertex): Tail vertex of the edge.

        Returns:
            list of Edge: List of edges with the provided label.
        """
        return self.g.V(head.id).outE(label).where(__.inV().hasId(tail.id)).toList()

    def get_edges_by_label(self, label: str) -> list[Edge]:
        """Find an edge by its label.

        Args:
            label (str): Label of the edge.

        Returns:
            list of Edge: List of edges with the provided label.
        """

        return self.g.E().hasLabel(label).toList()

    def get_edges_by_properties(
        self, include_keys: list[str], exclude_keys: list[str] = []
    ) -> list[Edge]:
        """Find edges based on included and excluded properties.

        Args:
            include_keys (list of str): List of properties that must be included.
            exclude_keys (list of str, optional): List of properties that must be
                excluded.

        Returns:
            list of Edge: List of edges matching the criteria.
        """
        traversal = self.g.E()

        # Add filters for properties to include
        for key in include_keys:
            traversal = traversal.has(key)

        # Add filters for properties to exclude
        if exclude_keys:
            for key in exclude_keys:
                traversal = traversal.hasNot(key)

        return traversal.toList()

    def get_edges_by_label_and_properties(
        self, label: str, include_keys: list[str] = [], exclude_keys: list[str] = []
    ) -> list[Edge]:
        """
        Find edges by label and filter them based on included and excluded properties.

        Args:
            label (str): The label to search for.
            include_keys (list of str, optional): List of properties that must be
                included.
            exclude_keys (list of str, optional): List of properties that must be
                excluded.

        Returns:
            list of Edge: List of edges matching the criteria.
        """
        traversal = self.g.E().hasLabel(label)

        # Add filters for properties to include
        if include_keys:
            for key in include_keys:
                traversal = traversal.has(key)

        # Add filters for properties to exclude
        if exclude_keys:
            for key in exclude_keys:
                traversal = traversal.hasNot(key)

        return traversal.toList()

    def get_label(self, element: Vertex | Edge) -> str:
        """Retrieve the label of a vertex or edge.

        Args:
            element (Vertex | Edge): Vertex or edge to retrieve the label for.

        Returns:
            str: Label of the element.
        """
        return element.label

    def get_properties(self, vertex_or_edge: Vertex | Edge) -> dict:
        """Retrieve all properties of a vertex or edge, decoding JSON-encoded values.

        Args:
            vertex_or_edge (Vertex | Edge): Vertex or edge to retrieve properties for.

        Returns:
            dict: Dictionary of properties for the element.
        """
        if vertex_or_edge.properties is None:
            return {}

        return {prop.key: prop.value for prop in vertex_or_edge.properties}

    def get_within_hops(
        self,
        vertices: list[Vertex],
        hops: int,
        include_keys: list[str] = [],
        exclude_keys: list[str] = [],
    ) -> tuple[list[Vertex], list[Edge]]:
        """Retrieve all vertices and edges within N hops from a starting vertex.

        Args:
            vertices (list[Vertex]): List of starting vertex IDs for the traversal.
            hops (int): Number of hops to traverse from the starting vertex.
            include_keys (list of str, optional): List of properties that must be
                included.
            exclude_keys (list of str, optional): List of properties that must be
                excluded.

        Returns:
            tuple: List of vertices and edges within N hops from the starting vertex.
        """
        assert hops > 0, "Number of hops must be a non-negative integer."
        assert isinstance(vertices, list), "Vertices must be provided as a list."

        # Perform traversal for N hops
        traversal = (
            self.g.V([v.id for v in vertices])  # Start from the provided vertex IDs
            .emit()  # Emit the starting vertex
            .repeat(__.both().simplePath())  # Traverse to neighbors
            .times(hops)  # Limit the number of hops
            .dedup()  # Avoid duplicate vertices in the result
        )

        # Add filters for properties to include
        if include_keys:
            for key in include_keys:
                traversal = traversal.has(key)

        # Add filters for properties to exclude
        if exclude_keys:
            for key in exclude_keys:
                traversal = traversal.hasNot(key)

        # Execute the traversal and return the results
        vertices = traversal.toList()
        edges = self.get_edges_between_vertices(vertices)

        return vertices, edges

    def get_edges_between_vertices(self, vertices: list[Vertex]) -> list[Edge]:
        """Retrieve all edges between a list of vertices.

        Args:
            g (Graph): JanusGraph graph instance.
            vertices (list[Vertex]): List of vertices to find edges between.

        Returns:
            list[Edge]: List of edges between the provided vertices.
        """
        assert isinstance(vertices, list), "`vertices` must be provided as a list."
        # Extract vertex IDs from the provided Vertex objects
        vertex_ids = [v.id for v in vertices]

        edges_between_vertices = (
            self.g.V(vertex_ids)  # Start with the given vertex IDs
            .bothE()  # Traverse all edges connected to these vertices
            .where(
                __.otherV().hasId(P.within(vertex_ids))
            )  # Ensure the other end is in the vertex set
            .dedup()  # Avoid duplicates
            .toList()  # Convert traversal result to a list
        )

        return edges_between_vertices

    def write_short_term_vertex(self, label: str, properties: dict) -> Vertex:
        """
        Write a new short-term vertex to the graph. This does not check if a vertex with
        the same label is in the database or not. The current_time should be included
        in properties.

        Args:
            label (str): Label of the vertex.
            current_time (str): Current time in ISO 8601 format.
            properties (dict): Properties of the vertex.

        Returns:
            Vertex: The newly created short-term memory vertex.

        """
        assert (
            "current_time" in properties
        ), "Current time must be provided in properties."
        assert is_iso8601_datetime(
            properties["current_time"]
        ), "Current time must be an ISO 8601 datetime."

        short_term_vertex = self.write_vertex(label, properties)
        self.logger.debug(f"Created vertex with ID: {short_term_vertex.id}")

        return short_term_vertex

    def write_short_term_edge(
        self,
        head_vertex: Vertex,
        label: str,
        tail_vertex: Vertex,
        properties: dict,
    ) -> Edge:
        """
        Write a new short-term edge to the graph.

        This does not check if an edge with the same label is in the database or not.

        Args:
            head_vertex (Vertex): Head vertex of the edge.
            tail_vertex (Vertex): Tail vertex of the edge.
            label (str): Label of the edge.
            properties (dict): Properties of the edge.

        Returns:
            Edge: The newly created edge.
        """
        assert (
            "current_time" in properties
        ), "Current time must be provided in properties."
        assert is_iso8601_datetime(
            properties["current_time"]
        ), "Current time must be an ISO 8601 datetime."

        edge = self.write_edge(head_vertex, label, tail_vertex, properties)
        self.logger.debug(f"Created edge with ID: {edge.id}")

        return edge

    def move_short_term_vertex(self, vertex: Vertex, action: str) -> None:
        """Move the short-term vertex to another memory type.

        Args:
            vertex (Vertex): The vertex to be moved.
            action (str): The action to be taken. Choose from 'episodic' or 'semantic'

        """
        assert action in [
            "episodic",
            "semantic",
        ], "Invalid action. Choose from 'episodic' or 'semantic'."
        assert "current_time" in self.get_properties(
            vertex
        ), "Current time must be provided in properties."

        properties = self.get_properties(vertex)
        properties["num_recalled"] = 0
        current_time = properties.pop("current_time")

        if action not in ["episodic", "semantic"]:
            self.logger.error("Invalid action. Choose from 'episodic' or 'semantic'.")
            raise ValueError("Invalid action. Choose from 'episodic' or 'semantic'.")

        updated_vertex = self.remove_vertex_properties(vertex, ["current_time"])
        properties["time_added"] = current_time
        updated_vertex = self.update_vertex_properties(vertex, properties)
        self.logger.debug(
            f"Moved vertex to {action} memory with ID: {updated_vertex.id}"
        )

    def move_short_term_edge(self, edge: Edge, action: str) -> None:
        """Move the short-term edge to another memory type.

        Args:
            edge (Edge): The edge to be moved.
            action (str): The action to be taken. Choose from 'episodic' or 'semantic'

        """
        assert action in [
            "episodic",
            "semantic",
        ], "Invalid action. Choose from 'episodic' or 'semantic'."
        assert "current_time" in self.get_properties(
            edge
        ), "Current time must be provided in properties."

        properties = self.get_properties(edge)
        properties["num_recalled"] = 0
        current_time = properties.pop("current_time")

        updated_edge = self.remove_edge_properties(edge, ["current_time"])
        properties["time_added"] = current_time
        updated_edge = self.update_edge_properties(edge, properties)
        self.logger.debug(f"Moved edge to {action} memory with ID: {updated_edge.id}")

    def remove_all_short_term(self) -> None:
        """Remove all pure short-term vertices and edges.

        This method removes all the short-term edges.

        """
        self.g.V().has("current_time").drop().iterate()
        self.logger.debug("Removed all short-term vertices (and edges).")

    def write_long_term_vertex(
        self,
        label: str,
        properties: dict,
    ) -> Vertex:
        """
        Write a new long-term vertex to the graph. This is directly writing a vertex to
        the long-term memory.

        Args:
            label (str): Label of the vertex.
            properties (dict): Properties of the vertex.

        Returns:
            Vertex: The updated vertex.
        """
        assert "time_added" in properties

        assert is_iso8601_datetime(
            properties["time_added"]
        ), "time must be an ISO 8601 datetime."

        properties["num_recalled"] = 0
        # Step 1: Create a vertex with the given label and properties
        vertex = self.write_vertex(label, properties)
        self.logger.debug(f"Created a long-term vertex with ID: {vertex.id}")

        return vertex

    def write_long_term_edge(
        self, head_vertex: Vertex, label: str, tail_vertex: Vertex, properties: dict
    ) -> Edge:
        """
        Write a new long-term edge to the graph.

        Args:
            head_vertex (Vertex): Head vertex of the edge.
            label (str): Label of the edge.
            tail_vertex (Vertex): Tail vertex of the edge.
            properties (dict): Properties of the edge.

        Returns:
            Edge: The newly created edge.
        """
        assert "time_added" in properties

        assert is_iso8601_datetime(
            properties["time_added"]
        ), "time must be an ISO 8601 datetime."

        properties["num_recalled"] = 0
        edge = self.write_edge(head_vertex, label, tail_vertex, properties)
        self.logger.debug(f"Created a long-term edge with ID: {edge.id}")

        return edge

    def connect_duplicate_vertices(self, match_logic: str = "exact_label") -> None:
        """Connect duplicate vertices based on the match logic. This will create
        "meta" nodes for each label and connect the duplicate nodes to the meta node
        with a "has_meta_node" edge.

        Args:
            match_logic (str): The logic to match vertices. Choose from 'exact_label' or
                'exact_properties'.

        """
        if match_logic == "exact_label":
            repeated_labels = [
                key
                for key, val in self.g.V().label().groupCount().toList()[0].items()
                if val > 1
            ]
            self.logger.debug(f"Repeated labels found: {repeated_labels}")

            for label in repeated_labels:
                # Create a reference node for the label
                if self.g.V().hasLabel(f"meta_{label}").hasNext():
                    meta_node = self.g.V().hasLabel(f"meta_{label}").next()
                else:
                    meta_node = (
                        self.g.addV(f"meta_{label}").property("meta_node", True).next()
                    )
                unconnected_nodes = (
                    self.g.V().hasLabel(label).not_(__.outE("has_meta_node")).toList()
                )

                for node in unconnected_nodes:
                    self.g.V(node).addE("has_meta_node").to(meta_node).iterate()
        else:
            raise NotImplementedError(
                "Currently, only 'exact_label' match logic is supported."
            )

    def _increment_num_recalled(
        self, vertices: list[Vertex], edges: list[Edge]
    ) -> tuple[list[Vertex], list[Edge]]:
        """Helper function to increment 'num_recalled' on Edges

        Args:
            vertices (list of Vertex): List of vertices to be updated.
            edges (list of Edge): List of edges to be updated.

        Returns:
            tuple: List of updated vertices and edges.

        """
        vertices_updated = []
        for vertex in vertices:
            num_recalled = self.get_properties(vertex).get("num_recalled")
            vertex = self.update_vertex_properties(
                vertex, {"num_recalled": num_recalled + 1}
            )
            vertices_updated.append(vertex)

        edges_updated = []
        for edge in edges:
            num_recalled = self.get_properties(edge).get("num_recalled")
            edge = self.update_edge_properties(edge, {"num_recalled": num_recalled + 1})
            edges_updated.append(edge)

        return vertices_updated, edges_updated

    def get_working(
        self,
        hops: int = 1,
        include_all_long_term: bool = False,
        match_logic: str = "exact_label",
    ) -> tuple[list[Vertex], list[Edge], list[Vertex], list[Edge]]:
        """
        Retrieves the working memory based on the short-term memories. This considers
        meta nodes for duplicate vertices. If include_all_long_term is True, all
        long-term memories are included. Otherwise, the long-term memories are included
        based on the hops.

        Currently we only use the labels from the short-term memory to retrieve the
        long-term memory with the exact string matching.

        Args:
            hops (int): Number of hops to traverse from the trigger vertex.
            include_all_long_term (bool): If True, include all long-term memories.
            match_logic (str): The logic to match vertices. Choose from 'exact_label' or
                'exact_properties'.

        Returns:
            tuple: short-term vertices, short-term edges, long-term vertices, long-term
                edges.
        """
        assert hops > 0, "Hops must be a positive integer."
        if match_logic != "exact_label":
            raise NotImplementedError(
                "Currently, only 'exact_label' match logic is supported."
            )

        short_term_vertices, short_term_edges = self.get_all_short_term()

        if len(short_term_vertices) == 0:
            self.logger.debug("Short-term memory is emtpy")
            return [], [], [], []

        if include_all_long_term:
            long_term_vertices, long_term_edges = self.get_all_long_term()

        else:
            assert (
                hops is not None
            ), "hops must be provided when include_all_long_term is False."

            # Exact string matching for labels
            trigger_labels = [vertex.label for vertex in short_term_vertices]
            long_term_vertices = (
                self.g.V()
                .hasLabel(*trigger_labels)
                .emit()
                .repeat(
                    __.bothE()
                    .otherV()
                    .union(
                        __.out("has_meta_node"),
                        __.out("has_meta_node").in_("has_meta_node"),
                        __.in_("has_meta_node"),
                        __.identity(),  # Also keep the current node
                    )
                    .simplePath()  # Avoid revisiting nodes in the same path
                )
                .times(hops)
                .dedup()  # Remove duplicate vertices
                .hasNot("meta_node")  # Exclude vertices with 'meta_node'
                .has("num_recalled")  # Only include long-term vertices
                .hasNot("current_time")  # Exclude short-term vertices
                .toList()
            )

            long_term_edges = self.get_edges_between_vertices(long_term_vertices)

        long_term_vertices, long_term_edges = self._increment_num_recalled(
            long_term_vertices, long_term_edges
        )

        return (
            short_term_vertices,
            short_term_edges,
            long_term_vertices,
            long_term_edges,
        )

    def save_db_as_json(self, json_name: str = "db.json") -> None:
        """Read the database as a JSON file.

        Args:
            json_name (str): The name of the JSON file.
        """
        self.g.io(json_name).write().iterate()

        copy_file_from_docker(
            "jce-janusgraph", f"/opt/janusgraph/{json_name}", json_name
        )

    def load_db_from_json(self, json_name: str = "db.json") -> None:
        """Write a JSON file to the database.

        Args:
            json_name (str): The name of the JSON file.
        """
        copy_file_to_docker("jce-janusgraph", json_name, f"/opt/janusgraph/{json_name}")

        self.g.io(json_name).read().iterate()

    def get_all_short_term(self) -> tuple[list[Vertex], list[Edge]]:
        """
        Retrieve all short-term vertices and edges from the graph.

        Returns:
            tuple: List of short-term vertices and edges.
        """
        vertices = self.g.V().has("current_time").toList()
        edges = self.g.E().has("current_time").toList()

        return vertices, edges

    def get_all_long_term(self) -> tuple[list[Vertex], list[Edge]]:
        """
        Retrieve all long-term vertices and edges from the graph.

        Returns:
            tuple: List of long-term vertices and edges.
        """
        vertices = self.g.V().has("num_recalled").toList()
        edges = self.g.E().has("num_recalled").toList()

        return vertices, edges

    def get_all_episodic(self) -> tuple[list[Vertex], list[Edge]]:
        """
        Retrieve all episodic vertices and edges from the graph.
        Episodic memories have 'time_added' property but do not have 'derived_from' property.

        Returns:
            tuple: List of episodic vertices and edges.
        """
        vertices = self.g.V().has("time_added").hasNot("derived_from").toList()
        edges = self.g.E().has("time_added").hasNot("derived_from").toList()

        return vertices, edges

    def get_all_semantic(self) -> tuple[list[Vertex], list[Edge]]:
        """
        Retrieve all semantic vertices and edges from the graph.
        Semantic memories have both 'time_added' and 'derived_from' properties.

        Returns:
            tuple: List of semantic vertices and edges.
        """
        vertices = self.g.V().has("time_added").has("derived_from").toList()
        edges = self.g.E().has("time_added").has("derived_from").toList()

        return vertices, edges

    def get_all_episodic_in_time_range(
        self, start_time: str, end_time: str
    ) -> tuple[list[Vertex], list[Edge]]:
        """Retrieve episodic vertices and edges within a time range.
        Episodic memories have 'time_added' property but do not have 'derived_from' property.

        Args:
            start_time (str): Lower bound of the time range.
            end_time (str): Upper bound of the time range.

        Returns:
            tuple: List of episodic vertices and edges within the time range.
        """
        assert is_iso8601_datetime(
            start_time
        ), "Lower bound must be an ISO 8601 datetime."
        assert is_iso8601_datetime(
            end_time
        ), "Upper bound must be an ISO 8601 datetime."

        vertices = (
            self.g.V()
            .has("time_added", P.gte(start_time).and_(P.lte(end_time)))
            .hasNot("derived_from")  # Episodic memories don't have derived_from
            .toList()
        )
        edges = (
            self.g.E()
            .has("time_added", P.gte(start_time).and_(P.lte(end_time)))
            .hasNot("derived_from")  # Episodic memories don't have derived_from
            .toList()
        )

        return vertices, edges

    def get_all_semantic_in_time_range(
        self, start_time: str, end_time: str
    ) -> tuple[list[Vertex], list[Edge]]:
        """Retrieve semantic vertices and edges within a time range.
        Semantic memories have both 'time_added' and 'derived_from' properties.

        Args:
            start_time (str): Lower bound of the time range.
            end_time (str): Upper bound of the time range.

        Returns:
            tuple: List of semantic vertices and edges within the time range.
        """
        assert is_iso8601_datetime(
            start_time
        ), "Lower bound must be an ISO 8601 datetime."
        assert is_iso8601_datetime(
            end_time
        ), "Upper bound must be an ISO 8601 datetime."

        vertices = (
            self.g.V()
            .has("time_added", P.gte(start_time).and_(P.lte(end_time)))
            .has("derived_from")  # Semantic memories have derived_from
            .toList()
        )
        edges = (
            self.g.E()
            .has("time_added", P.gte(start_time).and_(P.lte(end_time)))
            .has("derived_from")  # Semantic memories have derived_from
            .toList()
        )

        return vertices, edges

    def get_all_long_term_in_time_range(
        self, start_time: str, end_time: str
    ) -> tuple[list[Vertex], list[Edge]]:
        """Retrieve long-term vertices and edges within a time range.

        Args:
            start_time (str): Lower bound of the time range.
            end_time (str): Upper bound of the time range.

        Returns:
            list of Vertex: List of long-term vertices within the time range.
        """
        assert is_iso8601_datetime(
            start_time
        ), "Lower bound must be an ISO 8601 datetime."
        assert is_iso8601_datetime(
            end_time
        ), "Upper bound must be an ISO 8601 datetime."

        episodic_vertices, episodic_edges = self.get_all_episodic_in_time_range(
            start_time, end_time
        )
        semantic_vertices, semantic_edges = self.get_all_semantic_in_time_range(
            start_time, end_time
        )
        long_term_vertices = episodic_vertices + semantic_vertices
        long_term_edges = episodic_edges + semantic_edges

        return long_term_vertices, long_term_edges
