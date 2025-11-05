"""Tests for HumemAI SDK."""

import pytest
from unittest.mock import Mock, patch, mock_open
from humemai import Client


class TestClient:
    """Test cases for the Client class."""
    
    def test_client_initialization(self):
        """Test that client initializes correctly."""
        client = Client(api_url="https://api.example.com", api_key="test-key")
        assert client.api_url == "https://api.example.com"
        assert client.api_key == "test-key"
        assert client.timeout == 30
        assert client._session.headers['Authorization'] == 'Bearer test-key'
        assert client._session.headers['Content-Type'] == 'application/json'
        client.close()
    
    def test_client_initialization_without_api_key(self):
        """Test client initialization without API key."""
        client = Client(api_url="https://api.example.com")
        assert client.api_key is None
        assert 'Authorization' not in client._session.headers
        assert client._session.headers['Content-Type'] == 'application/json'
        client.close()
    
    def test_client_url_normalization(self):
        """Test that trailing slashes are removed from API URL."""
        client = Client(api_url="https://api.example.com/", api_key="test-key")
        assert client.api_url == "https://api.example.com"
        client.close()
    
    @patch('humemai.client.requests.Session.request')
    def test_insert_memory(self, mock_request):
        """Test insert_memory method."""
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'mem_123', 'status': 'success'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        client = Client(api_url="https://api.example.com", api_key="test-key")
        result = client.insert_memory(
            content="Test memory",
            memory_type="episodic",
            metadata={"key": "value"},
            tags=["tag1", "tag2"]
        )
        
        assert result['id'] == 'mem_123'
        assert result['status'] == 'success'
        
        # Verify the request was made correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert '/memories' in call_args[1]['url']
        assert call_args[1]['json']['content'] == "Test memory"
        assert call_args[1]['json']['memory_type'] == "episodic"
        assert call_args[1]['json']['metadata'] == {"key": "value"}
        assert call_args[1]['json']['tags'] == ["tag1", "tag2"]
        
        client.close()
    
    @patch('humemai.client.requests.Session.request')
    def test_query_memory(self, mock_request):
        """Test query_memory method."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'memories': [
                {'id': 'mem_1', 'content': 'Memory 1'},
                {'id': 'mem_2', 'content': 'Memory 2'}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        client = Client(api_url="https://api.example.com", api_key="test-key")
        result = client.query_memory(
            query="test query",
            memory_type="episodic",
            limit=5,
            filters={"key": "value"}
        )
        
        assert len(result['memories']) == 2
        assert result['memories'][0]['id'] == 'mem_1'
        
        # Verify the request
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert '/memories/query' in call_args[1]['url']
        assert call_args[1]['json']['query'] == "test query"
        assert call_args[1]['json']['memory_type'] == "episodic"
        assert call_args[1]['json']['limit'] == 5
        assert call_args[1]['json']['filters'] == {"key": "value"}
        
        client.close()
    
    @patch('humemai.client.requests.Session.request')
    @patch('builtins.open', new_callable=mock_open, read_data=b'file content')
    def test_upload_data(self, mock_file, mock_request):
        """Test upload_data method."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'uploaded', 'file_id': 'file_123'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        client = Client(api_url="https://api.example.com", api_key="test-key")
        result = client.upload_data(
            file_path="/path/to/file.pdf",
            data_type="document",
            metadata={"source": "test"}
        )
        
        assert result['status'] == 'uploaded'
        assert result['file_id'] == 'file_123'
        
        # Verify file was opened
        mock_file.assert_called_once_with("/path/to/file.pdf", 'rb')
        
        # Verify the request
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'POST'
        assert '/upload' in call_args[1]['url']
        
        client.close()
    
    @patch('humemai.client.requests.Session.request')
    def test_get_memory(self, mock_request):
        """Test get_memory method."""
        mock_response = Mock()
        mock_response.json.return_value = {'id': 'mem_123', 'content': 'Test memory'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        client = Client(api_url="https://api.example.com", api_key="test-key")
        result = client.get_memory(memory_id="mem_123")
        
        assert result['id'] == 'mem_123'
        assert result['content'] == 'Test memory'
        
        # Verify the request
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'GET'
        assert '/memories/mem_123' in call_args[1]['url']
        
        client.close()
    
    @patch('humemai.client.requests.Session.request')
    def test_delete_memory(self, mock_request):
        """Test delete_memory method."""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'deleted'}
        mock_response.raise_for_status = Mock()
        mock_request.return_value = mock_response
        
        client = Client(api_url="https://api.example.com", api_key="test-key")
        result = client.delete_memory(memory_id="mem_123")
        
        assert result['status'] == 'deleted'
        
        # Verify the request
        call_args = mock_request.call_args
        assert call_args[1]['method'] == 'DELETE'
        assert '/memories/mem_123' in call_args[1]['url']
        
        client.close()
    
    def test_context_manager(self):
        """Test that client works as context manager."""
        with Client(api_url="https://api.example.com", api_key="test-key") as client:
            assert client.api_url == "https://api.example.com"
        # Session should be closed after exiting context
    
    def test_upload_data_file_not_found(self):
        """Test upload_data with non-existent file."""
        client = Client(api_url="https://api.example.com", api_key="test-key")
        
        with pytest.raises(FileNotFoundError):
            client.upload_data(file_path="/nonexistent/file.pdf")
        
        client.close()
