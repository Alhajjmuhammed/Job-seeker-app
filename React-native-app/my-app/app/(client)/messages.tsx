import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ScrollView, TextInput, TouchableOpacity, ActivityIndicator, RefreshControl } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';

interface Conversation {
  id: number;
  name: string;
  username: string;
  user_type: string;
  last_message: string;
  last_message_time: string;
  unread_count: number;
  is_online: boolean;
}

export default function ClientMessagesScreen() {
  const router = useRouter();
  const { theme, isDark } = useTheme();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filteredConversations, setFilteredConversations] = useState<Conversation[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    let mounted = true;
    
    const loadData = async () => {
      try {
        const response = await apiService.getConversations();
        if (mounted) {
          setConversations(response.conversations || []);
        }
      } catch (error) {
        console.error('Error loading conversations:', error);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    
    loadData();
    
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredConversations(conversations);
    } else {
      const filtered = conversations.filter(conv =>
        conv.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        conv.username.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredConversations(filtered);
    }
  }, [searchQuery, conversations]);

  const loadConversations = async (checkMounted = () => true) => {
    try {
      const response = await apiService.getConversations();
      if (checkMounted()) {
        setConversations(response.conversations || []);
      }
    } catch (error) {
      console.error('Error loading conversations:', error);
    } finally {
      if (checkMounted()) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  };

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadConversations();
  }, []);

  const handleConversationPress = (userId: number, userName: string) => {
    router.push(`/(client)/conversation/${userId}?name=${userName}`);
  };

  const formatTime = (dateString: string) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m`;
    if (diffHours < 24) return `${diffHours}h`;
    if (diffDays < 7) return `${diffDays}d`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Messages" />

      <View style={[styles.searchContainer, { borderBottomColor: theme.border }]}>
        <TextInput
          style={[styles.searchInput, { backgroundColor: theme.surface, color: theme.text }]}
          placeholder="Search conversations..."
          placeholderTextColor={theme.textSecondary}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.textSecondary }]}>Loading conversations...</Text>
        </View>
      ) : (
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.primary]} />
        }
      >
        {filteredConversations.length === 0 ? (
          <View style={styles.emptyState}>
            <Ionicons name="chatbubbles-outline" size={48} color={theme.textSecondary} style={{ marginBottom: 12 }} />
            <Text style={[styles.emptyText, { color: theme.text }]}>No conversations yet</Text>
            <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>Start chatting with workers and admins</Text>
          </View>
        ) : (
          filteredConversations.map((conv) => (
            <TouchableOpacity 
              key={conv.id} 
              style={[
                styles.messageCard,
                { backgroundColor: theme.surface },
                isDark ? {} : {
                  shadowColor: '#000',
                  shadowOffset: { width: 0, height: 2 },
                  shadowOpacity: 0.05,
                  shadowRadius: 4,
                  elevation: 2,
                }
              ]}
              onPress={() => handleConversationPress(conv.id, conv.name)}
            >
            <View style={[styles.avatar, { backgroundColor: theme.primary }]}>
              <Text style={styles.avatarText}>{conv.name.substring(0, 2).toUpperCase()}</Text>
            </View>
            <View style={styles.messageContent}>
              <View style={styles.messageHeader}>
                <View style={styles.nameContainer}>
                  <Text style={[styles.name, { color: theme.text }]}>{conv.name}</Text>
                  {conv.user_type && (
                    <View style={[styles.badge, { backgroundColor: conv.user_type === 'admin' ? theme.error : theme.primary + '20' }]}>
                      <Text style={[styles.badgeText, { color: conv.user_type === 'admin' ? theme.error : theme.primary }]}>
                        {conv.user_type}
                      </Text>
                    </View>
                  )}
                </View>
                <Text style={[styles.time, { color: theme.textSecondary }]}>{formatTime(conv.last_message_time)}</Text>
              </View>
              <Text style={[styles.lastMessage, { color: theme.textSecondary }]} numberOfLines={1}>
                {conv.last_message || 'No messages yet'}
              </Text>
            </View>
            {conv.unread_count > 0 && (
              <View style={[styles.unreadBadge, { backgroundColor: theme.error }]}>
                <Text style={styles.unreadText}>{conv.unread_count > 9 ? '9+' : conv.unread_count}</Text>
              </View>
            )}
          </TouchableOpacity>
          ))
        )}
      </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  searchContainer: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  searchInput: {
    height: 40,
    borderRadius: 10,
    paddingHorizontal: 16,
    fontSize: 15,
    fontFamily: 'Poppins_400Regular',
  },
  scrollContent: {
    padding: 20,
  },
  messageCard: {
    flexDirection: 'row',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontFamily: 'Poppins_700Bold',
  },
  messageContent: {
    flex: 1,
  },
  messageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  nameContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  name: {
    fontSize: 16,
    fontFamily: 'Poppins_600SemiBold',
  },
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  badgeText: {
    fontSize: 10,
    fontFamily: 'Poppins_600SemiBold',
    textTransform: 'uppercase',
  },
  time: {
    fontSize: 12,
    fontFamily: 'Poppins_400Regular',
  },
  lastMessage: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
  },
  unreadBadge: {
    borderRadius: 10,
    minWidth: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
    paddingHorizontal: 6,
  },
  unreadText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontFamily: 'Poppins_700Bold',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingTop: 50,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 16,
    fontFamily: 'Poppins_400Regular',
  },
  emptyState: {
    padding: 60,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 18,
    fontFamily: 'Poppins_600SemiBold',
    marginBottom: 4,
  },
  emptySubtext: {
    fontSize: 14,
    fontFamily: 'Poppins_400Regular',
    textAlign: 'center',
  },
});
