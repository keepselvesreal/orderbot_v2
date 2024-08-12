import { useState, useEffect, useRef, useContext, createContext } from 'react';
import { UserContext } from './UserContext';

const WebSocketContext = createContext(null);

export const WebSocketProvider = ({ children }) => {
  const { userId } = useContext(UserContext);
  const [socketOpen, setSocketOpen] = useState(false);
  const socketRef = useRef(null);

  useEffect(() => {
    if (userId) {
      const token = localStorage.getItem('accessToken');
      const url = `ws://127.0.0.1:8000/ws/chat/room/${userId}/?token=${token}`;

      socketRef.current = new WebSocket(url);

      socketRef.current.onopen = () => {
        console.log('WebSocket connection established.');
        setSocketOpen(true);
      };

      socketRef.current.onclose = () => {
        console.error('Chat socket closed unexpectedly');
        setSocketOpen(false);
      };

      return () => {
        if (socketRef.current) {
          socketRef.current.close();
        }
      };
    }
  }, [userId]);

  const sendMessage = (message) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not open. Unable to send message.');
    }
  };

  return (
    <WebSocketContext.Provider value={{ socket: socketRef.current, socketOpen, sendMessage }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  return useContext(WebSocketContext);
};