import { useState } from "react";
import { MessageCircle, Send, Sparkles, Loader2, AlertCircle, X, MapPin } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { postQuery, AIQueryResponse, APIError } from "@/lib/api";
import { useHighlight } from "@/contexts/HighlightContext";

interface Message {
  id: number;
  text: string;
  sender: "user" | "bot";
  timestamp: Date;
  data?: AIQueryResponse;
  error?: boolean;
  highlightedFloats?: number[];
}

interface ChatbotPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ChatbotPanel = ({ isOpen, onClose }: ChatbotPanelProps) => {
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
  const [lastContext, setLastContext] = useState<{location?: string, variables?: string[]}>({});
  const { highlightedFloats, setHighlightedFloats, clearHighlights } = useHighlight();

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
      // Add context to follow-up queries
      let enhancedQuery = currentInput;
      
      // Check if this is a follow-up query (contains "too", "also", "as well", or starts with "show me", "what is")
      const isFollowUp = /\b(too|also|as well|there)\b/i.test(currentInput) || 
                         /^(show me|what is|what are|give me|find)/i.test(currentInput);
      
      // If it's a follow-up and we have context, enhance the query
      if (isFollowUp && lastContext.location && !/(pacific|atlantic|indian|arctic|southern)/i.test(currentInput)) {
        enhancedQuery = `${currentInput} in ${lastContext.location}`;
        
        // Add context indicator message
        const contextMessage: Message = {
          id: Date.now() + 0.5,
          text: `💡 Using context from previous query: ${lastContext.location}`,
          sender: "bot",
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, contextMessage]);
      }
      
      // Call the real API
      const response = await postQuery(enhancedQuery);
      
      // Save context for next query
      if (response.parameters.location) {
        setLastContext({
          location: response.parameters.location,
          variables: response.parameters.variables || []
        });
      }
      
      // Extract float IDs for highlighting
      const floatIds = response.floats.map(f => f.id);
      setHighlightedFloats(floatIds);
      
      // Create formatted bot response
      const botResponse: Message = {
        id: Date.now() + 1,
        text: formatAIResponse(response),
        sender: "bot",
        timestamp: new Date(),
        data: response,
        highlightedFloats: floatIds,
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
    
    // If it's a single float query (ID/WMO search), show detailed info
    if (response.floats.length === 1 && response.query.includes('ID')) {
      const float = response.floats[0];
      formattedText = `📍 **Float Details**\n\n`;
      formattedText += `**WMO ID:** ${float.wmo_id}\n`;
      formattedText += `**Float ID:** ${float.id}\n`;
      formattedText += `**Status:** ${float.status.charAt(0).toUpperCase() + float.status.slice(1)}\n`;
      if (float.latitude && float.longitude) {
        formattedText += `**Location:** ${float.latitude.toFixed(4)}°, ${float.longitude.toFixed(4)}°\n`;
      }
      if (float.profile_count) {
        formattedText += `**Profiles:** ${float.profile_count}\n`;
      }
      if (float.latest_profile_date) {
        formattedText += `**Last Update:** ${new Date(float.latest_profile_date).toLocaleString()}\n`;
      }
      formattedText += `\n`;
    } else {
      formattedText += `**Found ${response.floats.length} floats** matching your criteria.\n\n`;
    }
    
    if (response.insights) {
      formattedText += `**AI Insights:**\n${response.insights}\n\n`;
    }
    
    formattedText += `*Processing time: ${response.processing_time.toFixed(2)}s*`;
    
    return formattedText;
  };

  const handleRecommendationClick = async (recommendation: string) => {
    if (isLoading) return;
    
    // Add user message
    const userMessage: Message = {
      id: Date.now(),
      text: recommendation,
      sender: "user",
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Call the real API
      const response = await postQuery(recommendation);
      
      // Save context for next query
      if (response.parameters.location) {
        setLastContext({
          location: response.parameters.location,
          variables: response.parameters.variables || []
        });
      }
      
      // Extract float IDs for highlighting
      const floatIds = response.floats.map(f => f.id);
      setHighlightedFloats(floatIds);
      
      // Create formatted bot response
      const botResponse: Message = {
        id: Date.now() + 1,
        text: formatAIResponse(response),
        sender: "bot",
        timestamp: new Date(),
        data: response,
        highlightedFloats: floatIds,
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

  const handleRemoveHighlight = () => {
    clearHighlights();
  };

  return (
    <div 
      className={`fixed right-0 top-0 w-96 bg-ocean-darker border-l border-border flex flex-col h-screen transition-transform duration-300 ease-in-out ${
        isOpen ? 'translate-x-0' : 'translate-x-full'
      }`}
      style={{ zIndex: 1001 }}
    >
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
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
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            ✕
          </Button>
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
                
                {/* Recommendations as clickable buttons */}
                {message.data && message.data.recommendations && message.data.recommendations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-border/50">
                    <div className="text-xs font-semibold text-muted-foreground mb-2">💡 Try these:</div>
                    <div className="flex flex-col gap-1">
                      {message.data.recommendations.slice(0, 3).map((rec, index) => (
                        <Button
                          key={index}
                          variant="outline"
                          size="sm"
                          className="justify-start text-left h-auto py-2 px-3 text-xs hover:bg-primary/10 hover:border-primary/50 transition-colors"
                          onClick={() => handleRecommendationClick(rec)}
                        >
                          <span className="truncate">{rec}</span>
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Float highlighting indicator */}
                {message.highlightedFloats && message.highlightedFloats.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-border/50">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs">
                        <MapPin className="w-3 h-3 text-primary" />
                        <span className="text-muted-foreground">
                          {message.highlightedFloats.length} floats highlighted on map
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                
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
      
      {/* Highlight Control Bar */}
      {highlightedFloats.length > 0 && (
        <div className="px-4 py-2 bg-primary/10 border-t border-primary/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-primary">
                {highlightedFloats.length} floats highlighted
              </span>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveHighlight}
              className="h-7 text-xs hover:bg-primary/20"
            >
              <X className="w-3 h-3 mr-1" />
              Remove
            </Button>
          </div>
        </div>
      )}

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
