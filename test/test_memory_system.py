import unittest
from datetime import datetime

from rdflib import RDF, Literal, Namespace, URIRef
from rdflib.namespace import XSD

from humemai import MemorySystem

# Define the custom namespace for the ontology
humemai = Namespace("https://humem.ai/ontology#")


class TestMemorySystem(unittest.TestCase):

    def setUp(self):
        # Initialize the memory system
        self.memory = MemorySystem()

        # Define multiple triples
        self.triples = [
            (
                URIRef("https://example.org/person/Alice"),
                URIRef("https://example.org/event/met"),
                URIRef("https://example.org/person/Bob"),
            ),
            (
                URIRef("https://example.org/person/Bob"),
                URIRef("https://example.org/event/met"),
                URIRef("https://example.org/person/Charlie"),
            ),
            (
                URIRef("https://example.org/person/Alice"),
                URIRef("https://example.org/relationship/knows"),
                URIRef("https://example.org/person/David"),
            ),
            (
                URIRef("https://example.org/person/Charlie"),
                URIRef("https://example.org/event/met"),
                URIRef("https://example.org/person/Eve"),
            ),
            (
                URIRef("https://example.org/person/David"),
                URIRef("https://example.org/event/invited"),
                URIRef("https://example.org/person/Alice"),
            ),
            (
                URIRef("https://example.org/person/Eve"),
                URIRef("https://example.org/relationship/worksWith"),
                URIRef("https://example.org/person/Bob"),
            ),
            (
                URIRef("https://example.org/person/Charlie"),
                URIRef("https://example.org/event/attended"),
                URIRef("https://example.org/person/Bob"),
            ),
            (
                URIRef("https://example.org/entity/Dog"),
                URIRef("https://example.org/relationship/is"),
                URIRef("https://example.org/entity/Animal"),
            ),
            (
                URIRef("https://example.org/person/Alice"),
                URIRef("https://example.org/relationship/owns"),
                URIRef("https://example.org/entity/Dog"),
            ),
            (
                URIRef("https://example.org/person/Eve"),
                URIRef("https://example.org/event/met"),
                URIRef("https://example.org/person/Alice"),
            ),
            (
                URIRef("https://example.org/person/John"),
                URIRef("https://example.org/relationship/loves"),
                URIRef("https://example.org/entity/Animal"),
            ),
        ]

        # Define qualifiers for episodic memories using URIRef and Literal
        episodic_qualifiers_1 = {
            humemai.location: Literal("New York"),
            humemai.eventTime: Literal(
                "2024-04-27T15:00:00",
                datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
            humemai.emotion: Literal("happy"),
            humemai.event: Literal("Coffee meeting"),
        }
        episodic_qualifiers_2 = {
            humemai.location: Literal("London"),
            humemai.eventTime: Literal(
                "2024-05-01T10:00:00",
                datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
            humemai.emotion: Literal("excited"),
            humemai.event: Literal("Conference meeting"),
        }
        episodic_qualifiers_3 = {
            humemai.location: Literal("Paris"),
            humemai.eventTime: Literal(
                "2024-05-03T14:00:00",
                datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
            humemai.emotion: Literal("curious"),
            humemai.event: Literal("Workshop"),
        }

        # Add episodic memories
        self.memory.memory.add_episodic_memory(
            [self.triples[0]], qualifiers=episodic_qualifiers_1
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[1]], qualifiers=episodic_qualifiers_2
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[2]], qualifiers=episodic_qualifiers_3
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[3]], qualifiers=episodic_qualifiers_1
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[4]], qualifiers=episodic_qualifiers_2
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[5]], qualifiers=episodic_qualifiers_3
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[6]], qualifiers=episodic_qualifiers_1
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[7]], qualifiers=episodic_qualifiers_2
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[8]], qualifiers=episodic_qualifiers_3
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[9]], qualifiers=episodic_qualifiers_1
        )
        self.memory.memory.add_episodic_memory(
            [self.triples[10]], qualifiers=episodic_qualifiers_2
        )

        # Add semantic memories
        semantic_qualifiers = {
            humemai.knownSince: Literal(
                "2023-01-01T00:00:00",
                datatype="http://www.w3.org/2001/XMLSchema#dateTime",
            ),
            humemai.derivedFrom: Literal("animal_research"),
            humemai.strength: Literal(
                5, datatype="http://www.w3.org/2001/XMLSchema#integer"
            ),
        }
        self.memory.memory.add_semantic_memory(
            [self.triples[7]], qualifiers=semantic_qualifiers
        )
        self.memory.memory.add_semantic_memory(
            [self.triples[7]], qualifiers=semantic_qualifiers
        )
        self.memory.memory.add_semantic_memory(
            [self.triples[10]], qualifiers=semantic_qualifiers
        )
        self.memory.memory.add_semantic_memory(
            [self.triples[10]], qualifiers=semantic_qualifiers
        )

        # Add short-term memories
        self.memory.memory.add_short_term_memory(
            [self.triples[8]], qualifiers={humemai.location: Literal("Alice's home")}
        )
        self.memory.memory.add_short_term_memory(
            [self.triples[8]], qualifiers={humemai.location: Literal("Paris Cafe")}
        )

        # Add another short-term memory
        self.memory.memory.add_short_term_memory(
            [self.triples[9]], qualifiers={humemai.location: Literal("Paris Cafe")}
        )
        self.memory.memory.add_short_term_memory(
            [self.triples[9]], qualifiers={humemai.location: Literal("Paris Cafe")}
        )

    def test_working_memory_hop_0(self):
        """Test that hop=0 only retrieves short-term memories involving Alice."""
        trigger_node = URIRef("https://example.org/person/Alice")
        working_memory = self.memory.get_working_memory(
            trigger_node=trigger_node, hops=0
        )

        self.assertEqual(working_memory.get_main_triple_count_except_event(), 2)
        self.assertEqual(working_memory.get_memory_count(), 4)

    def test_working_memory_hop_1(self):
        """Test that hop=1 retrieves immediate neighbors' relationships."""
        trigger_node = URIRef("https://example.org/person/Alice")
        working_memory = self.memory.get_working_memory(
            trigger_node=trigger_node, hops=1
        )

        self.assertEqual(working_memory.get_main_triple_count_except_event(), 5)
        self.assertEqual(working_memory.get_memory_count(), 9)

    def test_working_memory_hop_2(self):
        """Test that hop=2 retrieves 2-hop neighbors' relationships."""
        trigger_node = URIRef("https://example.org/person/Alice")
        working_memory = self.memory.get_working_memory(
            trigger_node=trigger_node, hops=2
        )

        self.assertEqual(working_memory.get_main_triple_count_except_event(), 10)
        self.assertEqual(working_memory.get_memory_count(), 16)

    def test_working_memory_hop_3(self):
        """Test that hop=3 retrieves 3-hop neighbors' relationships."""
        trigger_node = URIRef("https://example.org/person/Alice")
        working_memory = self.memory.get_working_memory(
            trigger_node=trigger_node, hops=3
        )

        self.assertEqual(working_memory.get_main_triple_count_except_event(), 11)
        self.assertEqual(working_memory.get_memory_count(), 19)

    def test_working_memory_include_all_long_term(self):
        """Test that all long-term memories are included when include_all_long_term=True."""
        working_memory = self.memory.get_working_memory(include_all_long_term=True)

        self.assertEqual(working_memory.get_main_triple_count_except_event(), 11)
        self.assertEqual(working_memory.get_memory_count(), 19)

    def test_recalled_value_increment(self):
        """Test that the recalled value increments correctly."""
        trigger_node = URIRef("https://example.org/person/Alice")

        # Retrieve working memory at different hops
        self.memory.get_working_memory(trigger_node=trigger_node, hops=1)
        self.memory.get_working_memory(trigger_node=trigger_node, hops=2)

        # Check that recalled has incremented accordingly
        working_memory = self.memory.get_working_memory(
            trigger_node=trigger_node, hops=3
        )

        # Find an example of a statement and assert its recall count
        memory_statements = working_memory.graph.triples((None, None, None))
        for triple in memory_statements:
            if str(triple[1]) == "met" and str(triple[2]) == "Bob":
                # Ensure the 'recalled' qualifier has increased properly (should be 3)
                qualifiers = list(working_memory.graph.predicate_objects(triple[0]))
                for pred, obj in qualifiers:
                    if str(pred) == str(humemai.recalled):
                        self.assertEqual(int(obj), 3)

    def test_empty_memory(self):
        """Test that working memory handles empty memory cases."""
        empty_memory_system = MemorySystem()
        working_memory = empty_memory_system.get_working_memory(
            URIRef("https://example.org/person/Alice"), hops=1
        )

        self.assertEqual(working_memory.get_main_triple_count_except_event(), 0)
        self.assertEqual(working_memory.get_memory_count(), 0)

    def test_invalid_trigger_node(self):
        """Test behavior when an invalid trigger node is provided."""
        with self.assertRaises(ValueError):
            self.memory.get_working_memory(trigger_node=None, hops=1)


