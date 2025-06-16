import React, { useState, useEffect } from 'react';
import { RefreshCw, Download, Filter, Search, TrendingUp, AlertCircle, Calendar, DollarSign, Activity, BarChart3 } from 'lucide-react';

// Define the 'shape' of a Tender object for TypeScript
type Tender = {
  id: string;
  tender_id: string;
  title: string;
  organization: string;
  portal: string;
  value: number;
  closing_date: string;
  posted_date: string;
  description: string;
  location: string;
  categories: string[];
  keywords: string[];
  contact_email: string | null;
  contact_phone: string | null;
  tender_url: string;
  documents_url: string | null;
  priority: string;
  matching_courses: string[];
};

// Define the 'shape' of a Portal object
type Portal = {
  id: string;
  name: string;
};

// Define the shape of the Stats object
type Stats = {
    total_tenders: number;
    total_value: number;
    by_portal: { portal: string; count: number; value: number }[];
    by_category: { [key: string]: number };
    closing_soon: number;
    new_today: number;
    last_scan: string | null;
};

const ProcurementDashboard = () => {
  // Use the new types to define our state
  const [tenders, setTenders] = useState<Tender[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanningStatus, setScanningStatus] = useState('idle');
  const [stats, setStats] = useState<Stats>({
    total_tenders: 0,
    total_value: 0,
    by_portal: [],
    by_category: {},
    closing_soon: 0,
    new_today: 0,
    last_scan: null
  });
  const [filters, setFilters] = useState({
    portal: '',
    minValue: '',
    category: '',
    search: '',
    priority: ''
  });
  const [portals, setPortals] = useState<Portal[]>([]);
  const [selectedTender, setSelectedTender] = useState<Tender | null>(null);

  // Use environment variable or default to localhost for development
  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  // Fetch portals list
  const fetchPortals = async () => {
    try {
      const response = await fetch(`${API_BASE}/portals`);
      const data = await response.json();
      setPortals(data.portals || []);
    } catch (error) {
      console.error('Error fetching portals:', error);
    }
  };

  // Fetch tenders from API
  const fetchTenders = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: '0',
        limit: '100',
        ...(filters.portal && { portal: filters.portal }),
        ...(filters.minValue && { min_value: filters.minValue }),
        ...(filters.category && { category: filters.category }),
        ...(filters.search && { search: filters.search }),
        ...(filters.priority && { priority: filters.priority })
      });

      const response = await fetch(`${API_BASE}/tenders?${params}`);
      const data = await response.json();
      setTenders(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error fetching tenders:', error);
      setTenders([]);
    } finally {
      setLoading(false);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const response = await fetch(`${API_BASE}/stats`);
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  // Fetch tender details
  const fetchTenderDetails = async (tenderId: string) => {
    try {
      const response = await fetch(`${API_BASE}/tender/${tenderId}`);
      const data = await response.json();
      setSelectedTender(data);
    } catch (error) {
      console.error('Error fetching tender details:', error);
    }
  };

  // Trigger manual scan
  const triggerScan = async () => {
    try {
      setScanningStatus('scanning');
      await fetch(`${API_BASE}/scan`, { method: 'POST' });
      
      setTimeout(() => {
        setScanningStatus('updating');
      }, 3000);
      
      setTimeout(() => {
        fetchTenders();
        fetchStats();
        fetchPortals();
        setScanningStatus('complete');
        setTimeout(() => setScanningStatus('idle'), 3000);
      }, 10000);
    } catch (error) {
      console.error('Error triggering scan:', error);
      setScanningStatus('error');
      setTimeout(() => setScanningStatus('idle'), 3000);
    }
  };

  // Export to CSV
  const exportToCSV = () => {
    const csv = [
      ['ID', 'Title', 'Organization', 'Portal', 'Value', 'Closing Date', 'Location', 'Priority', 'Matching Courses', 'URL'],
      ...tenders.map(t => [
        t.tender_id,
        `"${t.title.replace(/"/g, '""')}"`,
        `"${t.organization.replace(/"/g, '""')}"`,
        t.portal,
        t.value,
        new Date(t.closing_date).toLocaleDateString(),
        t.location,
        t.priority,
        `"${t.matching_courses.join('; ')}"`,
        t.tender_url
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tenders_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  // Initial data load
  useEffect(() => {
    fetchPortals();
    fetchTenders();
    fetchStats();
    
    const interval = setInterval(() => {
      fetchTenders();
      fetchStats();
    }, 300000);
    
    return () => clearInterval(interval);
  }, []);

  // Refetch when filters change
  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      fetchTenders();
    }, 500);
    
    return () => clearTimeout(debounceTimer);
  }, [filters]);

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'border-red-500 bg-red-50';
      case 'medium': return 'border-yellow-500 bg-yellow-50';
      default: return 'border-gray-300 bg-gray-50';
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-CA', {
      style: 'currency',
      currency: 'CAD',
      minimumFractionDigits: 0
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-CA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const getScanStatusMessage = () => {
    switch (scanningStatus) {
      case 'scanning': return 'Scanning portals for new tenders...';
      case 'updating': return 'Processing and updating database...';
      case 'complete': return 'Scan completed successfully!';
      case 'error': return 'Error occurred during scan';
      default: return '';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">
                Canadian Procurement Intelligence Scanner
              </h1>
              <p className="text-gray-600 mt-2">
                Real-time monitoring of {portals.length} procurement portals across Canada
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={triggerScan}
                disabled={scanningStatus !== 'idle'}
                className={`flex items-center gap-2 px-4 py-2 rounded transition-colors ${
                  scanningStatus !== 'idle' 
                    ? 'bg-gray-400 text-gray-200 cursor-not-allowed' 
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                <RefreshCw className={`w-4 h-4 ${scanningStatus === 'scanning' ? 'animate-spin' : ''}`} />
                {scanningStatus === 'idle' ? 'Scan Now' : getScanStatusMessage()}
              </button>
              <button
                onClick={exportToCSV}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                <Download className="w-4 h-4" />
                Export CSV
              </button>
            </div>
          </div>
          
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Active Tenders</p>
                  <p className="text-2xl font-bold text-blue-600">{stats.total_tenders}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-blue-400" />
              </div>
            </div>
            <div className="bg-green-50 p-4 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Value</p>
                  <p className="text-2xl font-bold text-green-600">{formatCurrency(stats.total_value)}</p>
                </div>
                <DollarSign className="w-8 h-8 text-green-400" />
              </div>
            </div>
            <div className="bg-yellow-50 p-4 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Closing Soon</p>
                  <p className="text-2xl font-bold text-yellow-600">{stats.closing_soon}</p>
                  <p className="text-xs text-gray-500">Next 7 days</p>
                </div>
                <AlertCircle className="w-8 h-8 text-yellow-400" />
              </div>
            </div>
            <div className="bg-purple-50 p-4 rounded">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">New Today</p>
                  <p className="text-2xl font-bold text-purple-600">{stats.new_today}</p>
                  <p className="text-xs text-gray-500">
                    Last scan: {stats.last_scan ? new Date(stats.last_scan).toLocaleTimeString() : 'Never'}
                  </p>
                </div>
                <Activity className="w-8 h-8 text-purple-400" />
              </div>
            </div>
          </div>
        </div>

        {/* Portal Status */}
        {stats.by_portal.length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              Portal Activity
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {stats.by_portal.map(portal => (
                <div key={portal.portal} className="text-center p-3 bg-gray-50 rounded hover:bg-gray-100 transition-colors">
                  <p className="text-sm font-medium text-gray-700">{portal.portal}</p>
                  <p className="text-lg font-bold text-blue-600">{portal.count}</p>
                  <p className="text-xs text-gray-500">{formatCurrency(portal.value)}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Filter className="w-5 h-5" />
            Search & Filter
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="lg:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="Keywords, organization, title..."
                  className="w-full pl-10 pr-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={filters.search}
                  onChange={(e) => setFilters({...filters, search: e.target.value})}
                />
                <Search className="w-5 h-5 text-gray-400 absolute left-3 top-2.5" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Portal</label>
              <select
                className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={filters.portal}
                onChange={(e) => setFilters({...filters, portal: e.target.value})}
              >
                <option value="">All Portals</option>
                {portals.map(portal => (
                  <option key={portal.id} value={portal.name}>{portal.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Value</label>
              <input
                type="number"
                placeholder="0"
                className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={filters.minValue}
                onChange={(e) => setFilters({...filters, minValue: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                value={filters.category}
                onChange={(e) => setFilters({...filters, category: e.target.value})}
              >
                <option value="">All Categories</option>
                <option value="project-management">Project Management</option>
                <option value="it-technical">IT & Technical</option>
                <option value="leadership">Leadership</option>
                <option value="agile-scrum">Agile/Scrum</option>
                <option value="cybersecurity">Cybersecurity</option>
                <option value="data-analytics">Data Analytics</option>
                <option value="soft-skills">Soft Skills</option>
                <option value="compliance">Compliance</option>
              </select>
            </div>
          </div>
          <div className="mt-4 flex gap-2">
            <label className="flex items-center">
              <input
                type="radio"
                name="priority"
                value=""
                checked={filters.priority === ''}
                onChange={(e) => setFilters({...filters, priority: e.target.value})}
                className="mr-2"
              />
              All Priorities
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="priority"
                value="high"
                checked={filters.priority === 'high'}
                onChange={(e) => setFilters({...filters, priority: e.target.value})}
                className="mr-2"
              />
              <span className="text-red-600">High Priority</span>
            </label>
            <label className="flex items-center">
              <input
                type="radio"
                name="priority"
                value="medium"
                checked={filters.priority === 'medium'}
                onChange={(e) => setFilters({...filters, priority: e.target.value})}
                className="mr-2"
              />
              <span className="text-yellow-600">Medium Priority</span>
            </label>
          </div>
        </div>

        {/* Category Distribution */}
        {Object.keys(stats.by_category).length > 0 && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Category Distribution</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(stats.by_category).map(([category, count]) => (
                <div 
                  key={category} 
                  className="p-3 bg-gray-50 rounded cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => setFilters({...filters, category: category})}
                >
                  <p className="text-sm font-medium capitalize">{category.replace('-', ' ')}</p>
                  <p className="text-lg font-bold text-blue-600">{count as number}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tenders List */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">
            Active Tenders {tenders.length > 0 && `(${tenders.length})`}
          </h2>
          
          {loading ? (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-gray-600">Loading tenders...</p>
            </div>
          ) : tenders.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-600">No tenders found matching your criteria.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {tenders.map(tender => {
                const daysLeft = Math.ceil((new Date(tender.closing_date).getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24));
                const isClosingSoon = daysLeft <= 7 && daysLeft >= 0;
                const isExpired = daysLeft < 0;
                
                return (
                  <div
                    key={tender.id}
                    className={`border-l-4 p-4 rounded ${getPriorityColor(tender.priority)} transition-all hover:shadow-md cursor-pointer`}
                    onClick={() => fetchTenderDetails(tender.id)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-gray-800 hover:text-blue-600">
                          {tender.title}
                        </h3>
                        <p className="text-sm text-gray-600">
                          {tender.tender_id} | {tender.portal} | {tender.organization}
                        </p>
                        <p className="text-sm text-gray-500 mt-1">
                          <span className="inline-flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            {tender.location}
                          </span>
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-xl font-bold text-green-600">
                          {formatCurrency(tender.value)}
                        </p>
                        <p className={`text-sm ${isExpired ? 'text-gray-500 line-through' : isClosingSoon ? 'text-red-600 font-bold' : 'text-gray-600'}`}>
                          {isExpired ? 'Expired' : `Closes: ${formatDate(tender.closing_date)}`}
                          {!isExpired && ` (${daysLeft} days)`}
                        </p>
                      </div>
                    </div>
                    
                    {tender.description && (
                      <p className="text-gray-700 mb-3 line-clamp-2">{tender.description}</p>
                    )}
                    
                    {tender.matching_courses.length > 0 && (
                      <div className="mb-3">
                        <span className="text-sm font-medium text-gray-600">Matching TKA Courses: </span>
                        <div className="inline-flex flex-wrap gap-2 mt-1">
                          {tender.matching_courses.map((course, idx) => (
                            <span
                              key={idx}
                              className="inline-block px-2 py-1 text-xs bg-green-100 text-green-800 rounded"
                            >
                              {course}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div className="flex gap-2 mt-3">
                      <a
                        href={tender.tender_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                        onClick={(e) => e.stopPropagation()}
                      >
                        View on Portal
                      </a>
                      <button 
                        className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                        onClick={(e) => {
                          e.stopPropagation();
                          // Add to tracking functionality
                        }}
                      >
                        Track
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Tender Details Modal */}
        {selectedTender && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50" onClick={() => setSelectedTender(null)}>
            <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-2xl font-bold text-gray-800">{selectedTender.title}</h2>
                <button
                  onClick={() => setSelectedTender(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div>
                  <p className="text-sm text-gray-600">Tender ID</p>
                  <p className="font-semibold">{selectedTender.tender_id}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Organization</p>
                  <p className="font-semibold">{selectedTender.organization}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Portal</p>
                  <p className="font-semibold">{selectedTender.portal}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Location</p>
                  <p className="font-semibold">{selectedTender.location}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Value</p>
                  <p className="font-semibold text-green-600">{formatCurrency(selectedTender.value)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Priority</p>
                  <p className={`font-semibold ${
                    selectedTender.priority === 'high' ? 'text-red-600' : 
                    selectedTender.priority === 'medium' ? 'text-yellow-600' : 'text-gray-600'
                  }`}>
                    {selectedTender.priority.toUpperCase()}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Posted Date</p>
                  <p className="font-semibold">{formatDate(selectedTender.posted_date)}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Closing Date</p>
                  <p className="font-semibold">{formatDate(selectedTender.closing_date)}</p>
                </div>
              </div>
              
              {selectedTender.description && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-2">Description</h3>
                  <p className="text-gray-700 whitespace-pre-wrap">{selectedTender.description}</p>
                </div>
              )}
              
              {selectedTender.categories.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-2">Categories</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedTender.categories.map((cat, idx) => (
                      <span key={idx} className="px-3 py-1 bg-blue-100 text-blue-800 rounded">
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedTender.matching_courses.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-2">Matching TKA Courses</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedTender.matching_courses.map((course, idx) => (
                      <span key={idx} className="px-3 py-1 bg-green-100 text-green-800 rounded">
                        {course}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {(selectedTender.contact_email || selectedTender.contact_phone) && (
                <div className="mb-6">
                  <h3 className="text-lg font-semibold mb-2">Contact Information</h3>
                  {selectedTender.contact_email && <p>Email: {selectedTender.contact_email}</p>}
                  {selectedTender.contact_phone && <p>Phone: {selectedTender.contact_phone}</p>}
                </div>
              )}
              
              <div className="flex gap-3">
                <a
                  href={selectedTender.tender_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  View on Portal
                </a>
                {selectedTender.documents_url && (
                  <a
                    href={selectedTender.documents_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                  >
                    Download Documents
                  </a>
                )}
                <button
                  onClick={() => setSelectedTender(null)}
                  className="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ProcurementDashboard;