# HumemAI Python SDK

HumemAI is a Python SDK for interacting with an AI memory system that supports both episodic and semantic databases. This SDK provides a simple and intuitive interface for storing, querying, and managing AI memories.

## Features

- **Simple API**: Easy-to-use client interface for memory operations
- **Dual Memory Types**: Support for both episodic and semantic memory databases
- **Authentication**: Built-in API key authentication
- **File Upload**: Upload documents and data files for processing
- **Flexible Querying**: Query memories with filters and limits
- **Type Hints**: Full type annotations for better IDE support

## Installation

Install the package using pip:

```bash
pip install humemai
```

Or install from source:

```bash
git clone https://github.com/humemai/humemai.git
cd humemai
pip install -e .
```

## Quick Start

### Basic Usage

```python
from humemai import Client

# Initialize the client
client = Client(
    api_url="https://api.humemai.com",
    api_key="your-api-key-here"
)

# Insert a memory
response = client.insert_memory(
    content="Attended team standup meeting at 9 AM",
    memory_type="episodic",
    metadata={"date": "2025-01-15", "participants": ["Alice", "Bob", "Charlie"]},
    tags=["meeting", "team", "standup"]
)
print(f"Memory inserted: {response}")

# Query memories
results = client.query_memory(
    query="team meetings",
    memory_type="episodic",
    limit=5
)
print(f"Found {len(results.get('memories', []))} memories")

# Upload a document
upload_response = client.upload_data(
    file_path="/path/to/document.pdf",
    data_type="document",
    metadata={"source": "research_papers", "category": "AI"}
)
print(f"Upload status: {upload_response}")
```

### Using Context Manager

```python
from humemai import Client

# Use context manager for automatic cleanup
with Client(api_url="https://api.humemai.com", api_key="your-api-key") as client:
    # Insert semantic knowledge
    client.insert_memory(
        content="Python is a high-level programming language",
        memory_type="semantic",
        tags=["programming", "python", "knowledge"]
    )
    
    # Query semantic memories
    results = client.query_memory(
        query="programming languages",
        memory_type="semantic"
    )
```

## API Reference

### Client

Initialize the HumemAI client:

```python
Client(api_url: str, api_key: Optional[str] = None, timeout: int = 30)
```

**Parameters:**
- `api_url`: The base URL of the HumemAI API
- `api_key`: Optional API key for authentication
- `timeout`: Request timeout in seconds (default: 30)

### Methods

#### insert_memory()

Insert a new memory into the database.

```python
client.insert_memory(
    content: str,
    memory_type: str = "episodic",
    metadata: Optional[Dict[str, Any]] = None,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `content`: The content of the memory to store
- `memory_type`: Type of memory - "episodic" or "semantic" (default: "episodic")
- `metadata`: Optional metadata associated with the memory
- `tags`: Optional list of tags for categorization

**Returns:** Response from the API containing the inserted memory details

#### query_memory()

Query memories from the database.

```python
client.query_memory(
    query: str,
    memory_type: Optional[str] = None,
    limit: int = 10,
    filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `query`: Search query string
- `memory_type`: Optional filter by memory type ("episodic" or "semantic")
- `limit`: Maximum number of results to return (default: 10)
- `filters`: Optional additional filters to apply

**Returns:** Response from the API containing matching memories

#### upload_data()

Upload data file to be processed and stored as memories.

```python
client.upload_data(
    file_path: str,
    data_type: str = "document",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `file_path`: Path to the file to upload
- `data_type`: Type of data being uploaded (default: "document")
- `metadata`: Optional metadata to associate with the uploaded data

**Returns:** Response from the API containing upload status and processing details

#### get_memory()

Retrieve a specific memory by ID.

```python
client.get_memory(memory_id: str) -> Dict[str, Any]
```

**Parameters:**
- `memory_id`: The unique identifier of the memory

**Returns:** Response from the API containing the memory details

#### delete_memory()

Delete a specific memory by ID.

```python
client.delete_memory(memory_id: str) -> Dict[str, Any]
```

**Parameters:**
- `memory_id`: The unique identifier of the memory to delete

**Returns:** Response from the API confirming deletion

## Examples

### Store Episodic Memories

```python
from humemai import Client

client = Client(api_url="https://api.humemai.com", api_key="your-api-key")

# Store a meeting memory
client.insert_memory(
    content="Discussed Q4 roadmap with product team",
    memory_type="episodic",
    metadata={
        "date": "2025-01-15",
        "time": "14:00",
        "location": "Conference Room A",
        "participants": ["Alice", "Bob", "Carol"]
    },
    tags=["meeting", "roadmap", "Q4"]
)
```

### Store Semantic Knowledge

```python
# Store factual knowledge
client.insert_memory(
    content="Machine learning is a subset of artificial intelligence",
    memory_type="semantic",
    metadata={
        "domain": "computer_science",
        "topic": "AI"
    },
    tags=["AI", "machine-learning", "knowledge"]
)
```

### Search and Filter

```python
# Search with filters
results = client.query_memory(
    query="product roadmap",
    memory_type="episodic",
    limit=10,
    filters={
        "tags": ["roadmap"],
        "metadata.date": {"$gte": "2025-01-01"}
    }
)

for memory in results.get('memories', []):
    print(f"- {memory['content']}")
```

### Batch Operations

```python
# Insert multiple memories
memories = [
    "Completed code review for PR #123",
    "Fixed bug in authentication module",
    "Updated documentation for API endpoints"
]

for content in memories:
    client.insert_memory(
        content=content,
        memory_type="episodic",
        tags=["development"]
    )
```

## Error Handling

The SDK provides custom exception classes for better error handling:

- `HumemAIError`: Base exception for all SDK errors
- `APIError`: Raised for API-related errors (network issues, server errors, etc.)
- `FileUploadError`: Raised for file upload errors

```python
from humemai import Client, APIError, FileUploadError

client = Client(api_url="https://api.humemai.com", api_key="your-api-key")

# Handle API errors
try:
    result = client.insert_memory(
        content="Important memory",
        memory_type="episodic"
    )
except APIError as e:
    print(f"API error: {e}")

# Handle file upload errors
try:
    client.upload_data(file_path="/path/to/file.pdf")
except FileNotFoundError:
    print("File not found")
except PermissionError:
    print("Permission denied")
except FileUploadError as e:
    print(f"Upload error: {e}")
```

## Development

### Running Tests

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=humemai
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions, please open an issue on [GitHub](https://github.com/humemai/humemai/issues).
