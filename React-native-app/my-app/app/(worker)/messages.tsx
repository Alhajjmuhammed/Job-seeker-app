import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';

interface Message {
  id: number;
  name: string;
  lastMessage: string;
  time: string;
  unread: number;
  avatar: string;
}

export default function WorkerMessagesScreen() {
  const [messages] = React.useState<Message[]>([
    {
      id: 1,
      name: 'Ahmed Hassan',
      lastMessage: 'Can you start tomorrow at 9 AM?',
      time: '10 min ago',
      unread: 2,
      avatar: 'AH',
    },
    {
      id: 2,
      name: 'Fatima Ali',
      lastMessage: 'Thank you for the great work!',
      time: '2 hours ago',
      unread: 0,
      avatar: 'FA',
    },
    {
      id: 3,
      name: 'Ibrahim Omar',
      lastMessage: 'What is your rate for this job?',
      time: '1 day ago',
      unread: 1,
      avatar: 'IO',
    },
  ]);

  return (
    <View style={styles.container}>
      <StatusBar style="light" />
      
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Messages</Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchContainer}>
        <TextInput
          style={styles.searchInput}
          placeholder="Search messages..."
          placeholderTextColor="#9CA3AF"
        />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {messages.map((message) => (
          <TouchableOpacity key={message.id} style={styles.messageCard}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>{message.avatar}</Text>
            </View>
            <View style={styles.messageContent}>
              <View style={styles.messageHeader}>
                <Text style={styles.name}>{message.name}</Text>
                <Text style={styles.time}>{message.time}</Text>
              </View>
              <Text style={styles.lastMessage} numberOfLines={1}>
                {message.lastMessage}
              </Text>
            </View>
            {message.unread > 0 && (
              <View style={styles.unreadBadge}>
                <Text style={styles.unreadText}>{message.unread}</Text>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F3F4F6',
  },
  header: {
    backgroundColor: '#0F766E',
    paddingTop: 60,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  searchContainer: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  searchInput: {
    height: 40,
    backgroundColor: '#F3F4F6',
    borderRadius: 10,
    paddingHorizontal: 16,
    fontSize: 15,
  },
  scrollContent: {
    padding: 20,
  },
  messageCard: {
    flexDirection: 'row',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  avatar: {
    width: 50,
    height: 50,
    borderRadius: 25,
    backgroundColor: '#0F766E',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  avatarText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: 'bold',
  },
  messageContent: {
    flex: 1,
  },
  messageHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  name: {
    fontSize: 16,
    fontWeight: '600',
    color: '#1F2937',
  },
  time: {
    fontSize: 12,
    color: '#9CA3AF',
  },
  lastMessage: {
    fontSize: 14,
    color: '#6B7280',
  },
  unreadBadge: {
    backgroundColor: '#EF4444',
    borderRadius: 10,
    width: 24,
    height: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 8,
  },
  unreadText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: 'bold',
  },
});
