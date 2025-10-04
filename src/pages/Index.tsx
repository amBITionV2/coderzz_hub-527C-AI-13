import { Sidebar } from "@/components/Sidebar";
import { MapView } from "@/components/MapView";
import { ChatbotPanel } from "@/components/ChatbotPanel";

const Index = () => {
  return (
    <div className="flex w-full h-screen overflow-hidden bg-background">
      <Sidebar />
      <MapView />
      <ChatbotPanel />
    </div>
  );
};

export default Index;
