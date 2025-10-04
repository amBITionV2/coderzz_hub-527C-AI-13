import { useState, useEffect } from "react";
import { ArrowLeft, Activity, Droplets, Wind, TrendingUp, Calendar } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { fetchFloatDetail, FloatDetail as FloatDetailType } from "@/lib/api";

interface FloatDetailProps {
  floatId: number;
  onClose: () => void;
}

export const FloatDetail = ({ floatId, onClose }: FloatDetailProps) => {
  const [floatData, setFloatData] = useState<FloatDetailType | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedProfile, setSelectedProfile] = useState(0);

  useEffect(() => {
    loadFloatDetail();
  }, [floatId]);

  const loadFloatDetail = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchFloatDetail(floatId);
      setFloatData(data);
      setSelectedProfile(0);
    } catch (err) {
      console.error('Error loading float detail:', err);
      setError('Failed to load float details');
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-400 mx-auto mb-4"></div>
          <p className="text-slate-400">Loading float data...</p>
        </div>
      </div>
    );
  }

  if (error || !floatData) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error || 'Float not found'}</p>
          <Button onClick={onClose} variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Map
          </Button>
        </div>
      </div>
    );
  }

  const profile = floatData.profiles[selectedProfile];
  
  // Prepare chart data for Temperature vs Depth
  const tempDepthData = profile?.measurements
    ?.filter(m => m.temperature !== null && m.depth !== null)
    .map(m => ({
      depth: m.depth,
      temperature: m.temperature,
    }))
    .sort((a, b) => a.depth - b.depth) || [];

  // Prepare chart data for Salinity vs Depth
  const salinityDepthData = profile?.measurements
    ?.filter(m => m.salinity !== null && m.depth !== null)
    .map(m => ({
      depth: m.depth,
      salinity: m.salinity,
    }))
    .sort((a, b) => a.depth - b.depth) || [];

  // Prepare chart data for Dissolved Oxygen vs Depth
  const oxygenDepthData = profile?.measurements
    ?.filter(m => m.dissolved_oxygen !== null && m.depth !== null)
    .map(m => ({
      depth: m.depth,
      oxygen: m.dissolved_oxygen,
    }))
    .sort((a, b) => a.depth - b.depth) || [];

  // Prepare surface data over time (from all profiles)
  const surfaceData = floatData.profiles
    .filter(p => p.measurements && p.measurements.length > 0)
    .map(p => {
      const surfaceMeasurement = p.measurements[0]; // First measurement is surface
      return {
        time: new Date(p.timestamp).toLocaleDateString(),
        temperature: surfaceMeasurement.temperature,
        salinity: surfaceMeasurement.salinity,
      };
    })
    .filter(d => d.temperature !== null || d.salinity !== null);

  const getStatusBadge = (status: string) => {
    const styles = {
      active: "bg-green-500/20 text-green-400 border-green-500/50",
      maintenance: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50",
      inactive: "bg-red-500/20 text-red-400 border-red-500/50",
    };
    return styles[status as keyof typeof styles] || styles.active;
  };

  // Calculate performance score (based on data quality and recency)
  const calculatePerformance = () => {
    if (!floatData.profiles.length) return 0;
    const daysSinceUpdate = Math.floor(
      (Date.now() - new Date(floatData.last_update || Date.now()).getTime()) / (1000 * 60 * 60 * 24)
    );
    const recencyScore = Math.max(0, 100 - daysSinceUpdate);
    return Math.min(100, Math.round(recencyScore));
  };

  // Calculate data quality (based on measurement completeness)
  const calculateDataQuality = () => {
    if (!profile?.measurements?.length) return 0;
    const validMeasurements = profile.measurements.filter(
      m => m.temperature !== null && m.salinity !== null
    ).length;
    return Math.round((validMeasurements / profile.measurements.length) * 100);
  };

  return (
    <div className="h-full bg-slate-900 text-white overflow-y-auto">
      {/* Header */}
      <div className="bg-gradient-to-r from-slate-800 to-slate-900 border-b border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <Button onClick={onClose} variant="ghost" size="sm" className="text-slate-400 hover:text-white">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <Button size="sm" className="bg-cyan-500 hover:bg-cyan-600">
            Live Mode
          </Button>
        </div>

        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold mb-2">Monsoon Tracker</h1>
            <p className="text-slate-400">
              WMO ID: {floatData.wmo_id} • {floatData.institution || 'Unknown Institution'}
            </p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-4 p-6">
        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="text-sm text-slate-400 mb-1">Status</div>
          <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-medium ${getStatusBadge(floatData.status)}`}>
            <Activity className="h-3 w-3" />
            {floatData.status.charAt(0).toUpperCase() + floatData.status.slice(1)}
          </div>
        </Card>

        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="text-sm text-slate-400 mb-1">Performance</div>
          <div className="text-2xl font-bold text-white">{calculatePerformance()}/100</div>
        </Card>

        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="text-sm text-slate-400 mb-1">Data Quality</div>
          <div className="flex items-center gap-2">
            <div className="text-lg font-bold text-cyan-400">Good</div>
            <div className="text-sm text-slate-400">{calculateDataQuality()}%</div>
          </div>
        </Card>

        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="text-sm text-slate-400 mb-1">Real-time Trends</div>
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-green-400" />
            <div className="text-sm">Temp: ↑</div>
            <div className="text-sm">Sal: →</div>
          </div>
        </Card>
      </div>

      {/* Profile Explorer */}
      <div className="px-6 mb-6">
        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Historical Profile Explorer</h3>
            <div className="text-sm text-slate-400">
              {floatData.profiles.length > 0 && (
                <>Profile: <span className="text-cyan-400">{selectedProfile + 1}</span> of {floatData.profiles.length}</>
              )}
            </div>
          </div>

          {/* Profile Timeline */}
          <div className="flex items-center gap-2 mb-4">
            <Calendar className="h-4 w-4 text-slate-400" />
            <div className="flex-1 flex gap-1">
              {floatData.profiles.slice(0, 30).map((p, idx) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedProfile(idx)}
                  className={`flex-1 h-2 rounded-full transition-all ${
                    idx === selectedProfile
                      ? 'bg-cyan-400'
                      : 'bg-slate-600 hover:bg-slate-500'
                  }`}
                  title={`Profile ${idx + 1} - ${new Date(p.timestamp).toLocaleDateString()}`}
                />
              ))}
            </div>
          </div>

          {profile && (
            <div className="text-sm text-slate-400">
              Showing profile {selectedProfile + 1} of {floatData.profiles.length} • 
              Live date: {new Date(profile.timestamp).toLocaleString()}
            </div>
          )}
        </Card>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-2 gap-6 px-6 pb-6">
        {/* Temperature Profile */}
        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-2 w-2 rounded-full bg-red-400"></div>
            <h3 className="font-semibold">Temperature Profile</h3>
          </div>
          <div className="text-sm text-slate-400 mb-4">Temperature (°C) vs Depth (m)</div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={tempDepthData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                type="number"
                dataKey="temperature" 
                stroke="#94a3b8"
                label={{ value: 'Temperature (°C)', position: 'insideBottom', offset: -5, fill: '#94a3b8' }}
              />
              <YAxis 
                type="number"
                dataKey="depth" 
                stroke="#94a3b8"
                reversed
                label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Line 
                type="monotone" 
                dataKey="temperature" 
                stroke="#ef4444" 
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Salinity Profile */}
        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-2 w-2 rounded-full bg-cyan-400"></div>
            <h3 className="font-semibold">Salinity Profile</h3>
          </div>
          <div className="text-sm text-slate-400 mb-4">Salinity (PSU) vs Depth (m)</div>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={salinityDepthData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis 
                type="number"
                dataKey="salinity" 
                stroke="#94a3b8"
                label={{ value: 'Salinity (PSU)', position: 'insideBottom', offset: -5, fill: '#94a3b8' }}
              />
              <YAxis 
                type="number"
                dataKey="depth" 
                stroke="#94a3b8"
                reversed
                label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
              />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Line 
                type="monotone" 
                dataKey="salinity" 
                stroke="#06b6d4" 
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Dissolved Oxygen Profile */}
        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-2 w-2 rounded-full bg-blue-400"></div>
            <h3 className="font-semibold">Dissolved Oxygen Profile</h3>
          </div>
          <div className="text-sm text-slate-400 mb-4">Dissolved Oxygen (mg/L) vs Depth (m)</div>
          {oxygenDepthData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={oxygenDepthData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  type="number"
                  dataKey="oxygen" 
                  stroke="#94a3b8"
                  label={{ value: 'Dissolved Oxygen (mg/L)', position: 'insideBottom', offset: -5, fill: '#94a3b8' }}
                />
                <YAxis 
                  type="number"
                  dataKey="depth" 
                  stroke="#94a3b8"
                  reversed
                  label={{ value: 'Depth (m)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="oxygen" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-slate-500">
              No dissolved oxygen data available
            </div>
          )}
        </Card>

        {/* Real-time Surface Data */}
        <Card className="bg-slate-800 border-slate-700 p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="h-2 w-2 rounded-full bg-green-400"></div>
            <h3 className="font-semibold">Real-time Surface Data</h3>
          </div>
          <div className="text-sm text-slate-400 mb-4">Real-time Surface Measurements</div>
          {surfaceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={surfaceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis 
                  dataKey="time" 
                  stroke="#94a3b8"
                  angle={-45}
                  textAnchor="end"
                  height={60}
                />
                <YAxis 
                  yAxisId="temp"
                  stroke="#ef4444"
                  label={{ value: 'Temperature (°C)', angle: -90, position: 'insideLeft', fill: '#ef4444' }}
                />
                <YAxis 
                  yAxisId="sal"
                  orientation="right"
                  stroke="#06b6d4"
                  label={{ value: 'Salinity (PSU)', angle: 90, position: 'insideRight', fill: '#06b6d4' }}
                />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Legend />
                <Line 
                  yAxisId="temp"
                  type="monotone" 
                  dataKey="temperature" 
                  stroke="#ef4444" 
                  strokeWidth={2}
                  name="Temperature"
                  dot={{ r: 3 }}
                />
                <Line 
                  yAxisId="sal"
                  type="monotone" 
                  dataKey="salinity" 
                  stroke="#06b6d4" 
                  strokeWidth={2}
                  name="Salinity"
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-slate-500">
              No surface data available
            </div>
          )}
        </Card>
      </div>

      {/* Additional Info */}
      <div className="px-6 pb-6">
        <Card className="bg-slate-800 border-slate-700 p-4">
          <h3 className="font-semibold mb-4">Float Information</h3>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-slate-400">Platform Type:</span>
              <span className="ml-2 text-white">{floatData.platform_type || 'N/A'}</span>
            </div>
            <div>
              <span className="text-slate-400">Project:</span>
              <span className="ml-2 text-white">{floatData.project_name || 'N/A'}</span>
            </div>
            <div>
              <span className="text-slate-400">Total Profiles:</span>
              <span className="ml-2 text-white">{floatData.profiles.length}</span>
            </div>
            <div>
              <span className="text-slate-400">Last Update:</span>
              <span className="ml-2 text-white">
                {floatData.last_update ? new Date(floatData.last_update).toLocaleDateString() : 'N/A'}
              </span>
            </div>
            {profile && (
              <>
                <div>
                  <span className="text-slate-400">Current Position:</span>
                  <span className="ml-2 text-white">
                    {profile.latitude.toFixed(4)}°, {profile.longitude.toFixed(4)}°
                  </span>
                </div>
                <div>
                  <span className="text-slate-400">Measurements:</span>
                  <span className="ml-2 text-white">{profile.measurements?.length || 0}</span>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
};
