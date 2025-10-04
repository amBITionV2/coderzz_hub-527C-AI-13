import { useState } from "react";
import { MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sidebar } from "@/components/Sidebar";
import { MapView } from "@/components/MapView";
import { ChatbotPanel } from "@/components/ChatbotPanel";
import { FloatDetail } from "@/components/FloatDetail";

const Index = () => {
  const [selectedFloatId, setSelectedFloatId] = useState<number | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="flex w-full h-screen overflow-hidden bg-background">
      <Sidebar />
      {selectedFloatId ? (
        <FloatDetail 
          floatId={selectedFloatId} 
          onClose={() => setSelectedFloatId(null)}
          onOpenChat={() => setIsChatOpen(true)}
        />
      ) : (
        <MapView onFloatClick={setSelectedFloatId} />
      )}
      
      {/* Floating Chat Button */}
      {!isChatOpen && (
        <Button
          onClick={() => setIsChatOpen(true)}
          className="fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg bg-primary hover:bg-primary/90"
          style={{ zIndex: 1000 }}
          size="icon"
        >
          <MessageCircle className="h-6 w-6" />
        </Button>
      )}
      
      {/* Slideable Chatbot Panel */}
      <ChatbotPanel isOpen={isChatOpen} onClose={() => setIsChatOpen(false)} />
    </div>
  );
};

export default Index;
