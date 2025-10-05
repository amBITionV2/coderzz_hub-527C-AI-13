import { useState, useEffect } from "react";
import { Activity, AlertTriangle, Power, Loader2, RefreshCw, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { MapContainer, TileLayer, CircleMarker, Popup } from "react-leaflet";
import { Alert, AlertDescription } from "@/components/ui/alert";
import "leaflet/dist/leaflet.css";
import { LatLngTuple } from "leaflet";
import { fetchFloats, FloatSummary, APIError } from "@/lib/api";
import { useHighlight } from "@/contexts/HighlightContext";

interface MapViewProps {
  onFloatClick?: (floatId: number) => void;
}

export const MapView = ({ onFloatClick }: MapViewProps) => {
  const [floats, setFloats] = useState<FloatSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFloats, setSelectedFloats] = useState<number[]>([]);
  const { highlightedFloats } = useHighlight();

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
          <div className="ml-auto text-sm text-muted-foreground">
            Displaying {selectedFloats.length > 0 ? selectedFloats.length : floats.length} of {floats.length} floats
          </div>
        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 relative overflow-hidden" style={{ minHeight: '500px' }}>
        {/* Highlighted Floats Indicator */}
        {highlightedFloats.length > 0 && (
          <div className="absolute top-6 left-6 z-[1000]">
            <div className="bg-card/90 backdrop-blur-sm border border-cyan-500/30 rounded-lg p-3 shadow-lg">
              <span className="text-sm text-cyan-400 font-medium">
                🔆 {highlightedFloats.length} float{highlightedFloats.length !== 1 ? 's' : ''} highlighted
              </span>
            </div>
          </div>
        )}

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
              
              const isHighlighted = highlightedFloats.includes(float.id);
              const isSelected = selectedFloats.includes(float.id);
              
              return (
                <CircleMarker
                  key={float.id}
                  center={[float.latitude!, float.longitude!] as LatLngTuple}
                  radius={isHighlighted ? 8 : 5}
                  pathOptions={{
                    color: isHighlighted ? "#00ffff" : getStatusColor(float.status),
                    fillColor: isHighlighted ? "#00ffff" : getStatusColor(float.status),
                    fillOpacity: isHighlighted ? 0.9 : (isSelected ? 1.0 : 0.8),
                    weight: isHighlighted ? 4 : (isSelected ? 3 : 2),
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
      </div>
    </div>
  );
};
