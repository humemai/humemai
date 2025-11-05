"""HumemAI Client for interacting with the memory API."""

import json
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    requests = None


class HumemAIError(Exception):
    """Base exception for HumemAI SDK errors."""
    pass


class APIError(HumemAIError):
    """Exception raised for API-related errors."""
    pass


class FileUploadError(HumemAIError):
    """Exception raised for file upload errors."""
    pass


class Client:
    """Client for interacting with HumemAI memory system.
    
    This client provides methods to interact with an AI memory system that supports
    both episodic and semantic databases.
    
    Args:
        api_url: The base URL of the HumemAI API
        api_key: Optional API key for authentication
        timeout: Request timeout in seconds (default: 30)
    
    Example:
        >>> client = Client(api_url="https://api.humemai.com", api_key="your-api-key")
        >>> client.insert_memory(content="Meeting with team", memory_type="episodic")
        >>> results = client.query_memory(query="team meetings")
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """Initialize the HumemAI client.
        
        Args:
            api_url: The base URL of the HumemAI API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 30)
        
        Raises:
            ImportError: If requests library is not installed
        """
        if requests is None:
            raise ImportError(
                "The 'requests' library is required to use HumemAI SDK. "
                "Install it with: pip install requests"
            )
        
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        
        # Set up authentication headers
        if self.api_key:
            self._session.headers.update({
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            })
        else:
            self._session.headers.update({
                'Content-Type': 'application/json'
            })
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to the API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Optional data to send in the request body
            files: Optional files to upload
        
        Returns:
            Response data as a dictionary
        
        Raises:
            APIError: If the request fails
        """
        url = urljoin(self.api_url + '/', endpoint.lstrip('/'))
        
        headers = dict(self._session.headers)
        
        try:
            if files:
                # For file uploads, remove Content-Type to let requests set it
                headers.pop('Content-Type', None)
                response = self._session.request(
                    method=method,
                    url=url,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=self.timeout
                )
            else:
                response = self._session.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers,
                    timeout=self.timeout
                )
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                return response.json()
            except json.JSONDecodeError:
                return {'status': 'success', 'data': response.text}
                
        except requests.exceptions.RequestException as e:
            raise APIError(f"API request failed: {str(e)}") from e
    
    def insert_memory(
        self,
        content: str,
        memory_type: str = "episodic",
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Insert a new memory into the database.
        
        Args:
            content: The content of the memory to store
            memory_type: Type of memory - "episodic" or "semantic" (default: "episodic")
            metadata: Optional metadata associated with the memory
            tags: Optional list of tags for categorization
        
        Returns:
            Response from the API containing the inserted memory details
        
        Example:
            >>> client.insert_memory(
            ...     content="Attended team standup meeting",
            ...     memory_type="episodic",
            ...     metadata={"date": "2025-01-15", "participants": ["Alice", "Bob"]},
            ...     tags=["meeting", "team"]
            ... )
        """
        data = {
            'content': content,
            'memory_type': memory_type
        }
        
        if metadata:
            data['metadata'] = metadata
        
        if tags:
            data['tags'] = tags
        
        return self._make_request('POST', '/memories', data=data)
    
    def query_memory(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query memories from the database.
        
        Args:
            query: Search query string
            memory_type: Optional filter by memory type ("episodic" or "semantic")
            limit: Maximum number of results to return (default: 10)
            filters: Optional additional filters to apply
        
        Returns:
            Response from the API containing matching memories
        
        Example:
            >>> results = client.query_memory(
            ...     query="team meetings",
            ...     memory_type="episodic",
            ...     limit=5
            ... )
            >>> for memory in results.get('memories', []):
            ...     print(memory['content'])
        """
        data = {
            'query': query,
            'limit': limit
        }
        
        if memory_type:
            data['memory_type'] = memory_type
        
        if filters:
            data['filters'] = filters
        
        return self._make_request('POST', '/memories/query', data=data)
    
    def upload_data(
        self,
        file_path: str,
        data_type: str = "document",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Upload data file to be processed and stored as memories.
        
        Args:
            file_path: Path to the file to upload
            data_type: Type of data being uploaded (default: "document")
            metadata: Optional metadata to associate with the uploaded data
        
        Returns:
            Response from the API containing upload status and processing details
        
        Example:
            >>> client.upload_data(
            ...     file_path="/path/to/document.pdf",
            ...     data_type="document",
            ...     metadata={"source": "research_papers"}
            ... )
        
        Raises:
            FileNotFoundError: If the file does not exist
            PermissionError: If the file cannot be read due to permissions
            FileUploadError: If the upload fails
        """
        try:
            with open(file_path, 'rb') as f:
                files = {'file': f}
                data = {'data_type': data_type}
                
                if metadata:
                    data['metadata'] = json.dumps(metadata)
                
                return self._make_request('POST', '/upload', data=data, files=files)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except PermissionError:
            raise PermissionError(f"Permission denied reading file: {file_path}")
        except APIError:
            raise
        except Exception as e:
            raise FileUploadError(f"Failed to upload file: {str(e)}") from e
    
    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """Retrieve a specific memory by ID.
        
        Args:
            memory_id: The unique identifier of the memory
        
        Returns:
            Response from the API containing the memory details
        
        Example:
            >>> memory = client.get_memory(memory_id="mem_123456")
            >>> print(memory['content'])
        """
        return self._make_request('GET', f'/memories/{memory_id}')
    
    def delete_memory(self, memory_id: str) -> Dict[str, Any]:
        """Delete a specific memory by ID.
        
        Args:
            memory_id: The unique identifier of the memory to delete
        
        Returns:
            Response from the API confirming deletion
        
        Example:
            >>> client.delete_memory(memory_id="mem_123456")
        """
        return self._make_request('DELETE', f'/memories/{memory_id}')
    
    def close(self):
        """Close the HTTP session."""
        if self._session:
            self._session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
