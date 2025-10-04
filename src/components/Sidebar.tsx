import { useState, useEffect } from "react";
import { Waves, Activity, Droplets, MapPin, Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { fetchFloats, FloatSummary, APIError } from "@/lib/api";

export const Sidebar = () => {
  const [floats, setFloats] = useState<FloatSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      console.error('Error loading floats in sidebar:', err);
      setError(err instanceof APIError ? err.message : 'Failed to load float data');
    } finally {
      setIsLoading(false);
    }
  };

  // Calculate real statistics from API data
  const getFloatStats = () => {
    const activeFloats = floats.filter(f => f.status === 'active').length;
    const maintenanceFloats = floats.filter(f => f.status === 'maintenance').length;
    const inactiveFloats = floats.filter(f => f.status === 'inactive').length;
    
    return {
      active: activeFloats,
      maintenance: maintenanceFloats,
      inactive: inactiveFloats,
      total: floats.length,
      dataQuality: floats.length > 0 ? Math.round((activeFloats / floats.length) * 100) : 0
    };
  };

  // Calculate ocean regions from real coordinates
  const getOceanRegions = () => {
    const regions = {
      "North Pacific": 0,
      "South Pacific": 0,
      "North Atlantic": 0,
      "South Atlantic": 0,
      "Indian Ocean": 0,
      "Southern Ocean": 0
    };

    floats.forEach(float => {
      if (!float.latitude || !float.longitude) return;
      
      const lat = float.latitude;
      const lon = float.longitude;
      
      // Simple ocean region classification based on coordinates
      if (lon >= -180 && lon <= -80) {
        // Pacific
        if (lat >= 0) regions["North Pacific"]++;
        else regions["South Pacific"]++;
      } else if (lon >= -80 && lon <= 20) {
        // Atlantic
        if (lat >= 0) regions["North Atlantic"]++;
        else regions["South Atlantic"]++;
      } else if (lon >= 20 && lon <= 147) {
        // Indian Ocean
        regions["Indian Ocean"]++;
      } else {
        // Pacific (western)
        if (lat >= 0) regions["North Pacific"]++;
        else regions["South Pacific"]++;
      }
      
      // Southern Ocean (below 60°S)
      if (lat < -60) {
        regions["Southern Ocean"]++;
      }
    });

    return Object.entries(regions)
      .filter(([_, count]) => count > 0)
      .map(([name, count]) => ({ name, count }));
  };

  const stats = getFloatStats();
  const oceanRegions = getOceanRegions();

  return (
    <div className="w-80 bg-ocean-darker border-r border-border flex flex-col h-screen">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3 mb-2">
          <Waves className="w-8 h-8 text-primary" />
          <div>
            <h1 className="text-xl font-bold text-foreground">FloatChat</h1>
            <p className="text-xs text-muted-foreground">Oceanographic AI Explorer</p>
          </div>
        </div>
      </div>

      {/* User Profile */}
      <div className="px-6 py-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-primary text-sm font-semibold">M</span>
            </div>
            <span className="text-sm font-medium text-foreground">mainak2005ops</span>
          </div>
          <Badge variant="outline" className="text-xs border-primary/30 text-primary">
            Premium
          </Badge>
        </div>
      </div>

      {/* Statistics */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div>
          <h2 className="text-sm font-semibold text-foreground mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            Global Ocean Monitoring
          </h2>
          
          <Card className="p-4 bg-card border-border space-y-4">
            {isLoading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-primary mr-2" />
                <span className="text-sm text-muted-foreground">Loading...</span>
              </div>
            ) : error ? (
              <div className="text-center py-4">
                <span className="text-sm text-destructive">Failed to load data</span>
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Active Floats</span>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-success">{stats.active}</span>
                    <span className="text-sm text-muted-foreground">/</span>
                    <span className="text-sm text-muted-foreground">{stats.total}</span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Maintenance</span>
                  <span className="text-lg font-bold text-warning">{stats.maintenance}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Data Quality</span>
                  <span className="text-lg font-bold text-foreground">{stats.dataQuality}%</span>
                </div>
              </>
            )}
          </Card>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-primary" />
            Ocean Regions
          </h3>
          {isLoading ? (
            <Card className="p-3 bg-card border-border">
              <div className="flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-primary mr-2" />
                <span className="text-xs text-muted-foreground">Loading regions...</span>
              </div>
            </Card>
          ) : error ? (
            <Card className="p-3 bg-card border-border">
              <span className="text-xs text-destructive">Failed to load regions</span>
            </Card>
          ) : oceanRegions.length > 0 ? (
            <div className="space-y-2">
              {oceanRegions.map((region) => (
                <div
                  key={region.name}
                  className="flex items-center justify-between p-2 rounded-lg bg-secondary/30 hover:bg-secondary/50 transition-colors cursor-pointer"
                >
                  <span className="text-sm text-foreground">{region.name}</span>
                  <Badge variant="secondary" className="text-xs bg-primary/20 text-primary border-0">
                    {region.count}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <Card className="p-3 bg-card border-border">
              <span className="text-xs text-muted-foreground">No regional data available</span>
            </Card>
          )}
        </div>

        <div>
          <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
            <Droplets className="w-4 h-4 text-primary" />
            Float Status Summary
          </h3>
          <Card className="p-3 bg-card border-border">
            {isLoading ? (
              <div className="flex items-center justify-center">
                <Loader2 className="w-4 h-4 animate-spin text-primary mr-2" />
                <span className="text-xs text-muted-foreground">Loading...</span>
              </div>
            ) : error ? (
              <span className="text-xs text-destructive">Failed to load status</span>
            ) : (
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">🟢 Active</span>
                  <span className="text-xs font-medium text-success">{stats.active}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">🟡 Maintenance</span>
                  <span className="text-xs font-medium text-warning">{stats.maintenance}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-muted-foreground">🔴 Inactive</span>
                  <span className="text-xs font-medium text-destructive">{stats.inactive}</span>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};