class TestMemorySystemMethods(unittest.TestCase):
    def setUp(self):
        """
        Set up a new MemorySystem instance before each test.
        """
        self.memory_system = MemorySystem()

        # Add a short-term memory to the memory system
        self.short_term_triplet_1 = (
            URIRef("https://example.org/Alice"),
            URIRef("https://example.org/meet"),
            URIRef("https://example.org/Bob"),
        )
        self.short_term_triplet_2 = (
            URIRef("https://example.org/Bob"),
            URIRef("https://example.org/travel"),
            URIRef("https://example.org/Paris"),
        )

        # Add these triples to short-term memory
        self.memory_system.memory.add_short_term_memory(
            [self.short_term_triplet_1],
            qualifiers={
                humemai.location: Literal("Paris"),
                humemai.currentTime: Literal(
                    "2023-05-05T00:00:00", datatype=XSD.dateTime
                ),
            },
        )
        self.memory_system.memory.add_short_term_memory(
            [self.short_term_triplet_2],
            qualifiers={
                humemai.location: Literal("Paris"),
                humemai.currentTime: Literal(
                    "2023-05-06T00:00:00", datatype=XSD.dateTime
                ),
            },
        )

    def test_move_short_term_to_long_term(self):
        """
        Test that a specific short-term memory is moved to long-term memory.
        """
        # Initially, ensure there are short-term memories
        short_term_memories = self.memory_system.memory.get_short_term_memories()
        self.assertEqual(short_term_memories.get_memory_count(), 2)

        # Move short-term memory with ID 0 to long-term memory
        self.memory_system.move_short_term_to_episodic(Literal(0))

        # Check that the short-term memory count is now 1 (after moving one to long-term)
        short_term_memories = self.memory_system.memory.get_short_term_memories()
        self.assertEqual(short_term_memories.get_memory_count(), 1)

        # Check that the long-term memory count is now 1 (since one was moved)
        long_term_memories = self.memory_system.memory.get_long_term_memories()
        self.assertEqual(long_term_memories.get_memory_count(), 1)

        # Check that the moved long-term memory contains the correct triple
        found_memory = False
        for subj, pred, obj, qualifiers in long_term_memories.iterate_memories():
            if (subj, pred, obj) == self.short_term_triplet_1:
                found_memory = True
        self.assertTrue(
            found_memory, "Moved short-term memory was not found in long-term memory."
        )

    def test_clear_short_term_memories(self):
        """
        Test that all short-term memories are cleared after calling clear_short_term_memories.
        """
        # Ensure there are initially 2 short-term memories
        short_term_memories = self.memory_system.memory.get_short_term_memories()
        self.assertEqual(short_term_memories.get_memory_count(), 2)

        # Clear all short-term memories
        self.memory_system.clear_short_term_memories()

        # Check that there are no short-term memories remaining
        short_term_memories = self.memory_system.memory.get_short_term_memories()
        self.assertEqual(short_term_memories.get_memory_count(), 0)

        # Ensure long-term memory is unaffected by clearing short-term memories
        long_term_memories = self.memory_system.memory.get_long_term_memories()
        self.assertEqual(long_term_memories.get_memory_count(), 0)


