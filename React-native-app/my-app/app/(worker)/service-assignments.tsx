import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
  TextInput,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import apiService from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import { useDebounce } from '../../hooks/useDebounce';

interface ServiceAssignment {
  id: number;
  title: string;
  category_name: string;
  urgency: 'normal' | 'urgent' | 'emergency';
  status: string;
  created_at: string;
  preferred_date: string | null;
  preferred_time: string | null;
  location: string;
  city: string;
  client_name: string;
  client_phone: string;
  estimated_duration_hours: number;
  worker_accepted: boolean | null;
}

export default function ServiceAssignments() {
  const { user } = useAuth();
  const { theme, isDark } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<'all' | 'pending' | 'active'>('all');
  const [assignments, setAssignments] = useState<ServiceAssignment[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const debouncedSearchQuery = useDebounce(searchQuery, 500);

  useFocusEffect(
    React.useCallback(() => {
      loadAssignments();
    }, [filter, debouncedSearchQuery])
  );

  const loadAssignments = async () => {
    try {
      setLoading(true);
      let response;
      
      if (filter === 'pending') {
        response = await apiService.getPendingAssignments();
      } else if (filter === 'active') {
        response = await apiService.getWorkerAssignments('in_progress');
      } else {
        response = await apiService.getWorkerAssignments();
      }
      
      setAssignments(response.assignments || response.results || response || []);
    } catch (error: any) {
      console.error('Error loading assignments:', error);
      Alert.alert('Error', error.response?.data?.error || 'Failed to load assignments');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadAssignments();
  };

  const getUrgencyBadge = (urgency: string) => {
    const colors = {
      normal: { bg: '#e8f5e9', text: '#2e7d32' },
      urgent: { bg: '#fff3e0', text: '#e65100' },
      emergency: { bg: '#ffebee', text: '#c62828' },
    };
    const config = colors[urgency as keyof typeof colors] || colors.normal;
    
    return (
      <View style={[styles.urgencyBadge, { backgroundColor: config.bg }]}>
        <Text style={[styles.urgencyText, { color: config.text }]}>
          {urgency.toUpperCase()}
        </Text>
      </View>
    );
  };

  const getStatusBadge = (status: string) => {
    const colors: { [key: string]: { bg: string; text: string } } = {
      pending: { bg: '#fff3e0', text: '#e65100' },
      assigned: { bg: '#e3f2fd', text: '#1565c0' },
      in_progress: { bg: '#f3e5f5', text: '#6a1b9a' },
      completed: { bg: '#e8f5e9', text: '#2e7d32' },
      cancelled: { bg: '#fce4ec', text: '#c2185b' },
    };
    const config = colors[status] || { bg: '#f5f5f5', text: '#616161' };
    
    return (
      <View style={[styles.statusBadge, { backgroundColor: config.bg }]}>
        <Text style={[styles.statusText, { color: config.text }]}>
          {status.replace('_', ' ').toUpperCase()}
        </Text>
      </View>
    );
  };

  // Filter assignments based on search query
  const filteredAssignments = assignments.filter((assignment) => {
    if (!debouncedSearchQuery) return true;
    
    const query = debouncedSearchQuery.toLowerCase();
    return (
      assignment.title?.toLowerCase().includes(query) ||
      assignment.category_name?.toLowerCase().includes(query) ||
      assignment.client_name?.toLowerCase().includes(query) ||
      assignment.location?.toLowerCase().includes(query) ||
      assignment.city?.toLowerCase().includes(query)
    );
  });

  const renderAssignment = ({ item }: { item: ServiceAssignment }) => (
    <TouchableOpacity
      style={[styles.assignmentCard, { backgroundColor: theme.card }]}
      onPress={() => {
        if (item.status === 'in_progress') {
          router.push('/(worker)/active-service' as any);
        } else {
          router.push(`/(worker)/service-assignment/${item.id}` as any);
        }
      }}
      activeOpacity={0.7}
    >
      <View style={styles.cardHeader}>
        <View style={styles.headerLeft}>
          <Text style={[styles.title, { color: theme.text }]} numberOfLines={1}>
            {item.title}
          </Text>
          <Text style={[styles.category, { color: theme.textSecondary }]}>
            {item.category_name}
          </Text>
        </View>
        <View style={styles.headerRight}>
          {getUrgencyBadge(item.urgency)}
          {getStatusBadge(item.status)}
        </View>
      </View>

      <View style={styles.cardBody}>
        <View style={styles.infoRow}>
          <Ionicons name="person-outline" size={16} color={theme.textSecondary} />
          <Text style={[styles.infoText, { color: theme.textSecondary }]}>
            {item.client_name}
          </Text>
        </View>

        <View style={styles.infoRow}>
          <Ionicons name="location-outline" size={16} color={theme.textSecondary} />
          <Text style={[styles.infoText, { color: theme.textSecondary }]}>
            {item.city}, {item.location}
          </Text>
        </View>

        {item.preferred_date && (
          <View style={styles.infoRow}>
            <Ionicons name="calendar-outline" size={16} color={theme.textSecondary} />
            <Text style={[styles.infoText, { color: theme.textSecondary }]}>
              {new Date(item.preferred_date).toLocaleDateString()}
              {item.preferred_time && ` at ${item.preferred_time}`}
            </Text>
          </View>
        )}

        <View style={styles.infoRow}>
          <Ionicons name="time-outline" size={16} color={theme.textSecondary} />
          <Text style={[styles.infoText, { color: theme.textSecondary }]}>
            Est. {item.estimated_duration_hours} hour{item.estimated_duration_hours !== 1 ? 's' : ''}
          </Text>
        </View>
      </View>

      <View style={styles.cardFooter}>
        <Text style={[styles.footerText, { color: theme.textSecondary }]}>
          {new Date(item.created_at).toLocaleDateString()}
        </Text>
        <Ionicons name="chevron-forward" size={20} color={theme.primary} />
      </View>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="Service Assignments" showBack />
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
        <StatusBar style={isDark ? 'light' : 'dark'} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="Service Assignments" showBack />
      
      {/* Search Bar */}
      <View style={[styles.searchContainer, { backgroundColor: theme.card }]}>
        <View style={[styles.searchInputContainer, { backgroundColor: theme.background, borderColor: theme.border }]}>
          <Ionicons name="search" size={20} color={theme.textSecondary} />
          <TextInput
            style={[styles.searchInput, { color: theme.text }]}
            placeholder="Search by title, client, location..."
            placeholderTextColor={theme.textTertiary}
            value={searchQuery}
            onChangeText={setSearchQuery}
          />
          {searchQuery.length > 0 && (
            <TouchableOpacity onPress={() => setSearchQuery('')}>
              <Ionicons name="close-circle" size={20} color={theme.textSecondary} />
            </TouchableOpacity>
          )}
        </View>
      </View>
      
      <View style={[styles.filterContainer, { backgroundColor: theme.card }]}>
        <TouchableOpacity
          style={[
            styles.filterButton,
            filter === 'all' && { backgroundColor: theme.primary },
          ]}
          onPress={() => setFilter('all')}
        >
          <Text style={[
            styles.filterText,
            { color: filter === 'all' ? '#fff' : theme.text },
          ]}>
            All
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.filterButton,
            filter === 'pending' && { backgroundColor: theme.primary },
          ]}
          onPress={() => setFilter('pending')}
        >
          <Text style={[
            styles.filterText,
            { color: filter === 'pending' ? '#fff' : theme.text },
          ]}>
            Pending
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.filterButton,
            filter === 'active' && { backgroundColor: theme.primary },
          ]}
          onPress={() => setFilter('active')}
        >
          <Text style={[
            styles.filterText,
            { color: filter === 'active' ? '#fff' : theme.text },
          ]}>
            Active
          </Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={filteredAssignments}
        renderItem={renderAssignment}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContainer}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={[theme.primary]}
          />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Ionicons name="briefcase-outline" size={64} color={theme.textSecondary} />
            <Text style={[styles.emptyText, { color: theme.textSecondary }]}>
              {filter === 'pending' ? 'No pending assignments' :
               filter === 'active' ? 'No active assignments' :
               'No service assignments yet'}
            </Text>
            <Text style={[styles.emptySubtext, { color: theme.textSecondary }]}>
              Assignments will appear here when clients request your services
            </Text>
          </View>
        }
      />

      <StatusBar style={isDark ? 'light' : 'dark'} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  filterContainer: {
    flexDirection: 'row',
    padding: 12,
    gap: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  filterButton: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  filterText: {
    fontSize: 14,
    fontWeight: '600',
  },
  listContainer: {
    padding: 16,
    paddingBottom: 32,
  },
  assignmentCard: {
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  headerLeft: {
    flex: 1,
    marginRight: 8,
  },
  headerRight: {
    alignItems: 'flex-end',
    gap: 6,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  category: {
    fontSize: 14,
  },
  urgencyBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    alignSelf: 'flex-start',
  },
  urgencyText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    alignSelf: 'flex-start',
  },
  statusText: {
    fontSize: 10,
    fontWeight: 'bold',
  },
  cardBody: {
    gap: 8,
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  infoText: {
    fontSize: 14,
    flex: 1,
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  footerText: {
    fontSize: 12,
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
    paddingHorizontal: 32,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 16,
    textAlign: 'center',
  },
  emptySubtext: {
    fontSize: 14,
    marginTop: 8,
    textAlign: 'center',
  },
  searchContainer: {
    padding: 12,
    paddingBottom: 8,
  },
  searchInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    padding: 0,
  },
});

