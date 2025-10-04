import { useState } from "react";
import { MessageCircle, Send, Sparkles, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { postQuery, AIQueryResponse, APIError } from "@/lib/api";

interface Message {
  id: number;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  data?: AIQueryResponse;
  error?: boolean;
}

export const ChatbotPanel = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "Hello! I'm FloatChat AI, your oceanographic assistant. How can I help you explore the ocean data today?",
      sender: "bot",
      timestamp: new Date(),
    },
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now(),
      text: inputValue.trim(),
      sender: "user",
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputValue.trim();
    setInputValue("");
    setIsLoading(true);

    try {
      // Call the real API
      const response = await postQuery(currentInput);
      
      // Create formatted bot response
      const botResponse: Message = {
        id: Date.now() + 1,
        text: formatAIResponse(response),
        sender: "bot",
        timestamp: new Date(),
        data: response,
      };

      setMessages(prev => [...prev, botResponse]);
    } catch (error) {
      console.error('API Error:', error);
      
      const errorMessage: Message = {
        id: Date.now() + 1,
        text: error instanceof APIError 
          ? `Sorry, I encountered an error: ${error.message}`
          : "I'm having trouble connecting to the ocean data service. Please try again later.",
        sender: "bot",
        timestamp: new Date(),
        error: true,
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatAIResponse = (response: AIQueryResponse): string => {
    let formattedText = `🌊 **Query Results**\n\n`;
    
    formattedText += `**Found ${response.floats.length} floats** matching your criteria.\n\n`;
    
    if (response.insights) {
      formattedText += `**AI Insights:**\n${response.insights}\n\n`;
    }
    
    if (response.recommendations.length > 0) {
      formattedText += `**Recommendations:**\n`;
      response.recommendations.forEach((rec, index) => {
        formattedText += `${index + 1}. ${rec}\n`;
      });
      formattedText += `\n`;
    }
    
    formattedText += `*Processing time: ${response.processing_time.toFixed(2)}s*`;
    
    return formattedText;
  };

  return (
    <div className="w-96 bg-ocean-darker border-l border-border flex flex-col h-screen">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center shadow-glow-cyan-sm">
            <Sparkles className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
              FloatChat AI
            </h2>
            <p className="text-xs text-muted-foreground">Ask me anything about ocean data</p>
          </div>
        </div>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.sender === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-lg p-3 ${
                  message.sender === "user"
                    ? "bg-primary text-primary-foreground shadow-glow-cyan-sm"
                    : message.error
                    ? "bg-destructive/10 text-destructive border border-destructive/20"
                    : "bg-card text-card-foreground border border-border"
                }`}
              >
                {message.sender === "bot" && (
                  <div className="flex items-center gap-2 mb-1">
                    {message.error ? (
                      <AlertCircle className="w-3 h-3 text-destructive" />
                    ) : (
                      <MessageCircle className="w-3 h-3 text-primary" />
                    )}
                    <span className="text-xs font-semibold text-primary">FloatChat AI</span>
                  </div>
                )}
                <div className="text-sm whitespace-pre-wrap">{message.text}</div>
                {message.data && (
                  <div className="mt-2 pt-2 border-t border-border/50">
                    <div className="text-xs text-muted-foreground">
                      Found {message.data.floats.length} floats • {message.data.parameters.variables?.join(', ') || 'General query'}
                    </div>
                  </div>
                )}
                <span className="text-xs opacity-70 mt-1 block">
                  {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <Input
            placeholder="Ask about ocean data..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && !isLoading && handleSendMessage()}
            disabled={isLoading}
            className="flex-1 bg-secondary border-border text-foreground placeholder:text-muted-foreground disabled:opacity-50"
          />
          <Button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-glow-cyan-sm disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Powered by AI • Real-time ocean insights
        </p>
      </div>
    </div>
  );
};
