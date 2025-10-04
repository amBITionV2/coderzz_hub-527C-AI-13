import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Activity, MapPin, Calendar, Thermometer, Droplets, Gauge, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fetchFloatById, FloatDetail, APIError } from "@/lib/api";

export const FloatDetailPage = () => {
  const { wmoId } = useParams<{ wmoId: string }>();
  const navigate = useNavigate();
  
  const [floatData, setFloatData] = useState<FloatDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (wmoId) {
      loadFloatData(wmoId);
    }
  }, [wmoId]);

  const loadFloatData = async (id: string) => {
    try {
      setIsLoading(true);
      setError(null);
      
      const data = await fetchFloatById(id);
      setFloatData(data);
    } catch (err) {
      console.error('Error loading float data:', err);
      setError(err instanceof APIError ? err.message : 'Failed to load float data');
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'active':
        return 'default';
      case 'maintenance':
        return 'secondary';
      case 'inactive':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getLatestProfile = () => {
    if (!floatData?.profiles || floatData.profiles.length === 0) return null;
    return floatData.profiles.reduce((latest, profile) => 
      new Date(profile.timestamp) > new Date(latest.timestamp) ? profile : latest
    );
  };

  const getProfileStats = () => {
    if (!floatData?.profiles) return { total: 0, withMeasurements: 0 };
    
    return {
      total: floatData.profiles.length,
      withMeasurements: floatData.profiles.filter(p => p.measurements.length > 0).length
    };
  };

  const getMeasurementStats = () => {
    if (!floatData?.profiles) return { total: 0, variables: {} };
    
    let total = 0;
    const variables: Record<string, number> = {};
    
    floatData.profiles.forEach(profile => {
      profile.measurements.forEach(measurement => {
        total++;
        if (measurement.temperature !== null) {
          variables.temperature = (variables.temperature || 0) + 1;
        }
        if (measurement.salinity !== null) {
          variables.salinity = (variables.salinity || 0) + 1;
        }
        if (measurement.dissolved_oxygen !== null) {
          variables.dissolved_oxygen = (variables.dissolved_oxygen || 0) + 1;
        }
      });
    });
    
    return { total, variables };
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
          <span className="text-lg">Loading float data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="max-w-4xl mx-auto">
          <Button 
            variant="ghost" 
            onClick={() => navigate(-1)}
            className="mb-6"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {error}
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => wmoId && loadFloatData(wmoId)} 
                className="ml-2"
              >
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  if (!floatData) {
    return (
      <div className="min-h-screen bg-background p-6">
        <div className="max-w-4xl mx-auto">
          <Button 
            variant="ghost" 
            onClick={() => navigate(-1)}
            className="mb-6"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back
          </Button>
          
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Float not found
            </AlertDescription>
          </Alert>
        </div>
      </div>
    );
  }

  const latestProfile = getLatestProfile();
  const profileStats = getProfileStats();
  const measurementStats = getMeasurementStats();

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              onClick={() => navigate(-1)}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            <div>
              <h1 className="text-3xl font-bold text-foreground">
                Float {floatData.wmo_id}
              </h1>
              <p className="text-muted-foreground">
                {floatData.institution} • {floatData.platform_type}
              </p>
            </div>
          </div>
          
          <Badge variant={getStatusBadgeVariant(floatData.status)}>
            {floatData.status.charAt(0).toUpperCase() + floatData.status.slice(1)}
          </Badge>
        </div>

        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Status</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold capitalize">{floatData.status}</div>
              <p className="text-xs text-muted-foreground">
                Last update: {floatData.last_update 
                  ? new Date(floatData.last_update).toLocaleDateString()
                  : 'Unknown'
                }
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Location</CardTitle>
              <MapPin className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {latestProfile 
                  ? `${latestProfile.latitude.toFixed(2)}°, ${latestProfile.longitude.toFixed(2)}°`
                  : 'Unknown'
                }
              </div>
              <p className="text-xs text-muted-foreground">
                {latestProfile 
                  ? `Updated ${new Date(latestProfile.timestamp).toLocaleDateString()}`
                  : 'No recent position'
                }
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Profiles</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{profileStats.total}</div>
              <p className="text-xs text-muted-foreground">
                {profileStats.withMeasurements} with measurements
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Measurements</CardTitle>
              <Gauge className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{measurementStats.total}</div>
              <p className="text-xs text-muted-foreground">
                {Object.keys(measurementStats.variables).length} variables
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Detailed Information */}
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="profiles">Profiles</TabsTrigger>
            <TabsTrigger value="measurements">Measurements</TabsTrigger>
            <TabsTrigger value="metadata">Metadata</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Float Information</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">WMO ID:</span>
                    <span className="font-mono">{floatData.wmo_id}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Platform:</span>
                    <span>{floatData.platform_type || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Institution:</span>
                    <span>{floatData.institution || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Project:</span>
                    <span>{floatData.project_name || 'Unknown'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">PI:</span>
                    <span>{floatData.pi_name || 'Unknown'}</span>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Data Summary</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Profiles:</span>
                    <span>{profileStats.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total Measurements:</span>
                    <span>{measurementStats.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Temperature:</span>
                    <span>{measurementStats.variables.temperature || 0} measurements</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Salinity:</span>
                    <span>{measurementStats.variables.salinity || 0} measurements</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Oxygen:</span>
                    <span>{measurementStats.variables.dissolved_oxygen || 0} measurements</span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="profiles" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Recent Profiles</CardTitle>
                <CardDescription>
                  Latest {Math.min(10, floatData.profiles.length)} profiles from this float
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {floatData.profiles
                    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
                    .slice(0, 10)
                    .map((profile) => (
                      <div key={profile.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <p className="font-medium">Cycle {profile.cycle_number}</p>
                          <p className="text-sm text-muted-foreground">
                            {profile.latitude.toFixed(2)}°, {profile.longitude.toFixed(2)}°
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-sm">{new Date(profile.timestamp).toLocaleDateString()}</p>
                          <p className="text-xs text-muted-foreground">
                            {profile.measurements.length} measurements
                          </p>
                        </div>
                      </div>
                    ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="measurements" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Measurement Variables</CardTitle>
                <CardDescription>
                  Available oceanographic variables from this float
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {Object.entries(measurementStats.variables).map(([variable, count]) => (
                    <div key={variable} className="p-4 border rounded-lg">
                      <div className="flex items-center gap-2 mb-2">
                        {variable === 'temperature' && <Thermometer className="w-4 h-4 text-orange-500" />}
                        {variable === 'salinity' && <Droplets className="w-4 h-4 text-blue-500" />}
                        {variable === 'dissolved_oxygen' && <Activity className="w-4 h-4 text-green-500" />}
                        <span className="font-medium capitalize">
                          {variable.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-2xl font-bold">{count}</p>
                      <p className="text-xs text-muted-foreground">measurements</p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="metadata" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Technical Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="font-medium mb-2">Deployment</h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Date:</span>
                        <span>{floatData.deployment_date 
                          ? new Date(floatData.deployment_date).toLocaleDateString()
                          : 'Unknown'
                        }</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Latitude:</span>
                        <span>{floatData.deployment_latitude?.toFixed(4) || 'Unknown'}°</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Longitude:</span>
                        <span>{floatData.deployment_longitude?.toFixed(4) || 'Unknown'}°</span>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h4 className="font-medium mb-2">System</h4>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Created:</span>
                        <span>{new Date(floatData.created_at).toLocaleDateString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Updated:</span>
                        <span>{new Date(floatData.updated_at).toLocaleDateString()}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-muted-foreground">Database ID:</span>
                        <span className="font-mono">{floatData.id}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default FloatDetailPage;
