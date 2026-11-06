/**
 * One chat thread - shared by the worker and the client app.
 *
 * The server decides what is allowed (jobs/chat_access.py on the backend):
 *  - can_send: false when the job behind this chat was cancelled/rejected,
 *    so the box is replaced by a "chat closed" note.
 *  - other_user.phone_number: only filled once the worker has ACCEPTED a job
 *    between the two of them - that is when the Call button shows.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, KeyboardAvoidingView,
  Platform, ActivityIndicator, RefreshControl, Alert, Linking,
} from 'react-native';
import { useLocalSearchParams, Stack, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import apiService from '../../services/api';
import { useTranslation } from 'react-i18next';

interface Message {
  id: number;
  sender_id: number;
  sender_name: string;
  message: string;
  subject: string;
  created_at: string;
  is_read: boolean;
  is_sent_by_me: boolean;
}

interface OtherUser {
  id: number;
  name: string;
  user_type: string;
  phone_number?: string;
}

const REFRESH_MS = 8000;

export default function ConversationView() {
  const { t } = useTranslation();
  const { id, name } = useLocalSearchParams();
  const { theme } = useTheme();
  const scrollViewRef = useRef<ScrollView>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [other, setOther] = useState<OtherUser | null>(null);
  const [canSend, setCanSend] = useState(true);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const scrollToBottom = () => scrollViewRef.current?.scrollToEnd({ animated: true });

  const loadMessages = useCallback(async (quiet = false) => {
    try {
      const response = await apiService.getMessages(Number(id));
      setMessages(response.messages || []);
      setOther(response.other_user || null);
      setCanSend(response.can_send !== false);
      if (!quiet) setTimeout(scrollToBottom, 100);
    } catch (error: any) {
      if (!quiet && error?.response?.status === 404) {
        Alert.alert(t('messages.chatNotAvailable'), t('messages.chatAfterAccept'));
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [id]);

  useEffect(() => {
    setLoading(true);
    loadMessages();
  }, [id]);

  // New messages appear on their own while this chat is on screen.
  useFocusEffect(
    useCallback(() => {
      const timer = setInterval(() => loadMessages(true), REFRESH_MS);
      return () => clearInterval(timer);
    }, [loadMessages])
  );

  const sendMessage = async () => {
    const text = newMessage.trim();
    if (!text || sending) return;
    setNewMessage('');
    setSending(true);
    try {
      await apiService.sendMessage(Number(id), text, 'Chat Message');
      await loadMessages();
    } catch (error: any) {
      setNewMessage(text); // keep what they typed
      const reason = error?.response?.data?.error;
      Alert.alert(t('messages.notSent'), reason || t('messages.sendFailed'));
      if (error?.response?.status === 403) setCanSend(false);
    } finally {
      setSending(false);
    }
  };

  const phone = other?.phone_number || '';
  const callOther = () => {
    if (!phone) return;
    Linking.openURL(`tel:${phone}`).catch(() =>
      Alert.alert(t('common.error'), t('messages.cannotCall')));
  };

  const formatMessageTime = (dateString: string) => {
    const date = new Date(dateString);
    const diffMins = Math.floor((Date.now() - date.getTime()) / 60000);
    if (diffMins < 1) return t('messages.justNow');
    if (diffMins < 60) return `${diffMins}m`;
    if (diffMins < 24 * 60) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' +
      date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <>
      <Stack.Screen
        options={{
          title: (other?.name || (name as string) || t('nav.messages')),
          headerShown: true,
          headerBackTitle: t('common.back', 'Back'),
          headerRight: () => phone ? (
            <TouchableOpacity onPress={callOther} style={[styles.callButton, { backgroundColor: theme.primary }]}
              accessibilityLabel={t('messages.call')}>
              <Ionicons name="call" size={18} color="#FFFFFF" />
              <Text style={styles.callText}>{t('messages.call')}</Text>
            </TouchableOpacity>
          ) : null,
        }}
      />
      <KeyboardAvoidingView style={{ flex: 1 }} behavior="padding"
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 70}>
        <View style={[styles.container, { backgroundColor: theme.background }]}>
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={theme.primary} />
            </View>
          ) : (
            <>
              <ScrollView
                ref={scrollViewRef}
                style={styles.messagesContainer}
                contentContainerStyle={styles.messagesContent}
                keyboardDismissMode="on-drag"
                keyboardShouldPersistTaps="handled"
                refreshControl={<RefreshControl refreshing={refreshing}
                  onRefresh={() => { setRefreshing(true); loadMessages(); }} colors={[theme.primary]} />}
                onContentSizeChange={scrollToBottom}
              >
                {messages.length === 0 ? (
                  <View style={styles.emptyState}>
                    <Ionicons name="chatbubble-outline" size={48} color={theme.textSecondary} />
                    <Text style={[styles.emptyText, { color: theme.text }]}>{t('messages.noMessagesYet')}</Text>
                    {canSend && (
                      <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>{t('messages.writeFirst')}</Text>
                    )}
                  </View>
                ) : (
                  messages.map((message) => (
                    <View key={message.id}
                      style={[styles.messageBubble, message.is_sent_by_me ? styles.sentMessage : styles.receivedMessage]}>
                      <View style={[styles.bubble,
                        message.is_sent_by_me ? { backgroundColor: theme.primary } : { backgroundColor: theme.surface }]}>
                        <Text style={[styles.messageText, { color: message.is_sent_by_me ? '#FFFFFF' : theme.text }]}>
                          {message.message}
                        </Text>
                        <View style={styles.metaRow}>
                          <Text style={[styles.messageTime,
                            { color: message.is_sent_by_me ? '#FFFFFFB3' : theme.textSecondary }]}>
                            {formatMessageTime(message.created_at)}
                          </Text>
                          {message.is_sent_by_me && (
                            <Ionicons name={message.is_read ? 'checkmark-done' : 'checkmark'} size={13}
                              color={message.is_read ? '#A7F3D0' : '#FFFFFFB3'} style={{ marginLeft: 4 }} />
                          )}
                        </View>
                      </View>
                    </View>
                  ))
                )}
              </ScrollView>

              {canSend ? (
                <View style={[styles.inputContainer, { backgroundColor: theme.surface, borderTopColor: theme.border }]}>
                  <TextInput
                    style={[styles.input, { backgroundColor: theme.background, color: theme.text, borderColor: theme.border }]}
                    placeholder={t('messages.typeMessage')}
                    placeholderTextColor={theme.textSecondary}
                    value={newMessage}
                    onChangeText={setNewMessage}
                    onFocus={() => setTimeout(scrollToBottom, 100)}
                    multiline
                    maxLength={5000}
                  />
                  <TouchableOpacity
                    style={[styles.sendButton, { backgroundColor: newMessage.trim() ? theme.primary : theme.textSecondary }]}
                    onPress={sendMessage}
                    disabled={!newMessage.trim() || sending}
                    accessibilityLabel={t('messages.send')}
                  >
                    {sending ? <ActivityIndicator size="small" color="#FFFFFF" />
                      : <Ionicons name="send" size={20} color="#FFFFFF" />}
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={[styles.closedBar, { borderTopColor: theme.border }]}>
                  <Ionicons name="lock-closed" size={16} color="#92400E" />
                  <Text style={styles.closedText}>{t('messages.chatClosed')}</Text>
                </View>
              )}
            </>
          )}
        </View>
      </KeyboardAvoidingView>
    </>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  messagesContainer: { flex: 1 },
  messagesContent: { padding: 16, paddingBottom: 8 },
  emptyState: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingVertical: 60 },
  emptyText: { fontSize: 18, fontFamily: 'Poppins_600SemiBold', marginTop: 12 },
  emptySubtext: { fontSize: 14, fontFamily: 'Poppins_400Regular', marginTop: 4, textAlign: 'center' },
  messageBubble: { marginBottom: 10, maxWidth: '80%' },
  sentMessage: { alignSelf: 'flex-end' },
  receivedMessage: { alignSelf: 'flex-start' },
  bubble: { borderRadius: 16, paddingHorizontal: 12, paddingTop: 8, paddingBottom: 6 },
  messageText: { fontSize: 15, fontFamily: 'Poppins_400Regular', lineHeight: 20 },
  metaRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', marginTop: 2 },
  messageTime: { fontSize: 10, fontFamily: 'Poppins_400Regular' },
  inputContainer: { flexDirection: 'row', padding: 12, borderTopWidth: 1, alignItems: 'flex-end' },
  input: {
    flex: 1, borderRadius: 20, paddingHorizontal: 16, paddingVertical: 10, fontSize: 15,
    fontFamily: 'Poppins_400Regular', maxHeight: 110, borderWidth: 1,
  },
  sendButton: { width: 42, height: 42, borderRadius: 21, justifyContent: 'center', alignItems: 'center', marginLeft: 8 },
  closedBar: {
    flexDirection: 'row', alignItems: 'center', gap: 8, padding: 14, borderTopWidth: 1, backgroundColor: '#FFFBEB',
  },
  closedText: { flex: 1, color: '#92400E', fontSize: 13, fontFamily: 'Poppins_400Regular' },
  callButton: {
    flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 7,
    borderRadius: 18, marginRight: 8,
  },
  callText: { color: '#FFFFFF', fontSize: 13, fontFamily: 'Poppins_600SemiBold' },
});
