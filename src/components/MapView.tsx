import { useState, useEffect } from "react";
import { Activity, AlertTriangle, Power, Loader2, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { Alert, AlertDescription } from "@/components/ui/alert";
import "leaflet/dist/leaflet.css";
import { LatLngTuple } from "leaflet";
import { fetchFloats, FloatSummary, APIError } from "@/lib/api";

interface MapViewProps {
  onFloatClick?: (floatId: number) => void;
}

export const MapView = ({ onFloatClick }: MapViewProps) => {
  const [floats, setFloats] = useState<FloatSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFloats, setSelectedFloats] = useState<number[]>([]);

  // Load float data on component mount
  useEffect(() => {
    loadFloats();
  }, []);

  const loadFloats = async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetchFloats({ size: 100 });
      setFloats(response.items);
    } catch (err) {
      console.error('Error loading floats:', err);
      setError(err instanceof APIError ? err.message : 'Failed to load float data');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active":
        return "#22c55e"; // green
      case "maintenance":
        return "#eab308"; // yellow
      case "inactive":
        return "#ef4444"; // red
      default:
        return "#6b7280"; // gray
    }
  };

  const getStatusCounts = () => {
    const counts = { active: 0, maintenance: 0, inactive: 0 };
    floats.forEach(float => {
      if (float.status in counts) {
        counts[float.status as keyof typeof counts]++;
      }
    });
    return counts;
  };

  const handleFloatClick = (floatId: number) => {
    if (onFloatClick) {
      onFloatClick(floatId);
    } else {
      setSelectedFloats(prev => 
        prev.includes(floatId) 
          ? prev.filter(id => id !== floatId)
          : [...prev, floatId]
      );
    }
  };

  const clearSelection = () => {
    setSelectedFloats([]);
  };

  const statusCounts = getStatusCounts();

  return (
    <div className="flex-1 flex flex-col bg-ocean-deep">
      {/* Top Bar */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground mb-2">Global Ocean Monitoring</h1>
            <p className="text-muted-foreground">
              Explore real-time oceanographic data from our worldwide float network
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              className="border-primary/30 text-primary hover:bg-primary/10"
              disabled={isLoading}
            >
              <Activity className="w-4 h-4 mr-2" />
              Active Floats ({statusCounts.active})
            </Button>
            <Button 
              onClick={loadFloats}
              disabled={isLoading}
              className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-glow-cyan"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              {isLoading ? 'Loading...' : 'Refresh Data'}
            </Button>
          </div>
        </div>

        {error && (
          <Alert className="mb-4">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={loadFloats} 
                className="ml-2"
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        )}

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-success" />
            <span className="text-sm font-medium text-success">{statusCounts.active} Active</span>
          </div>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning" />
            <span className="text-sm font-medium text-warning">{statusCounts.maintenance} Maintenance</span>
          </div>
          <div className="flex items-center gap-2">
            <Power className="w-4 h-4 text-destructive" />
            <span className="text-sm font-medium text-destructive">{statusCounts.inactive} Inactive</span>
          </div>
          <div className="ml-auto text-sm text-muted-foreground">
            Displaying {selectedFloats.length > 0 ? selectedFloats.length : floats.length} of {floats.length} floats
          </div>
        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 relative overflow-hidden" style={{ minHeight: '500px' }}>
        {/* Float Info Panel */}
        <div className="absolute top-6 left-6 z-[1000]">
          <div className="bg-card/90 backdrop-blur-sm border border-border rounded-lg p-4 shadow-lg max-w-sm">
            <div className="flex items-center gap-3 mb-3">
              <Activity className="w-5 h-5 text-primary" />
              <span className="text-sm font-semibold text-foreground">
                Float Positions ({floats.length} total)
              </span>
            </div>
            
            {selectedFloats.length > 0 && (
              <div className="mb-3 p-2 bg-primary/10 rounded">
                <span className="text-xs text-primary font-medium">
                  {selectedFloats.length} float{selectedFloats.length !== 1 ? 's' : ''} selected
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearSelection}
                  className="ml-2 h-6 px-2 text-xs border-primary/30 text-primary hover:bg-primary/10"
                >
                  Clear
                </Button>
              </div>
            )}
            
            <div className="text-xs text-muted-foreground space-y-1">
              <div>🌊 <strong>Map Center:</strong> 0°, 0° (Equator)</div>
              <div>🔍 <strong>Zoom:</strong> Global view (Level 2)</div>
              <div>📍 <strong>Markers:</strong> {floats.filter(f => f.latitude && f.longitude).length} positioned</div>
            </div>
            
            {floats.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/50">
                <div className="text-xs text-muted-foreground">
                  <strong>Sample Positions:</strong>
                </div>
                {floats.slice(0, 3).map(float => (
                  <div key={float.id} className="text-xs text-muted-foreground mt-1">
                    <span className="font-mono">
                      {float.wmo_id}: {float.latitude?.toFixed(1)}°, {float.longitude?.toFixed(1)}°
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Loading Overlay */}
        {isLoading && (
          <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-[1000] flex items-center justify-center">
            <div className="bg-card border border-border rounded-lg p-6 shadow-lg">
              <div className="flex items-center gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                <span className="text-sm font-medium">Loading float data...</span>
              </div>
            </div>
          </div>
        )}

        <MapContainer
          center={[0, 0] as LatLngTuple}
          zoom={2}
          className="w-full h-full"
          style={{ background: "hsl(var(--ocean-deep))" }}
          zoomControl={true}
          scrollWheelZoom={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
          />
          {floats
            .filter(float => 
              float.latitude !== null && 
              float.longitude !== null &&
              float.latitude >= -90 && 
              float.latitude <= 90 &&
              float.longitude >= -180 && 
              float.longitude <= 180
            )
            .map((float) => {
              // Debug logging for first few floats
              if (float.id <= 5) {
                console.log(`Float ${float.wmo_id}: ${float.latitude}, ${float.longitude} (${float.status})`);
              }
              
              return (
                <CircleMarker
                  key={float.id}
                  center={[float.latitude!, float.longitude!] as LatLngTuple}
                  radius={5}
                  pathOptions={{
                    color: getStatusColor(float.status),
                    fillColor: getStatusColor(float.status),
                    fillOpacity: selectedFloats.includes(float.id) ? 1.0 : 0.8,
                    weight: selectedFloats.includes(float.id) ? 3 : 2,
                    stroke: true,
                  }}
                  eventHandlers={{
                    click: () => handleFloatClick(float.id)
                  }}
                >
                  <Popup>
                    <div className="text-sm">
                      <p className="font-semibold">Float {float.wmo_id}</p>
                      <p className="text-muted-foreground capitalize">{float.status}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        <strong>Coordinates:</strong><br/>
                        Lat: {float.latitude!.toFixed(4)}°<br/>
                        Lon: {float.longitude!.toFixed(4)}°
                      </p>
                      {float.latest_profile_date && (
                        <p className="text-xs text-muted-foreground mt-1">
                          <strong>Last update:</strong><br/>
                          {new Date(float.latest_profile_date).toLocaleDateString()}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        <strong>Profiles:</strong> {float.profile_count}
                      </p>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
        </MapContainer>

        {/* Legend */}
        <div className="absolute bottom-6 left-6 z-[1000] bg-card/90 backdrop-blur-sm border border-border rounded-lg p-4 shadow-lg">
          <h3 className="text-sm font-semibold text-foreground mb-3">Float Status</h3>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-success" />
              <span className="text-xs text-foreground">Active</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-warning" />
              <span className="text-xs text-foreground">Maintenance</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-destructive" />
              <span className="text-xs text-foreground">Inactive</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
