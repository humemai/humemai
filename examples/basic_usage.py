"""
Example usage of the HumemAI Python SDK

This example demonstrates how to use the HumemAI client to:
1. Insert episodic and semantic memories
2. Query memories from the database
3. Upload data files
4. Retrieve and delete specific memories
"""

from humemai import Client

def main():
    # Initialize the client
    # Replace with your actual API URL and key
    client = Client(
        api_url="https://api.humemai.com",
        api_key="your-api-key-here"
    )
    
    print("HumemAI SDK Example\n")
    print("=" * 50)
    
    # Example 1: Insert an episodic memory
    print("\n1. Inserting episodic memory...")
    episodic_response = client.insert_memory(
        content="Attended team standup meeting at 9 AM",
        memory_type="episodic",
        metadata={
            "date": "2025-01-15",
            "time": "09:00",
            "participants": ["Alice", "Bob", "Charlie"]
        },
        tags=["meeting", "team", "standup"]
    )
    print(f"   Response: {episodic_response}")
    
    # Example 2: Insert a semantic memory
    print("\n2. Inserting semantic memory...")
    semantic_response = client.insert_memory(
        content="Python is a high-level, interpreted programming language known for its simplicity",
        memory_type="semantic",
        metadata={
            "domain": "programming",
            "language": "python"
        },
        tags=["programming", "python", "knowledge"]
    )
    print(f"   Response: {semantic_response}")
    
    # Example 3: Query episodic memories
    print("\n3. Querying episodic memories...")
    query_results = client.query_memory(
        query="team meetings",
        memory_type="episodic",
        limit=5
    )
    print(f"   Found {len(query_results.get('memories', []))} memories")
    
    # Example 4: Query semantic memories
    print("\n4. Querying semantic memories...")
    semantic_results = client.query_memory(
        query="programming languages",
        memory_type="semantic",
        limit=5
    )
    print(f"   Found {len(semantic_results.get('memories', []))} memories")
    
    # Example 5: Upload a document (if you have a file)
    # Uncomment this section if you have a file to upload
    # print("\n5. Uploading document...")
    # try:
    #     upload_response = client.upload_data(
    #         file_path="/path/to/your/document.pdf",
    #         data_type="document",
    #         metadata={"source": "research_papers", "category": "AI"}
    #     )
    #     print(f"   Upload response: {upload_response}")
    # except FileNotFoundError:
    #     print("   File not found - skipping upload example")
    
    # Example 6: Context manager usage
    print("\n6. Using context manager...")
    with Client(api_url="https://api.humemai.com", api_key="your-api-key-here") as ctx_client:
        response = ctx_client.insert_memory(
            content="Context manager ensures proper cleanup",
            memory_type="episodic",
            tags=["example"]
        )
        print(f"   Response: {response}")
    print("   Session closed automatically")
    
    # Close the client
    client.close()
    print("\n" + "=" * 50)
    print("Example completed successfully!")


if __name__ == "__main__":
    main()
