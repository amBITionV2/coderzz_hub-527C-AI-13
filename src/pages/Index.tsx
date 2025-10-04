import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { MapView } from "@/components/MapView";
import { ChatbotPanel } from "@/components/ChatbotPanel";
import { FloatDetail } from "@/components/FloatDetail";

const Index = () => {
  const [selectedFloatId, setSelectedFloatId] = useState<number | null>(null);

  return (
    <div className="flex w-full h-screen overflow-hidden bg-background">
      <Sidebar />
      {selectedFloatId ? (
        <FloatDetail 
          floatId={selectedFloatId} 
          onClose={() => setSelectedFloatId(null)} 
        />
      ) : (
        <MapView onFloatClick={setSelectedFloatId} />
      )}
      <ChatbotPanel />
    </div>
  );
};

export default Index;
