import { useState, useRef, useEffect } from 'react';
import { chat } from '../api/client';
import ReactMarkdown from 'react-markdown';
import { Send, Trash2, X, Loader2, Bot, User, MessageSquare } from 'lucide-react';

export default function ChatInterface({ codeContext, apiKey }) {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async () => {
        const question = input.trim();
        if (!question || loading) return;

        if (!apiKey) {
            setMessages((prev) => [
                ...prev,
                { role: 'user', content: question },
                { role: 'assistant', content: '⚠️ Please set your API key in the header settings first.' },
            ]);
            setInput('');
            return;
        }

        setMessages((prev) => [...prev, { role: 'user', content: question }]);
        setInput('');
        setLoading(true);

        try {
            const data = await chat(question, codeContext, apiKey);
            if (data.success) {
                setMessages((prev) => [...prev, { role: 'assistant', content: data.answer }]);
            } else {
                setMessages((prev) => [
                    ...prev,
                    { role: 'assistant', content: `❌ Error: ${data.error}` },
                ]);
            }
        } catch {
            setMessages((prev) => [
                ...prev,
                { role: 'assistant', content: '❌ Connection failed. Is the backend running?' },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const deleteMessage = (idx) => {
        setMessages((prev) => prev.filter((_, i) => i !== idx));
    };

    return (
        <div className="bg-surface rounded-2xl border border-border shadow-sm flex flex-col h-[520px] animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
                <div className="flex items-center gap-2">
                    <MessageSquare className="w-4 h-4 text-primary-600" />
                    <h3 className="font-semibold text-text-primary text-sm">Ask Your Code</h3>
                </div>
                {messages.length > 0 && (
                    <button
                        id="clear-chat-btn"
                        onClick={() => setMessages([])}
                        className="flex items-center gap-1.5 text-xs text-text-muted hover:text-danger transition-colors"
                    >
                        <Trash2 className="w-3.5 h-3.5" />
                        Clear
                    </button>
                )}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
                {messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-center">
                        <Bot className="w-10 h-10 text-text-muted mb-3" />
                        <p className="text-text-secondary text-sm font-medium">Ready to help</p>
                        <p className="text-text-muted text-xs mt-1">Ask anything about the loaded codebase</p>
                    </div>
                ) : (
                    messages.map((m, i) => (
                        <div
                            key={i}
                            className={`flex gap-2.5 group ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            {m.role === 'assistant' && (
                                <div className="w-7 h-7 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                                    <Bot className="w-3.5 h-3.5 text-primary-600" />
                                </div>
                            )}
                            <div
                                className={`relative max-w-[80%] rounded-xl px-4 py-2.5 text-sm leading-relaxed ${m.role === 'user'
                                        ? 'bg-primary-600 text-white rounded-br-md'
                                        : 'bg-surface-alt border border-border text-text-primary rounded-bl-md prose max-w-none'
                                    }`}
                            >
                                {m.role === 'assistant' ? (
                                    <ReactMarkdown>{m.content}</ReactMarkdown>
                                ) : (
                                    <p className="whitespace-pre-wrap">{m.content}</p>
                                )}
                                <button
                                    onClick={() => deleteMessage(i)}
                                    className="absolute -top-2 -right-2 w-5 h-5 rounded-full bg-surface border border-border flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50 hover:border-red-200"
                                >
                                    <X className="w-3 h-3 text-text-muted hover:text-danger" />
                                </button>
                            </div>
                            {m.role === 'user' && (
                                <div className="w-7 h-7 rounded-lg bg-primary-600/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                                    <User className="w-3.5 h-3.5 text-primary-600" />
                                </div>
                            )}
                        </div>
                    ))
                )}
                {loading && (
                    <div className="flex gap-2.5">
                        <div className="w-7 h-7 rounded-lg bg-primary-100 flex items-center justify-center flex-shrink-0">
                            <Bot className="w-3.5 h-3.5 text-primary-600" />
                        </div>
                        <div className="bg-surface-alt border border-border rounded-xl px-4 py-3 rounded-bl-md">
                            <div className="flex items-center gap-2 text-sm text-text-muted">
                                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                Thinking...
                            </div>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-4 py-3 border-t border-border">
                <div className="flex items-center gap-2">
                    <input
                        id="chat-input"
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                        placeholder="Ask about the code..."
                        disabled={loading}
                        className="flex-1 px-4 py-2.5 rounded-xl border border-border bg-surface-alt text-text-primary text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 disabled:opacity-50 transition"
                    />
                    <button
                        id="send-message-btn"
                        onClick={sendMessage}
                        disabled={loading || !input.trim()}
                        className="w-10 h-10 rounded-xl bg-primary-600 text-white flex items-center justify-center hover:bg-primary-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
    );
}
