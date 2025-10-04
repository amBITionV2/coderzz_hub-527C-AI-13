import { useState, useEffect } from 'react';

export const ApiTest = () => {
  const [status, setStatus] = useState<string>('Testing...');
  const [apiUrl, setApiUrl] = useState<string>('');

  useEffect(() => {
    // Check environment variables
    const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    setApiUrl(url);
    
    // Test API connection
    testApi();
  }, []);

  const testApi = async () => {
    try {
      const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      console.log('Testing API at:', url);
      
      const response = await fetch(`${url}/health`);
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('API Response:', data);
      
      setStatus(`✅ API Connected: ${data.status} (${data.version})`);
    } catch (error) {
      console.error('API Test Error:', error);
      setStatus(`❌ API Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const testFloatsEndpoint = async () => {
    try {
      const url = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      console.log('Testing floats endpoint at:', url);
      
      const response = await fetch(`${url}/api/v1/floats?size=5`);
      console.log('Floats response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log('Floats data:', data);
      
      setStatus(`✅ Floats API: Found ${data.total} floats, showing ${data.items.length}`);
    } catch (error) {
      console.error('Floats API Test Error:', error);
      setStatus(`❌ Floats API Error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  return (
    <div className="p-6 bg-gray-800 border border-gray-600 rounded-lg text-white">
      <h2 className="text-xl font-bold mb-4">API Connection Test</h2>
      
      <div className="space-y-4">
        <div>
          <strong>API URL:</strong> {apiUrl}
        </div>
        
        <div>
          <strong>Status:</strong> {status}
        </div>
        
        <div className="flex gap-2">
          <button 
            onClick={testApi} 
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white"
          >
            Test Health
          </button>
          <button 
            onClick={testFloatsEndpoint}
            className="px-4 py-2 bg-green-600 hover:bg-green-700 rounded text-white"
          >
            Test Floats
          </button>
        </div>
        
        <div className="text-sm text-gray-400">
          Check browser console for detailed logs
        </div>
      </div>
    </div>
  );
};
