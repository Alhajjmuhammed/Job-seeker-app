import React, { useState, useEffect, useRef } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, KeyboardAvoidingView, Platform, ActivityIndicator, RefreshControl } from 'react-native';
import { useLocalSearchParams, useRouter, Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../../contexts/ThemeContext';
import apiService from '../../../services/api';

interface Message {
  id: number;
  sender_id: number;
  sender_name: string;
  sender_type: string;
  recipient_id: number;
  recipient_name: string;
  message: string;
  subject: string;
  created_at: string;
  is_read: boolean;
  is_sent_by_me: boolean;
}

export default function ConversationScreen() {
  const { id, name } = useLocalSearchParams();
  const router = useRouter();
  const { theme, isDark } = useTheme();
  const scrollViewRef = useRef<ScrollView>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadMessages();
  }, [id]);

  const loadMessages = async () => {
    try {
      const response = await apiService.getMessages(Number(id));
      setMessages(response.messages || []);
      setTimeout(() => scrollToBottom(), 100);
    } catch (error) {
      console.error('Error loading messages:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadMessages();
  };

  const scrollToBottom = () => {
    scrollViewRef.current?.scrollToEnd({ animated: true });
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;

    const messageText = newMessage.trim();
    setNewMessage('');
    setSending(true);

    try {
      await apiService.sendMessage(Number(id), messageText, 'Chat Message');
      await loadMessages();
      setTimeout(() => scrollToBottom(), 100);
    } catch (error) {
      console.error('Error sending message:', error);
      setNewMessage(messageText); // Restore message on error
    } finally {
      setSending(false);
    }
  };

  const formatMessageTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <>
      <Stack.Screen 
        options={{
          title: name as string || 'Conversation',
          headerShown: true,
          headerBackTitle: 'Back',
        }}
      />
      <KeyboardAvoidingView 
        style={[styles.container, { backgroundColor: theme.background }]}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading messages...</Text>
          </View>
        ) : (
          <>
            <ScrollView
              ref={scrollViewRef}
              style={styles.messagesContainer}
              contentContainerStyle={styles.messagesContent}
              refreshControl={
                <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.primary]} />
              }
              onContentSizeChange={() => scrollToBottom()}
            >
              {messages.length === 0 ? (
                <View style={styles.emptyState}>
                  <Ionicons name="chatbubble-outline" size={48} color={theme.textSecondary} />
                  <Text style={[styles.emptyText, { color: theme.text }]}>No messages yet</Text>
                  <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>Send a message to start the conversation</Text>
                </View>
              ) : (
                messages.map((message) => (
                  <View
                    key={message.id}
                    style={[
                      styles.messageBubble,
                      message.is_sent_by_me ? styles.sentMessage : styles.receivedMessage,
                    ]}
                  >
                    <View
                      style={[
                        styles.bubble,
                        message.is_sent_by_me
                          ? { backgroundColor: theme.primary }
                          : { backgroundColor: theme.surface },
                      ]}
                    >
                      {!message.is_sent_by_me && (
                        <Text style={[styles.senderName, { color: theme.primary }]}>
                          {message.sender_name}
                        </Text>
                      )}
                      <Text
                        style={[
                          styles.messageText,
                          { color: message.is_sent_by_me ? '#FFFFFF' : theme.text },
                        ]}
                      >
                        {message.message}
                      </Text>
                      <Text
                        style={[
                          styles.messageTime,
                          { color: message.is_sent_by_me ? '#FFFFFF99' : theme.textSecondary },
                        ]}
                      >
                        {formatMessageTime(message.created_at)}
                      </Text>
                    </View>
                  </View>
                ))
              )}
            </ScrollView>

            <View style={[styles.inputContainer, { backgroundColor: theme.surface, borderTopColor: theme.border }]}>
              <TextInput
                style={[
                  styles.input,
                  { 
                    backgroundColor: theme.background, 
                    color: theme.text,
                    borderColor: theme.border,
                  }
                ]}
                placeholder="Type a message..."
                placeholderTextColor={theme.textSecondary}
                value={newMessage}
                onChangeText={setNewMessage}
                multiline
                maxLength={1000}
              />
              <TouchableOpacity
                style={[
                  styles.sendButton,
                  { backgroundColor: newMessage.trim() ? theme.primary : theme.textSecondary },
                ]}
                onPress={sendMessage}
                disabled={!newMessage.trim() || sending}
              >
                {sending ? (
                  <ActivityIndicator size="small" color="#FFFFFF" />
                ) : (
                  <Ionicons name="send" size={20} color="#FFFFFF" />
                )}
              </TouchableOpacity>
            </View>
          </>
        )}
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  messagesContainer: {
    flex: 1,
  },
  messagesContent: {
    padding: 16,
    paddingBottom: 8,
  },
  emptyState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    marginTop: 12,
  },
  emptySubtext: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    marginTop: 4,
    textAlign: 'center',
  },
  messageBubble: {
    marginBottom: 12,
    maxWidth: '80%',
  },
  sentMessage: {
    alignSelf: 'flex-end',
  },
  receivedMessage: {
    alignSelf: 'flex-start',
  },
  bubble: {
    borderRadius: 16,
    padding: 12,
  },
  senderName: {
    fontSize: 12,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  messageText: {
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
    lineHeight: 20,
  },
  messageTime: {
    fontSize: 10,
    fontFamily: 'Poppins_400Regular',
    marginTop: 4,
  },
  inputContainer: {
    flexDirection: 'row',
    padding: 12,
    borderTopWidth: 1,
    alignItems: 'flex-end',
  },
  input: {
    flex: 1,
    borderRadius: 20,
    paddingHorizontal: 16,
    paddingVertical: 10,
    paddingTop: 10,
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
    maxHeight: 100,
    borderWidth: 1,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
});