class TestMemorySystemMoveShortTermToLongTerm(unittest.TestCase):

    def setUp(self):
        """
        Set up the MemorySystem for testing with some initial short-term memories.
        """
        self.memory_system = MemorySystem()

        # Add a short-term memory to the memory system
        self.memory_system.memory.add_short_term_memory(
            [
                (
                    URIRef("https://example.org/Alice"),
                    URIRef("https://example.org/met"),
                    URIRef("https://example.org/Bob"),
                )
            ],
            qualifiers={
                humemai.location: Literal("Paris"),
                humemai.currentTime: Literal(
                    "2023-05-05T00:00:00", datatype=XSD.dateTime
                ),
            },
        )

        # Add another short-term memory
        self.memory_system.memory.add_short_term_memory(
            [
                (
                    URIRef("https://example.org/Charlie"),
                    URIRef("https://example.org/saw"),
                    URIRef("https://example.org/Alice"),
                )
            ],
            qualifiers={
                humemai.location: Literal("London"),
                humemai.currentTime: Literal(
                    "2023-05-06T00:00:00", datatype=XSD.dateTime
                ),
            },
        )

    def test_move_short_term_to_long_term_episodic(self):
        """
        Test moving a short-term memory to long-term episodic memory with emotion and event qualifiers.
        """
        # Move short-term memory to long-term episodic memory
        self.memory_system.move_short_term_to_episodic(
            memory_id_to_move=Literal(0),
            qualifiers={
                humemai.emotion: Literal("excited"),
                humemai.event: Literal("AI Conference"),
            },
        )

        # Check that the memory was moved to long-term and has correct qualifiers
        long_term_memories = self.memory_system.memory.get_long_term_memories()
        episodic_memories = list(
            self.memory_system.memory.iterate_memories(memory_type="episodic")
        )

        # Assert that the long-term memory contains the correct triple and qualifiers
        self.assertEqual(len(episodic_memories), 1)
        subj, pred, obj, qualifiers = episodic_memories[0]
        self.assertEqual(subj, URIRef("https://example.org/Alice"))
        self.assertEqual(pred, URIRef("https://example.org/met"))
        self.assertEqual(obj, URIRef("https://example.org/Bob"))
        self.assertEqual(qualifiers.get(humemai.location), Literal("Paris"))
        self.assertEqual(
            qualifiers.get(humemai.eventTime),
            Literal("2023-05-05T00:00:00", datatype=XSD.dateTime),
        )
        self.assertEqual(qualifiers.get(humemai.emotion), Literal("excited"))
        self.assertEqual(qualifiers.get(humemai.event), Literal("AI Conference"))

    def test_move_short_term_to_long_term_semantic(self):
        """
        Test moving a short-term memory to long-term semantic memory with strength and derivedFrom qualifiers.
        """
        # Move short-term memory to long-term semantic memory
        self.memory_system.move_short_term_to_semantic(
            memory_id_to_move=Literal(1),
            qualifiers={
                humemai.strength: Literal(5),
                humemai.derivedFrom: Literal("Observation"),
            },
        )

        # Check that the memory was moved to long-term and has correct qualifiers
        semantic_memories = list(
            self.memory_system.memory.iterate_memories(memory_type="semantic")
        )

        # Assert that the long-term memory contains the correct triple and qualifiers
        self.assertEqual(len(semantic_memories), 1)
        subj, pred, obj, qualifiers = semantic_memories[0]
        self.assertEqual(subj, URIRef("https://example.org/Charlie"))
        self.assertEqual(pred, URIRef("https://example.org/saw"))
        self.assertEqual(obj, URIRef("https://example.org/Alice"))
        self.assertEqual(qualifiers.get(humemai.strength), Literal(5))
        self.assertEqual(qualifiers.get(humemai.derivedFrom), Literal("Observation"))
