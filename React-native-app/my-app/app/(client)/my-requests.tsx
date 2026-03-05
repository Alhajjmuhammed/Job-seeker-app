import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
  Modal,
  TextInput,
} from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useDebounce } from '../../hooks/useDebounce';

interface ServiceRequest {
  id: number;
  title: string;
  category_name: string;
  status: string;
  urgency: string;
  location: string;
  city: string;
  created_at: string;
  worker_name?: string;
  worker_accepted?: boolean;
  total_price?: string;
  client_rating?: number;
}

export default function MyRequestsScreen() {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [categories, setCategories] = useState<any[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [fromDate, setFromDate] = useState<Date | null>(null);
  const [toDate, setToDate] = useState<Date | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const debouncedSearchQuery = useDebounce(searchQuery, 500);

  useFocusEffect(
    useCallback(() => {
      loadCategories();
      setCurrentPage(1);
      loadRequests(1);
    }, [])
  );

  useEffect(() => {
    setCurrentPage(1);
    loadRequests(1);
  }, [selectedCategory, fromDate, toDate, debouncedSearchQuery]);

  const loadCategories = async () => {
    try {
      const response = await apiService.getClientCategories();
      setCategories(response.categories || []);
    } catch (error) {
      console.error('Error loading categories:', error);
    }
  };

  const loadRequests = async (page: number = 1) => {
    try {
      if (page === 1) {
        setLoading(true);
      } else {
        setLoadingMore(true);
      }
      
      const response = await apiService.getMyServiceRequests(
        page,
        selectedCategory,
        fromDate?.toISOString().split('T')[0],
        toDate?.toISOString().split('T')[0],
        debouncedSearchQuery
      );
      const data = response.results || response;
      
      if (page === 1) {
        setRequests(data);
      } else {
        setRequests(prev => [...prev, ...data]);
      }
      
      // Handle pagination metadata
      if (response.total_pages) {
        setTotalPages(response.total_pages);
        setCurrentPage(response.current_page || page);
        setHasMore(response.current_page < response.total_pages);
      } else if (response.next) {
        setHasMore(true);
      } else {
        setHasMore(false);
      }
    } catch (error: any) {
      console.error('Error loading requests:', error);
      Alert.alert('Error', 'Failed to load service requests');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    setCurrentPage(1);
    await loadRequests(1);
    setRefreshing(false);
  };

  const loadMore = () => {
    if (!loadingMore && hasMore) {
      loadRequests(currentPage + 1);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return '#FFA500';
      case 'assigned':
        return '#2196F3';
      case 'accepted':
        return '#4CAF50';
      case 'in_progress':
        return '#9C27B0';
      case 'completed':
        return '#4CAF50';
      case 'cancelled':
        return '#F44336';
      default:
        return theme.textSecondary;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return 'time-outline';
      case 'assigned':
        return 'person-add-outline';
      case 'accepted':
        return 'checkmark-circle-outline';
      case 'in_progress':
        return 'play-circle-outline';
      case 'completed':
        return 'checkmark-done-circle-outline';
      case 'cancelled':
        return 'close-circle-outline';
      default:
        return 'help-circle-outline';
    }
  };

  const getUrgencyBadge = (urgency: string) => {
    const colors = {
      normal: '#4CAF50',
      urgent: '#FFA500',
      emergency: '#F44336',
    };
    return colors[urgency as keyof typeof colors] || theme.textSecondary;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  };

  const filteredRequests = requests.filter(req => {
    if (filter === 'all') return true;
    if (filter === 'active') return ['pending', 'assigned', 'accepted', 'in_progress'].includes(req.status);
    if (filter === 'completed') return req.status === 'completed';
    return req.status === filter;
  });

  const filterButtons = [
    { key: 'all', label: 'All', count: requests.length },
    { key: 'active', label: 'Active', count: requests.filter(r => ['pending', 'assigned', 'accepted', 'in_progress'].includes(r.status)).length },
    { key: 'pending', label: 'Pending', count: requests.filter(r => r.status === 'pending').length },
    { key: 'in_progress', label: 'In Progress', count: requests.filter(r => r.status === 'in_progress').length },
    { key: 'completed', label: 'Completed', count: requests.filter(r => r.status === 'completed').length },
  ];

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: theme.background }]}>
        <Header title="My Service Requests" showBack />
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.primary} />
          <Text style={[styles.loadingText, { color: theme.text }]}>Loading your requests...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Header title="My Service Requests" showBack />
      
      {/* Search Bar */}
      <View style={[styles.searchContainer, { backgroundColor: theme.card }]}>
        <View style={[styles.searchInputContainer, { backgroundColor: theme.background, borderColor: theme.border }]}>
          <Ionicons name="search" size={20} color={theme.textSecondary} />
          <TextInput
            style={[styles.searchInput, { color: theme.text }]}
            placeholder="Search by title, description, location..."
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
      
      {/* Advanced Filters Button */}
      <View style={[styles.filtersHeader, { backgroundColor: theme.card }]}>
        <TouchableOpacity
          style={[styles.advancedFiltersButton, { borderColor: theme.primary }]}
          onPress={() => setShowFilters(!showFilters)}
        >
          <Ionicons name="options-outline" size={20} color={theme.primary} />
          <Text style={[styles.advancedFiltersText, { color: theme.primary }]}>
            Filters
          </Text>
          {(selectedCategory || fromDate || toDate || searchQuery) && (
            <View style={[styles.filterBadge, { backgroundColor: theme.primary }]}>
              <Text style={styles.filterBadgeText}>
                {[selectedCategory, fromDate, toDate, searchQuery].filter(Boolean).length}
              </Text>
            </View>
          )}
        </TouchableOpacity>
        
        {(selectedCategory || fromDate || toDate || searchQuery) && (
          <TouchableOpacity
            style={styles.clearFiltersButton}
            onPress={() => {
              setSelectedCategory('');
              setFromDate(null);
              setToDate(null);
              setSearchQuery('');
            }}
          >
            <Text style={[styles.clearFiltersText, { color: theme.error }]}>Clear</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Advanced Filters Panel */}
      {showFilters && (
        <View style={[styles.filtersPanel, { backgroundColor: theme.card }]}>
          <Text style={[styles.filtersPanelTitle, { color: theme.text }]}>Filter Options</Text>
          
          {/* Category Filter */}
          <View style={styles.filterGroup}>
            <Text style={[styles.filterLabel, { color: theme.textSecondary }]}>Category</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryScroll}>
              <TouchableOpacity
                style={[
                  styles.categoryChip,
                  !selectedCategory && { backgroundColor: theme.primary },
                  selectedCategory && { borderColor: theme.border, borderWidth: 1 }
                ]}
                onPress={() => setSelectedCategory('')}
              >
                <Text style={[
                  styles.categoryChipText,
                  !selectedCategory ? { color: '#fff' } : { color: theme.text }
                ]}>
                  All
                </Text>
              </TouchableOpacity>
              
              {categories.map((cat) => (
                <TouchableOpacity
                  key={cat.id}
                  style={[
                    styles.categoryChip,
                    selectedCategory === cat.id.toString() && { backgroundColor: theme.primary },
                    selectedCategory !== cat.id.toString() && { borderColor: theme.border, borderWidth: 1 }
                  ]}
                  onPress={() => setSelectedCategory(cat.id.toString())}
                >
                  <Text style={[
                    styles.categoryChipText,
                    selectedCategory === cat.id.toString() ? { color: '#fff' } : { color: theme.text }
                  ]}>
                    {cat.name}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>

          {/* Date Range Filter */}
          <View style={styles.filterGroup}>
            <Text style={[styles.filterLabel, { color: theme.textSecondary }]}>Date Range</Text>
            <View style={styles.dateRow}>
              <TouchableOpacity
                style={[styles.dateButton, { backgroundColor: theme.background, borderColor: theme.border }]}
                onPress={() => {
                  Alert.prompt(
                    'From Date',
                    'Enter start date (YYYY-MM-DD)',
                    (text) => {
                      const date = new Date(text);
                      if (!isNaN(date.getTime())) setFromDate(date);
                    }
                  );
                }}
              >
                <Ionicons name="calendar-outline" size={16} color={theme.textSecondary} />
                <Text style={[styles.dateButtonText, { color: theme.text }]}>
                  {fromDate ? fromDate.toLocaleDateString() : 'From Date'}
                </Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={[styles.dateButton, { backgroundColor: theme.background, borderColor: theme.border }]}
                onPress={() => {
                  Alert.prompt(
                    'To Date',
                    'Enter end date (YYYY-MM-DD)',
                    (text) => {
                      const date = new Date(text);
                      if (!isNaN(date.getTime())) setToDate(date);
                    }
                  );
                }}
              >
                <Ionicons name="calendar-outline" size={16} color={theme.textSecondary} />
                <Text style={[styles.dateButtonText, { color: theme.text }]}>
                  {toDate ? toDate.toLocaleDateString() : 'To Date'}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}
      
      {/* Filter Tabs */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.filterContainer}
        contentContainerStyle={styles.filterContent}
      >
        {filterButtons.map((btn) => (
          <TouchableOpacity
            key={btn.key}
            style={[
              styles.filterButton,
              { backgroundColor: filter === btn.key ? theme.primary : theme.card },
              filter === btn.key && styles.filterButtonActive,
            ]}
            onPress={() => setFilter(btn.key)}
          >
            <Text
              style={[
                styles.filterButtonText,
                { color: filter === btn.key ? '#FFFFFF' : theme.text },
              ]}
            >
              {btn.label} ({btn.count})
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <ScrollView
        style={styles.content}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
      >
        {filteredRequests.length === 0 ? (
          <View style={styles.emptyContainer}>
            <Ionicons name="document-text-outline" size={64} color={theme.textSecondary} />
            <Text style={[styles.emptyText, { color: theme.textSecondary }]}>
              {filter === 'all' 
                ? 'No service requests yet'
                : `No ${filter} requests`}
            </Text>
            <TouchableOpacity
              style={[styles.browseButton, { backgroundColor: theme.primary }]}
              onPress={() => router.push('/(client)/search')}
            >
              <Text style={styles.browseButtonText}>Browse Services</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={styles.requestsList}>
            {filteredRequests.map((request) => (
              <TouchableOpacity
                key={request.id}
                style={[styles.requestCard, { backgroundColor: theme.card }]}
                onPress={() => router.push(`/(client)/service-request/${request.id}` as any)}
              >
                {/* Status Badge */}
                <View style={styles.cardHeader}>
                  <View style={[styles.statusBadge, { backgroundColor: getStatusColor(request.status) + '20' }]}>
                    <Ionicons
                      name={getStatusIcon(request.status) as any}
                      size={16}
                      color={getStatusColor(request.status)}
                    />
                    <Text style={[styles.statusText, { color: getStatusColor(request.status) }]}>
                      {request.status.replace('_', ' ').toUpperCase()}
                    </Text>
                  </View>
                  {request.urgency && (
                    <View style={[styles.urgencyBadge, { backgroundColor: getUrgencyBadge(request.urgency) + '20' }]}>
                      <Text style={[styles.urgencyText, { color: getUrgencyBadge(request.urgency) }]}>
                        {request.urgency.toUpperCase()}
                      </Text>
                    </View>
                  )}
                </View>

                {/* Title & Category */}
                <Text style={[styles.requestTitle, { color: theme.text }]} numberOfLines={2}>
                  {request.title}
                </Text>
                <Text style={[styles.categoryText, { color: theme.textSecondary }]}>
                  {request.category_name}
                </Text>

                {/* Location */}
                <View style={styles.infoRow}>
                  <Ionicons name="location-outline" size={16} color={theme.textSecondary} />
                  <Text style={[styles.infoText, { color: theme.textSecondary }]}>
                    {request.city}
                  </Text>
                </View>

                {/* Date */}
                <View style={styles.infoRow}>
                  <Ionicons name="calendar-outline" size={16} color={theme.textSecondary} />
                  <Text style={[styles.infoText, { color: theme.textSecondary }]}>
                    {formatDate(request.created_at)}
                  </Text>
                </View>

                {/* Worker Info */}
                {request.worker_name && (
                  <View style={[styles.workerInfo, { backgroundColor: theme.background }]}>
                    <Ionicons name="person-outline" size={16} color={theme.primary} />
                    <Text style={[styles.workerName, { color: theme.text }]}>
                      {request.worker_name}
                    </Text>
                    {request.worker_accepted === true && (
                      <Ionicons name="checkmark-circle" size={16} color="#4CAF50" />
                    )}
                    {request.worker_accepted === false && (
                      <Text style={styles.rejectedText}>(Rejected)</Text>
                    )}
                  </View>
                )}

                {/* Price */}
                {request.total_price && (
                  <View style={styles.budgetRow}>
                    <Ionicons name="cash-outline" size={16} color={theme.primary} />
                    <Text style={[styles.budgetText, { color: theme.primary }]}>
                      SDG {request.total_price}
                    </Text>
                  </View>
                )}

                {/* View Details Button */}
                <TouchableOpacity
                  style={[styles.viewButton, { borderColor: theme.primary }]}
                  onPress={() => router.push(`/(client)/service-request/${request.id}` as any)}
                >
                  <Text style={[styles.viewButtonText, { color: theme.primary }]}>
                    View Details
                  </Text>
                  <Ionicons name="arrow-forward" size={16} color={theme.primary} />
                </TouchableOpacity>
              </TouchableOpacity>
            ))}

            {/* Load More Button */}
            {hasMore && !loading && (
              <TouchableOpacity
                style={[styles.loadMoreButton, { backgroundColor: theme.card }]}
                onPress={loadMore}
                disabled={loadingMore}
              >
                {loadingMore ? (
                  <ActivityIndicator color={theme.primary} />
                ) : (
                  <>
                    <Text style={[styles.loadMoreText, { color: theme.primary }]}>
                      Load More
                    </Text>
                    <Text style={[styles.pageInfo, { color: theme.textSecondary }]}>
                      Page {currentPage} of {totalPages}
                    </Text>
                  </>
                )}
              </TouchableOpacity>
            )}
          </View>
        )}
      </ScrollView>

      {/* Floating Action Button */}
      <TouchableOpacity
        style={[styles.fab, { backgroundColor: theme.primary }]}
        onPress={() => router.push('/(client)/request-service' as any)}
      >
        <Ionicons name="add" size={28} color="#FFFFFF" />
      </TouchableOpacity>
    </View>
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
  },
  filterContainer: {
    maxHeight: 60,
  },
  filterContent: {
    padding: 12,
    gap: 8,
  },
  filterButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 8,
  },
  filterButtonActive: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  filterButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  content: {
    flex: 1,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 18,
    marginTop: 16,
    marginBottom: 24,
  },
  browseButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  browseButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
  requestsList: {
    padding: 16,
  },
  requestCard: {
    padding: 16,
    borderRadius: 12,
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
    alignItems: 'center',
    marginBottom: 12,
  },
  statusBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
  },
  urgencyBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  urgencyText: {
    fontSize: 10,
    fontWeight: '700',
  },
  requestTitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 4,
  },
  categoryText: {
    fontSize: 14,
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
    gap: 6,
  },
  infoText: {
    fontSize: 14,
  },
  workerInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    marginTop: 8,
    gap: 8,
  },
  workerName: {
    fontSize: 14,
    fontWeight: '600',
    flex: 1,
  },
  rejectedText: {
    fontSize: 12,
    color: '#F44336',
    fontStyle: 'italic',
  },
  budgetRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    gap: 6,
  },
  budgetText: {
    fontSize: 16,
    fontWeight: '700',
  },
  viewButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderRadius: 8,
    paddingVertical: 10,
    marginTop: 12,
    gap: 6,
  },
  viewButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },
  loadMoreButton: {
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    marginTop: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  loadMoreText: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 4,
  },
  pageInfo: {
    fontSize: 12,
  },
  searchContainer: {
    padding: 12,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
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
  filtersHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  advancedFiltersButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
  },
  advancedFiltersText: {
    fontSize: 14,
    fontWeight: '600',
  },
  filterBadge: {
    width: 20,
    height: 20,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterBadgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  clearFiltersButton: {
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  clearFiltersText: {
    fontSize: 14,
    fontWeight: '600',
  },
  filtersPanel: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  filtersPanelTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 16,
  },
  filterGroup: {
    marginBottom: 16,
  },
  filterLabel: {
    fontSize: 14,
    fontWeight: '600',
    marginBottom: 8,
  },
  categoryScroll: {
    maxHeight: 80,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    marginRight: 8,
  },
  categoryChipText: {
    fontSize: 14,
    fontWeight: '600',
  },
  dateRow: {
    flexDirection: 'row',
    gap: 12,
  },
  dateButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
  },
  dateButtonText: {
    fontSize: 14,
  },
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 8,
  },
});
