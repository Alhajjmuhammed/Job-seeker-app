import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  TextInput,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { router, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../../contexts/ThemeContext';
import Header from '../../components/Header';
import apiService from '../../services/api';
import { useDebounce } from '../../hooks/useDebounce';
import { useTranslation } from 'react-i18next';

interface ServiceRequest {
  id: number;
  title: string;
  status: string;
  urgency: string;
  category_name: string;
  created_at: string;
  preferred_date?: string | null;
  location?: string;
  city?: string;
  total_price?: number;
  worker_name?: string;
}

const STATUS_COLOR: Record<string, string> = {
  pending:     '#F59E0B',
  assigned:    '#3B82F6',
  in_progress: '#8B5CF6',
  completed:   '#10B981',
  cancelled:   '#EF4444',
};

// translation keys - shown in capitals on the badge
const STATUS_LABEL: Record<string, string> = {
  pending:     'status.pending',
  assigned:    'status.assigned',
  in_progress: 'status.in_progress',
  completed:   'status.completed',
  cancelled:   'status.cancelled',
};

const URGENCY_LABEL: Record<string, string> = {
  normal:    'requestService.normal',
  urgent:    'requestService.urgent',
  emergency: 'requestService.emergency',
};

const URGENCY_COLOR: Record<string, string> = {
  normal:    '#10B981',
  urgent:    '#F59E0B',
  emergency: '#EF4444',
};

const FILTERS = [
  { key: 'all',         label: 'myRequests.filterAll' },
  { key: 'pending',     label: 'myRequests.filterPending' },
  { key: 'assigned',    label: 'myRequests.filterAssigned' },
  { key: 'in_progress', label: 'myRequests.filterActive' },
  { key: 'completed',   label: 'myRequests.filterDone' },
  { key: 'cancelled',   label: 'myRequests.filterCancelled' },
];

export default function MyRequests() {
  const { t } = useTranslation();
  const { theme, isDark } = useTheme();
  const [requests, setRequests] = useState<ServiceRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const debouncedSearch = useDebounce(searchQuery, 400);

  const loadRequests = useCallback(async () => {
    try {
      const data = await apiService.getMyServiceRequests(1, undefined, undefined, undefined, debouncedSearch || undefined);
      const results: ServiceRequest[] = Array.isArray(data) ? data : data?.results || [];
      setRequests(results);
    } catch (e) {
      console.log('my-requests load error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [debouncedSearch]);

  useFocusEffect(useCallback(() => {
    setLoading(true);
    loadRequests();
  }, [loadRequests]));

  const onRefresh = () => {
    setRefreshing(true);
    loadRequests();
  };

  const filtered = filter === 'all'
    ? requests
    : requests.filter(r => r.status === filter);

  const s = StyleSheet.create({
    container:    { flex: 1, backgroundColor: theme.background },
    searchBox: {
      flexDirection: 'row', alignItems: 'center',
      backgroundColor: theme.surface, borderRadius: 14,
      marginHorizontal: 16, marginTop: 12, marginBottom: 8,
      paddingHorizontal: 14, paddingVertical: 10,
      shadowColor: '#000', shadowOffset: { width: 0, height: 1 },
      shadowOpacity: 0.05, shadowRadius: 4, elevation: 1,
    },
    searchInput: {
      flex: 1, marginLeft: 8, fontSize: 14,
      fontFamily: 'Poppins_400Regular', color: theme.text,
    },
    filterBar: { paddingHorizontal: 12, marginBottom: 12 },
    filterScroll: { flexDirection: 'row', gap: 8 },
    filterChip: {
      paddingHorizontal: 14, paddingVertical: 7,
      borderRadius: 20, borderWidth: 1.5,
      borderColor: theme.border || (isDark ? '#333' : '#e5e7eb'),
      backgroundColor: theme.surface,
    },
    filterChipActive: {
      backgroundColor: theme.primary,
      borderColor: theme.primary,
    },
    filterChipText: { fontSize: 12, fontFamily: 'Poppins_600SemiBold', color: theme.textSecondary },
    filterChipTextActive: { color: '#fff' },

    listContent: { paddingHorizontal: 16, paddingBottom: 32 },

    card: {
      backgroundColor: theme.surface, borderRadius: 16, marginBottom: 12,
      overflow: 'hidden',
      shadowColor: '#000', shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.06, shadowRadius: 6, elevation: 2,
    },
    cardTop: {
      flexDirection: 'row', alignItems: 'center',
      paddingHorizontal: 14, paddingTop: 14, paddingBottom: 10,
    },
    cardIcon: {
      width: 44, height: 44, borderRadius: 12,
      alignItems: 'center', justifyContent: 'center', marginRight: 12,
    },
    cardBody: { flex: 1 },
    cardTitle: { fontSize: 15, fontFamily: 'Poppins_600SemiBold', color: theme.text, marginBottom: 2 },
    cardCategory: { fontSize: 12, fontFamily: 'Poppins_400Regular', color: theme.textSecondary },
    statusBadge: { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
    statusText: { fontSize: 10, fontFamily: 'Poppins_700Bold', color: '#fff' },

    cardDivider: { height: 1, backgroundColor: isDark ? '#2a2a2a' : '#f3f4f6', marginHorizontal: 14 },
    cardMeta: {
      flexDirection: 'row', flexWrap: 'wrap', gap: 12,
      paddingHorizontal: 14, paddingVertical: 10,
    },
    metaItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
    metaText: { fontSize: 12, fontFamily: 'Poppins_400Regular', color: theme.textSecondary },

    urgencyPill: {
      flexDirection: 'row', alignItems: 'center', gap: 4,
      borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3,
    },
    urgencyText: { fontSize: 10, fontFamily: 'Poppins_700Bold', color: '#fff' },

    emptyBox: {
      flex: 1, alignItems: 'center', justifyContent: 'center', paddingTop: 80,
    },
    emptyText: {
      fontSize: 14, fontFamily: 'Poppins_400Regular',
      color: theme.textSecondary, marginTop: 12, textAlign: 'center', lineHeight: 22,
    },
    centerLoader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  });

  const renderItem = ({ item }: { item: ServiceRequest }) => {
    const statusColor = STATUS_COLOR[item.status] || '#9CA3AF';
    const urgColor = URGENCY_COLOR[item.urgency] || '#10B981';
    return (
      <TouchableOpacity
        style={s.card}
        onPress={() => router.push(`/(client)/service-request/${item.id}`)}
        activeOpacity={0.75}
      >
        <View style={s.cardTop}>
          <View style={[s.cardIcon, { backgroundColor: statusColor + '20' }]}>
            <Ionicons name="construct-outline" size={22} color={statusColor} />
          </View>
          <View style={s.cardBody}>
            <Text style={s.cardTitle} numberOfLines={1}>{item.title || item.category_name}</Text>
            <Text style={s.cardCategory}>{item.category_name}</Text>
          </View>
          <View style={[s.statusBadge, { backgroundColor: statusColor }]}>
            <Text style={s.statusText}>{STATUS_LABEL[item.status] ? t(STATUS_LABEL[item.status]).toUpperCase() : item.status}</Text>
          </View>
        </View>

        <View style={s.cardDivider} />

        <View style={s.cardMeta}>
          <View style={s.metaItem}>
            <Ionicons name="calendar-outline" size={13} color={theme.textSecondary} />
            <Text style={s.metaText}>{new Date(item.created_at).toLocaleDateString()}</Text>
          </View>
          {item.city ? (
            <View style={s.metaItem}>
              <Ionicons name="location-outline" size={13} color={theme.textSecondary} />
              <Text style={s.metaText}>{item.city}</Text>
            </View>
          ) : null}
          {item.worker_name ? (
            <View style={s.metaItem}>
              <Ionicons name="person-outline" size={13} color={theme.textSecondary} />
              <Text style={s.metaText}>{item.worker_name}</Text>
            </View>
          ) : null}
          {item.total_price ? (
            <View style={s.metaItem}>
              <Ionicons name="cash-outline" size={13} color={theme.textSecondary} />
              <Text style={s.metaText}>TSh {item.total_price.toLocaleString()}</Text>
            </View>
          ) : null}
          <View style={[s.urgencyPill, { backgroundColor: urgColor }]}>
            <Text style={s.urgencyText}>{(URGENCY_LABEL[item.urgency] ? t(URGENCY_LABEL[item.urgency]) : item.urgency)?.toUpperCase()}</Text>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <View style={s.container}>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Header title={t('client.myRequests')} />

      {/* Search */}
      <View style={s.searchBox}>
        <Ionicons name="search-outline" size={18} color={theme.textSecondary} />
        <TextInput
          style={s.searchInput}
          placeholder={t('myRequests.searchPlaceholder')}
          placeholderTextColor={theme.textSecondary}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <Ionicons name="close-circle" size={18} color={theme.textSecondary} />
          </TouchableOpacity>
        )}
      </View>

      {/* Filter Chips */}
      <View style={s.filterBar}>
        <FlatList
          data={FILTERS}
          horizontal
          showsHorizontalScrollIndicator={false}
          keyExtractor={i => i.key}
          contentContainerStyle={s.filterScroll}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[s.filterChip, filter === item.key && s.filterChipActive]}
              onPress={() => setFilter(item.key)}
            >
              <Text style={[s.filterChipText, filter === item.key && s.filterChipTextActive]}>
                {t(item.label)}
              </Text>
            </TouchableOpacity>
          )}
        />
      </View>

      {loading ? (
        <View style={s.centerLoader}>
          <ActivityIndicator size="large" color={theme.primary} />
        </View>
      ) : filtered.length === 0 ? (
        <View style={s.emptyBox}>
          <Ionicons name="clipboard-outline" size={52} color={theme.textSecondary} />
          <Text style={s.emptyText}>
            {filter === 'all'
              ? t('myRequests.noRequestsYet')
              : t('myRequests.noFilteredRequests', {
                  status: t(FILTERS.find(f => f.key === filter)?.label ?? 'myRequests.filterAll').toLowerCase(),
                })}
          </Text>
        </View>
      ) : (
        <FlatList
          data={filtered}
          keyExtractor={item => String(item.id)}
          renderItem={renderItem}
          contentContainerStyle={s.listContent}
          showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.primary} />}
        />
      )}
    </View>
  );
}
